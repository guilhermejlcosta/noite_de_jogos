from __future__ import annotations

import asyncio
import random
import secrets
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from core.conexoes_jogo import ConexoesJogo
from core import jogadores as jogadores_core
from core import lobby as lobby_core

from . import game
from . import state


router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"

# WebSockets que estão, de fato, dentro do jogo Não Pode.
# O core/jogadores.py continua sendo a fonte compartilhada de sessão,
# nome, token, código, HOST e pontuação.
conexoes = ConexoesJogo()

# Compatibilidade com a atualização atual sem obrigar uma terceira troca
# de arquivo agora. Na próxima revisão do state.py, esse campo pode ficar lá.
if not hasattr(state, "jogadores_retornando_lobby"):
    state.jogadores_retornando_lobby = set()


# ============================================================
# ARQUIVOS WEB
# ============================================================


@router.get("/jogos/nao-pode")
async def pagina_nao_pode():
    return FileResponse(WEB_DIR / "index.html")


@router.get("/jogos/nao-pode/style.css")
async def estilo_nao_pode():
    return FileResponse(WEB_DIR / "style.css", media_type="text/css")


@router.get("/jogos/nao-pode/game.js")
async def javascript_nao_pode():
    return FileResponse(WEB_DIR / "game.js", media_type="application/javascript")


# ============================================================
# HELPERS DE JOGADOR / SESSÃO
# ============================================================


def _jogador_por_id(jogador_id: Optional[str]):
    if not jogador_id:
        return None

    return jogadores_core.jogadores.get(jogador_id)


def _jogador_por_token(token: str):
    token = (token or "").strip()

    if not token:
        return None

    for jogador in jogadores_core.jogadores.values():
        if jogador.get("token") == token:
            return jogador

    return None


def _jogador_por_codigo(codigo: str):
    codigo = (codigo or "").strip()

    if not codigo:
        return None

    for jogador in jogadores_core.jogadores.values():
        if jogador.get("codigo") == codigo:
            return jogador

    return None


def _gerar_codigo_recuperacao() -> str:
    codigos_em_uso = {
        jogador.get("codigo")
        for jogador in jogadores_core.jogadores.values()
        if jogador.get("codigo")
    }

    while True:
        codigo = f"{secrets.randbelow(10000):04d}"

        if codigo not in codigos_em_uso:
            return codigo


def _criar_jogador(nome: str):
    jogador_id = uuid.uuid4().hex

    jogador = {
        "id": jogador_id,
        "nome": nome,
        "token": secrets.token_urlsafe(32),
        "codigo": _gerar_codigo_recuperacao(),
        "pontos": 0,
        "conectado": False,
        "websocket": None,
    }

    jogadores_core.jogadores[jogador_id] = jogador

    if jogadores_core.host_id is None:
        jogadores_core.host_id = jogador_id

    return jogador


# ============================================================
# HELPERS DO ESTADO
# ============================================================


def _nome_jogador(jogador_id: Optional[str]):
    jogador = _jogador_por_id(jogador_id)

    if not jogador:
        return None

    return jogador.get("nome")


def _jogador_atual():
    return _jogador_por_id(state.jogador_atual_id)


def _lista_jogadores(jogador_destino_id: str):
    lista = []

    for jogador_id, jogador in jogadores_core.jogadores.items():
        lista.append(
            {
                "nome": jogador["nome"],
                "host": jogador_id == jogadores_core.host_id,
                "pontos": jogador.get("pontos", 0),
                "conectado": conexoes.conectado(jogador_id),
                "codigo_recuperacao": (
                    jogador.get("codigo") if jogador_id == jogador_destino_id else None
                ),
            }
        )

    return lista


def _montar_estado(jogador_destino_id: str):
    jogador_atual = _jogador_atual()

    estado = {
        "tipo": "estado",
        "versao": getattr(state, "VERSAO", None),
        "jogadores": _lista_jogadores(jogador_destino_id),
        "jogo_iniciado": state.jogo_iniciado,
        "jogo_finalizado": state.jogo_finalizado,
        "ordem": [
            _nome_jogador(jogador_id)
            for jogador_id in state.ordem_jogadores
            if _nome_jogador(jogador_id)
        ],
        "jogador_atual": (jogador_atual["nome"] if jogador_atual else None),
        "jogador_atual_conectado": (conexoes.conectado(state.jogador_atual_id)),
        "sou_jogador_atual": (jogador_destino_id == state.jogador_atual_id),
        "sou_host": (jogador_destino_id == jogadores_core.host_id),
        "tempo_configurado": state.tempo_configurado,
        "tempo_restante": state.tempo_restante,
        "rodadas_configuradas": state.rodadas_configuradas,
        "rodada_atual": state.rodada_atual,
        "carta_revelada": state.carta_revelada,
        "turno_travado": state.turno_travado,
        "partida_pausada": state.partida_pausada,
        "jogador_pausado": _nome_jogador(state.jogador_pausado_id),
        "codigo_recuperacao": (_jogador_por_id(jogador_destino_id) or {}).get("codigo"),
        "carta": None,
    }

    if (
        state.jogo_iniciado
        and state.carta_revelada
        and jogador_destino_id == state.jogador_atual_id
        and state.carta_atual
    ):
        estado["carta"] = state.carta_atual

    return estado


async def enviar_estado():
    desconectados = []

    for websocket, jogador_id in conexoes.itens():
        try:
            await websocket.send_json(_montar_estado(jogador_id))
        except Exception:
            desconectados.append(websocket)

    for websocket in desconectados:
        conexoes.remover(websocket)


# ============================================================
# TIMER
# ============================================================


def _cancelar_timer():
    tarefa = state.timer_task

    if tarefa and not tarefa.done():
        tarefa.cancel()

    state.timer_task = None


async def _executar_cronometro():
    try:
        while state.jogo_iniciado and state.carta_revelada and not state.turno_travado:
            if state.partida_pausada:
                await asyncio.sleep(0.20)
                continue

            await asyncio.sleep(1)

            if (
                not state.jogo_iniciado
                or not state.carta_revelada
                or state.turno_travado
            ):
                return

            if state.partida_pausada:
                continue

            state.tempo_restante = max(0, state.tempo_restante - 1)

            if state.tempo_restante <= 0:
                state.turno_travado = True

            await enviar_estado()

            if state.turno_travado:
                return

    except asyncio.CancelledError:
        return

    finally:
        tarefa_atual = asyncio.current_task()

        if state.timer_task is tarefa_atual:
            state.timer_task = None


def _iniciar_timer():
    _cancelar_timer()

    state.timer_task = asyncio.create_task(_executar_cronometro())


# ============================================================
# REGRAS DE TURNO
# ============================================================


def _preparar_turno():
    state.carta_atual = game.sortear_carta()
    state.carta_revelada = False
    state.tempo_restante = state.tempo_configurado
    state.turno_travado = False

    if conexoes.conectado(state.jogador_atual_id):
        state.partida_pausada = False
        state.jogador_pausado_id = None
    else:
        state.partida_pausada = True
        state.jogador_pausado_id = state.jogador_atual_id


def _finalizar_jogo():
    _cancelar_timer()

    state.jogo_iniciado = False
    state.jogo_finalizado = True
    state.carta_revelada = False
    state.turno_travado = False
    state.partida_pausada = False
    state.jogador_pausado_id = None
    state.tempo_restante = 0


def _avancar_turno():
    _cancelar_timer()

    if not state.ordem_jogadores:
        _finalizar_jogo()
        return

    state.indice_atual += 1

    if state.indice_atual >= len(state.ordem_jogadores):
        state.indice_atual = 0
        state.rodada_atual += 1

        if state.rodada_atual > state.rodadas_configuradas:
            _finalizar_jogo()
            return

    state.jogador_atual_id = state.ordem_jogadores[state.indice_atual]

    _preparar_turno()


# ============================================================
# VOLTAR AO LOBBY
# ============================================================


async def enviar_todos_para_lobby():
    await conexoes.enviar_voltar_lobby(state.jogadores_retornando_lobby)


# ============================================================
# WEBSOCKET
# ============================================================


@router.websocket("/ws/jogos/nao-pode")
async def websocket_nao_pode(websocket: WebSocket):
    await websocket.accept()

    jogador_id: Optional[str] = None

    try:
        while True:
            dados = await websocket.receive_json()
            acao = dados.get("acao")

            # =================================================
            # ENTRAR
            # =================================================

            if acao == "entrar":
                if state.jogo_iniciado:
                    await conexoes.enviar_erro(websocket, "A partida já começou.")
                    continue

                nome = str(dados.get("nome", "")).strip()

                if not nome:
                    await conexoes.enviar_erro(websocket, "Digite seu nome.")
                    continue

                nome_em_uso = any(
                    jogador["nome"].lower() == nome.lower()
                    for jogador in jogadores_core.jogadores.values()
                )

                if nome_em_uso:
                    await conexoes.enviar_erro(
                        websocket,
                        "Esse nome já está sendo usado. Se for você, use a reconexão.",
                    )
                    continue

                jogador = _criar_jogador(nome)
                jogador_id = jogador["id"]

                await conexoes.associar(websocket, jogador)

                await conexoes.enviar_sessao(websocket, jogador)

                await enviar_estado()
                continue

            # =================================================
            # RECONECTAR POR TOKEN
            # =================================================

            if acao == "reconectar":
                jogador = _jogador_por_token(str(dados.get("token", "")))

                if not jogador:
                    await websocket.send_json({"tipo": "sessao_invalida"})
                    continue

                jogador_id = jogador["id"]

                await conexoes.associar(websocket, jogador)

                if state.partida_pausada and state.jogador_pausado_id == jogador_id:
                    state.partida_pausada = False
                    state.jogador_pausado_id = None

                await conexoes.enviar_sessao(websocket, jogador)

                await enviar_estado()
                continue

            # =================================================
            # RECUPERAR POR CÓDIGO
            # =================================================

            if acao == "recuperar_codigo":
                jogador = _jogador_por_codigo(str(dados.get("codigo", "")))

                if not jogador:
                    await conexoes.enviar_erro(
                        websocket, "Código de recuperação não encontrado."
                    )
                    continue

                jogador_id = jogador["id"]

                await conexoes.associar(websocket, jogador)

                if state.partida_pausada and state.jogador_pausado_id == jogador_id:
                    state.partida_pausada = False
                    state.jogador_pausado_id = None

                await conexoes.enviar_sessao(websocket, jogador)

                await enviar_estado()
                continue

            # Daqui para baixo, precisa existir sessão associada.
            jogador_id = conexoes.id_por_websocket(websocket)

            if not jogador_id:
                await conexoes.enviar_erro(
                    websocket, "Sessão não encontrada. Entre novamente."
                )
                continue

            # =================================================
            # COMEÇAR
            # =================================================

            if acao == "comecar":
                if jogador_id != jogadores_core.host_id:
                    await conexoes.enviar_erro(
                        websocket, "Somente o HOST pode iniciar."
                    )
                    continue

                conectados = conexoes.ids_conectados()

                if len(conectados) < 2:
                    await conexoes.enviar_erro(
                        websocket, "São necessários pelo menos 2 jogadores conectados."
                    )
                    continue

                try:
                    tempo = int(dados.get("tempo", 60))
                    rodadas = int(dados.get("rodadas", 3))
                except (TypeError, ValueError):
                    await conexoes.enviar_erro(
                        websocket, "Configuração de tempo ou rodadas inválida."
                    )
                    continue

                tempo = max(10, min(600, tempo))
                rodadas = max(1, min(20, rodadas))

                game.resetar_para_nova_partida()

                for jogador in jogadores_core.jogadores.values():
                    jogador["pontos"] = 0

                state.tempo_configurado = tempo
                state.tempo_restante = tempo
                state.rodadas_configuradas = rodadas
                state.rodada_atual = 1

                state.ordem_jogadores = conectados.copy()
                random.shuffle(state.ordem_jogadores)

                state.indice_atual = 0
                state.jogador_atual_id = state.ordem_jogadores[0]
                state.jogo_iniciado = True
                state.jogo_finalizado = False

                _preparar_turno()

                await enviar_estado()
                continue

            # =================================================
            # REVELAR
            # =================================================

            if acao == "revelar":
                if not state.jogo_iniciado:
                    continue

                if jogador_id != state.jogador_atual_id:
                    await conexoes.enviar_erro(
                        websocket, "Somente o jogador da vez pode revelar a carta."
                    )
                    continue

                if state.partida_pausada:
                    continue

                if state.turno_travado:
                    continue

                if state.carta_revelada:
                    continue

                state.carta_revelada = True
                state.tempo_restante = state.tempo_configurado

                _iniciar_timer()

                await enviar_estado()
                continue

            # =================================================
            # RESULTADO
            # =================================================

            if acao == "resultado":
                if jogador_id != jogadores_core.host_id:
                    await conexoes.enviar_erro(
                        websocket, "Somente o HOST controla o resultado."
                    )
                    continue

                if not state.jogo_iniciado:
                    continue

                if not state.carta_revelada:
                    continue

                acertou = bool(dados.get("acertou", False))

                atual = _jogador_atual()

                if acertou and atual:
                    atual["pontos"] = atual.get("pontos", 0) + 1

                _avancar_turno()

                await enviar_estado()
                continue

            # =================================================
            # PULAR JOGADOR DESCONECTADO
            # =================================================

            if acao == "pular_desconectado":
                if jogador_id != jogadores_core.host_id:
                    await conexoes.enviar_erro(
                        websocket, "Somente o HOST pode pular o jogador."
                    )
                    continue

                if not state.partida_pausada:
                    continue

                if state.jogador_pausado_id != state.jogador_atual_id:
                    continue

                _avancar_turno()

                await enviar_estado()
                continue

            # =================================================
            # NOVA PARTIDA
            # =================================================

            if acao == "nova_partida":
                if jogador_id != jogadores_core.host_id:
                    await conexoes.enviar_erro(
                        websocket, "Somente o HOST pode iniciar uma nova partida."
                    )
                    continue

                game.resetar_para_nova_partida()

                for jogador in jogadores_core.jogadores.values():
                    jogador["pontos"] = 0

                await enviar_estado()
                continue

            # =================================================
            # VOLTAR AO LOBBY
            # =================================================

            if acao == "voltar_lobby":
                if jogador_id != jogadores_core.host_id:
                    await conexoes.enviar_erro(
                        websocket, "Somente o HOST pode voltar todos ao lobby."
                    )
                    continue

                # Libera a seleção para o lobby aceitar outro jogo.
                lobby_core.jogo_selecionado = None

                # Limpa somente o estado da partida.
                # Jogadores, sessões e HOST continuam no core/jogadores.py.
                game.resetar_para_nova_partida()

                await enviar_todos_para_lobby()
                continue

    except WebSocketDisconnect:
        pass

    except Exception as erro:
        print("Erro no WebSocket do Não Pode:", repr(erro))

    finally:
        jogador_id = jogador_id or conexoes.id_por_websocket(websocket)

        conexoes.remover(websocket, marcar_offline=False)

        if not jogador_id:
            return

        # Quando o HOST manda todos voltarem ao lobby, o fechamento do
        # WebSocket é intencional. Não podemos tratar isso como queda,
        # pausar partida ou derrubar a sessão compartilhada.
        if jogador_id in state.jogadores_retornando_lobby:
            state.jogadores_retornando_lobby.discard(jogador_id)
            return

        jogador = _jogador_por_id(jogador_id)

        if jogador and jogador.get("websocket") is websocket:
            jogador["websocket"] = None
            jogador["conectado"] = False

        if state.jogo_iniciado and state.jogador_atual_id == jogador_id:
            state.partida_pausada = True
            state.jogador_pausado_id = jogador_id

        # Troca de HOST somente entre jogadores que ainda estão conectados
        # ao Não Pode. A sessão do jogador desconectado é preservada para
        # reconexão por token/código.
        if jogadores_core.host_id == jogador_id:
            conectados = conexoes.ids_conectados()
            jogadores_core.host_id = conectados[0] if conectados else None

        await enviar_estado()

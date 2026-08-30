from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from core import jogadores as jogadores_core
from core import lobby as lobby_core
from core.conexoes_jogo import ConexoesJogo
from . import game, state


router = APIRouter()
WEB_DIR = Path(__file__).resolve().parent / "web"
conexoes = ConexoesJogo()


@router.get("/jogos/mimica")
async def pagina():
    return FileResponse(WEB_DIR / "index.html")


@router.get("/jogos/mimica/style.css")
async def estilo():
    return FileResponse(WEB_DIR / "style.css", media_type="text/css")


@router.get("/jogos/mimica/game.js")
async def javascript():
    return FileResponse(WEB_DIR / "game.js", media_type="application/javascript")


def montar_estado(destino_id):
    atual = conexoes.jogador(state.jogador_atual_id)
    lista = []
    for pid, cadastro in jogadores_core.jogadores.items():
        lista.append({
            "id": pid, "nome": cadastro["nome"],
            "host": pid == jogadores_core.host_id,
            "conectado": conexoes.conectado(pid), "pontos": state.pontos.get(pid, 0),
        })
    pode_ver = (
        state.jogo_iniciado and state.tema_revelado
        and destino_id == state.jogador_atual_id
    )
    return {
        "tipo": "estado", "versao": state.VERSAO, "jogadores": lista,
        "sou_host": destino_id == jogadores_core.host_id,
        "sou_jogador_atual": destino_id == state.jogador_atual_id,
        "jogo_iniciado": state.jogo_iniciado, "jogo_finalizado": state.jogo_finalizado,
        "jogador_atual": atual["nome"] if atual else None,
        "jogador_atual_conectado": conexoes.conectado(state.jogador_atual_id),
        "rodada_atual": state.rodada_atual,
        "rodadas_configuradas": state.rodadas_configuradas,
        "tempo_configurado": state.tempo_configurado,
        "tempo_restante": state.tempo_restante,
        "tema_revelado": state.tema_revelado,
        "tema": state.tema_atual if pode_ver else None,
        "turno_travado": state.turno_travado,
        "partida_pausada": state.partida_pausada,
        "codigo_recuperacao": (conexoes.jogador(destino_id) or {}).get("codigo"),
    }


async def enviar_estado():
    falhas = []
    for websocket, pid in conexoes.itens():
        try:
            await websocket.send_json(montar_estado(pid))
        except Exception:
            falhas.append(websocket)
    for websocket in falhas:
        conexoes.remover(websocket)


async def voltar_todos():
    await conexoes.enviar_voltar_lobby(state.jogadores_retornando_lobby)


@router.websocket("/ws/jogos/mimica")
async def websocket_jogo(websocket: WebSocket):
    await websocket.accept()
    jogador_id = None
    try:
        while True:
            dados = await websocket.receive_json()
            acao = dados.get("acao")

            if acao in ("reconectar", "recuperar_codigo"):
                if acao == "reconectar":
                    cadastro = jogadores_core.jogador_por_token(str(dados.get("token", "")).strip())
                else:
                    cadastro = jogadores_core.jogador_por_codigo(str(dados.get("codigo", "")).strip())
                if not cadastro:
                    if acao == "reconectar":
                        await websocket.send_json({"tipo": "sessao_invalida"})
                    else:
                        await conexoes.enviar_erro(websocket, "Código de recuperação não encontrado.")
                    continue
                if acao == "recuperar_codigo":
                    cadastro["token"] = uuid.uuid4().hex
                jogador_id = cadastro["id"]
                await conexoes.associar(websocket, cadastro)
                if state.partida_pausada and state.jogador_pausado_id == jogador_id:
                    state.partida_pausada = False
                    state.jogador_pausado_id = None
                    if state.tema_revelado and not state.turno_travado:
                        game.iniciar_timer(enviar_estado)
                await conexoes.enviar_sessao(websocket, cadastro)
                await enviar_estado()
                continue

            jogador_id = conexoes.id_por_websocket(websocket)
            if not jogador_id:
                await conexoes.enviar_erro(websocket, "Sessão não encontrada.")
                continue

            if acao == "comecar":
                if jogador_id != jogadores_core.host_id:
                    await conexoes.enviar_erro(websocket, "Somente o HOST pode iniciar.")
                    continue
                participantes = conexoes.ids_conectados()
                if len(participantes) < 2:
                    await conexoes.enviar_erro(websocket, "São necessários pelo menos 2 jogadores.")
                    continue
                try:
                    tempo = int(dados.get("tempo", 60))
                    rodadas = int(dados.get("rodadas", 3))
                except (TypeError, ValueError):
                    await conexoes.enviar_erro(websocket, "Configuração inválida.")
                    continue
                game.iniciar(participantes, max(30, min(180, tempo)), max(1, min(10, rodadas)), conexoes.conectado)

            elif acao == "revelar":
                if jogador_id != state.jogador_atual_id or not state.jogo_iniciado:
                    continue
                if state.partida_pausada or state.tema_revelado or state.turno_travado:
                    continue
                state.tema_revelado = True
                state.tempo_restante = state.tempo_configurado
                game.iniciar_timer(enviar_estado)

            elif acao == "resultado":
                if jogador_id != jogadores_core.host_id or not state.jogo_iniciado:
                    continue
                if not state.tema_revelado:
                    continue
                if bool(dados.get("acertou")) and state.jogador_atual_id:
                    state.pontos[state.jogador_atual_id] = state.pontos.get(state.jogador_atual_id, 0) + 1
                game.avancar_turno(conexoes.conectado)

            elif acao == "pular_desconectado":
                if jogador_id != jogadores_core.host_id or not state.partida_pausada:
                    continue
                game.avancar_turno(conexoes.conectado)

            elif acao == "nova_partida":
                if jogador_id != jogadores_core.host_id or not state.jogo_finalizado:
                    continue
                game.resetar()

            elif acao == "voltar_lobby":
                if jogador_id != jogadores_core.host_id:
                    await conexoes.enviar_erro(websocket, "Somente o HOST pode voltar ao Lobby.")
                    continue
                lobby_core.jogo_selecionado = None
                game.resetar()
                await voltar_todos()
                continue
            else:
                continue
            await enviar_estado()
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        print("Erro no WebSocket da Mímica:", repr(exc))
    finally:
        jogador_id = jogador_id or conexoes.id_por_websocket(websocket)
        conexoes.remover(websocket, marcar_offline=False)
        if not jogador_id:
            return
        if jogador_id in state.jogadores_retornando_lobby:
            state.jogadores_retornando_lobby.discard(jogador_id)
            return
        cadastro = conexoes.jogador(jogador_id)
        if cadastro and cadastro.get("websocket") is websocket:
            cadastro["websocket"] = None
            cadastro["conectado"] = False
        if state.jogo_iniciado and state.jogador_atual_id == jogador_id:
            game.cancelar_timer()
            state.partida_pausada = True
            state.jogador_pausado_id = jogador_id
        if jogadores_core.host_id == jogador_id:
            conectados = conexoes.ids_conectados()
            jogadores_core.host_id = conectados[0] if conectados else None
        await enviar_estado()

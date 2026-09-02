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


@router.get("/jogos/stop")
async def pagina():
    return FileResponse(WEB_DIR / "index.html")


@router.get("/jogos/stop/style.css")
async def estilo():
    return FileResponse(WEB_DIR / "style.css", media_type="text/css")


@router.get("/jogos/stop/game.js")
async def javascript():
    return FileResponse(WEB_DIR / "game.js", media_type="application/javascript")


def montar_estado(destino_id):
    revisao = state.fase in ("revisao", "final")
    lista = []
    for pid, cadastro in jogadores_core.jogadores.items():
        item = {
            "id": pid,
            "nome": cadastro["nome"],
            "host": pid == jogadores_core.host_id,
            "conectado": conexoes.conectado(pid),
            "enviou": pid in state.respostas,
            "pontos_rodada": state.pontos_rodada.get(pid, 0) if revisao else None,
            "pontos_totais": state.pontos_totais.get(pid, 0),
            "respostas": None,
        }
        if revisao:
            item["respostas"] = [
                {
                    "categoria_id": cat["id"],
                    "categoria": cat["nome"],
                    "resposta": state.respostas.get(pid, {}).get(cat["id"], ""),
                    "invalida": (pid, cat["id"]) in state.invalidas,
                }
                for cat in game.CATEGORIAS
            ]
        lista.append(item)
    maior = max(state.pontos_totais.values(), default=0)
    vencedores = (
        [
            conexoes.jogador(pid)["nome"]
            for pid in state.participantes
            if conexoes.jogador(pid) and state.pontos_totais.get(pid, 0) == maior
        ]
        if state.jogo_finalizado
        else []
    )
    return {
        "tipo": "estado",
        "versao": state.VERSAO,
        "jogadores": lista,
        "sou_host": destino_id == jogadores_core.host_id,
        "jogo_iniciado": state.jogo_iniciado,
        "jogo_finalizado": state.jogo_finalizado,
        "fase": state.fase,
        "categorias": game.CATEGORIAS,
        "letra": state.letra_atual,
        "rodada_atual": state.rodada_atual,
        "rodadas_configuradas": state.rodadas_configuradas,
        "tempo_restante": state.tempo_restante,
        "ja_enviei": destino_id in state.respostas,
        "minhas_respostas": (
            state.respostas.get(destino_id, {}) if state.fase == "preenchendo" else {}
        ),
        "ultima_rodada": state.rodada_atual >= state.rodadas_configuradas,
        "vencedores": vencedores,
        "maior_pontuacao": maior,
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


@router.websocket("/ws/jogos/stop")
async def websocket_jogo(websocket: WebSocket):
    await websocket.accept()
    jogador_id = None
    try:
        while True:
            dados = await websocket.receive_json()
            acao = dados.get("acao")
            if acao in ("reconectar", "recuperar_codigo"):
                cadastro = (
                    jogadores_core.jogador_por_token(
                        str(dados.get("token", "")).strip()
                    )
                    if acao == "reconectar"
                    else jogadores_core.jogador_por_codigo(
                        str(dados.get("codigo", "")).strip()
                    )
                )
                if not cadastro:
                    if acao == "reconectar":
                        await websocket.send_json({"tipo": "sessao_invalida"})
                    else:
                        await conexoes.enviar_erro(
                            websocket, "Código de recuperação não encontrado."
                        )
                    continue
                if acao == "recuperar_codigo":
                    cadastro["token"] = uuid.uuid4().hex
                jogador_id = cadastro["id"]
                await conexoes.associar(websocket, cadastro)
                await conexoes.enviar_sessao(websocket, cadastro)
                await enviar_estado()
                continue
            jogador_id = conexoes.id_por_websocket(websocket)
            if not jogador_id:
                await conexoes.enviar_erro(websocket, "Sessão não encontrada.")
                continue
            if acao == "comecar":
                if jogador_id != jogadores_core.host_id:
                    await conexoes.enviar_erro(
                        websocket, "Somente o HOST pode iniciar."
                    )
                    continue
                participantes = conexoes.ids_conectados()
                if len(participantes) < 2:
                    await conexoes.enviar_erro(
                        websocket, "São necessários pelo menos 2 jogadores."
                    )
                    continue
                try:
                    rodadas = int(dados.get("rodadas", 3))
                    tempo = int(dados.get("tempo", 90))
                except (TypeError, ValueError):
                    await conexoes.enviar_erro(websocket, "Configuração inválida.")
                    continue
                game.iniciar(
                    participantes,
                    max(1, min(10, rodadas)),
                    max(30, min(180, tempo)),
                    enviar_estado,
                )
            elif acao in ("salvar", "stop"):
                respostas = dados.get("respostas", {})
                if not isinstance(respostas, dict) or not game.salvar_respostas(
                    jogador_id, respostas
                ):
                    continue
                if acao == "stop":
                    game.encerrar_rodada()
            elif acao == "encerrar":
                if jogador_id != jogadores_core.host_id:
                    continue
                game.encerrar_rodada()
            elif acao == "invalidar":
                if jogador_id != jogadores_core.host_id:
                    continue
                game.alternar_invalida(
                    str(dados.get("jogador_id", "")), str(dados.get("categoria_id", ""))
                )
            elif acao == "proxima":
                if jogador_id != jogadores_core.host_id:
                    continue
                game.proxima(enviar_estado)
            elif acao == "nova_partida":
                if jogador_id != jogadores_core.host_id or not state.jogo_finalizado:
                    continue
                game.resetar()
            elif acao == "voltar_lobby":
                if jogador_id != jogadores_core.host_id:
                    await conexoes.enviar_erro(
                        websocket, "Somente o HOST pode voltar ao Lobby."
                    )
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
        print("Erro no WebSocket do Stop:", repr(exc))
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
        if jogadores_core.host_id == jogador_id:
            conectados = conexoes.ids_conectados()
            jogadores_core.host_id = conectados[0] if conectados else None
        await enviar_estado()

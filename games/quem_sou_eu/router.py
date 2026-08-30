from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from core import jogadores as jogadores_core
from core import lobby as lobby_core
from core.conexoes_jogo import ConexoesJogo
from . import game, state


router = APIRouter()
WEB_DIR = Path(__file__).resolve().parent / "web"
conexoes = ConexoesJogo()


@router.get("/jogos/quem-sou-eu")
async def pagina():
    return FileResponse(WEB_DIR / "index.html")


@router.get("/jogos/quem-sou-eu/style.css")
async def estilo():
    return FileResponse(WEB_DIR / "style.css", media_type="text/css")


@router.get("/jogos/quem-sou-eu/game.js")
async def javascript():
    return FileResponse(WEB_DIR / "game.js", media_type="application/javascript")


def montar_estado(destino_id):
    jogadores = []
    for jogador_id, jogador in jogadores_core.jogadores.items():
        jogadores.append({
            "id": jogador_id,
            "nome": jogador["nome"],
            "host": jogador_id == jogadores_core.host_id,
            "conectado": conexoes.conectado(jogador_id),
            "descobriu": jogador_id in state.descobriram,
            "identidade": (
                state.identidades.get(jogador_id)
                if jogador_id != destino_id or jogador_id in state.descobriram
                else None
            ),
        })
    atual = conexoes.jogador(state.jogador_atual_id)
    return {
        "tipo": "estado",
        "versao": state.VERSAO,
        "jogadores": jogadores,
        "sou_host": destino_id == jogadores_core.host_id,
        "sou_jogador_atual": destino_id == state.jogador_atual_id,
        "jogo_iniciado": state.jogo_iniciado,
        "jogo_finalizado": state.jogo_finalizado,
        "jogador_atual": atual["nome"] if atual else None,
        "codigo_recuperacao": (conexoes.jogador(destino_id) or {}).get("codigo"),
        "ordem_resultado": [
            (conexoes.jogador(pid) or {}).get("nome") for pid in state.descobriram
        ],
    }


async def enviar_estado():
    falhas = []
    for websocket, jogador_id in conexoes.itens():
        try:
            await websocket.send_json(montar_estado(jogador_id))
        except Exception:
            falhas.append(websocket)
    for websocket in falhas:
        conexoes.remover(websocket)


async def enviar_todos_para_lobby():
    await conexoes.enviar_voltar_lobby(state.jogadores_retornando_lobby)


@router.websocket("/ws/jogos/quem-sou-eu")
async def websocket_jogo(websocket: WebSocket):
    await websocket.accept()
    jogador_id = None
    try:
        while True:
            dados = await websocket.receive_json()
            acao = dados.get("acao")

            if acao == "reconectar":
                jogador = jogadores_core.jogador_por_token(str(dados.get("token", "")).strip())
                if not jogador:
                    await websocket.send_json({"tipo": "sessao_invalida"})
                    continue
                jogador_id = jogador["id"]
                await conexoes.associar(websocket, jogador)
                await conexoes.enviar_sessao(websocket, jogador)
                await enviar_estado()
                continue

            if acao == "recuperar_codigo":
                jogador = jogadores_core.jogador_por_codigo(str(dados.get("codigo", "")).strip())
                if not jogador:
                    await conexoes.enviar_erro(websocket, "Código de recuperação não encontrado.")
                    continue
                jogador["token"] = uuid.uuid4().hex
                jogador_id = jogador["id"]
                await conexoes.associar(websocket, jogador)
                await conexoes.enviar_sessao(websocket, jogador)
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
                conectados = conexoes.ids_conectados()
                if len(conectados) < 2:
                    await conexoes.enviar_erro(websocket, "São necessários pelo menos 2 jogadores.")
                    continue
                if len(conectados) > len(game.IDENTIDADES):
                    await conexoes.enviar_erro(websocket, "Não há identidades suficientes para todos.")
                    continue
                game.iniciar(conectados)

            elif acao == "resposta":
                if jogador_id != jogadores_core.host_id or not state.jogo_iniciado:
                    continue
                resposta = dados.get("resposta")
                if resposta == "nao":
                    game.avancar_turno()
                elif resposta == "acertou":
                    game.marcar_acerto()
                elif resposta != "sim":
                    continue

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
                await enviar_todos_para_lobby()
                continue
            else:
                continue

            await enviar_estado()
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        print("Erro no WebSocket do Quem Sou Eu:", repr(exc))
    finally:
        jogador_id = jogador_id or conexoes.id_por_websocket(websocket)
        conexoes.remover(websocket, marcar_offline=False)
        if not jogador_id:
            return
        if jogador_id in state.jogadores_retornando_lobby:
            state.jogadores_retornando_lobby.discard(jogador_id)
            return
        jogador = conexoes.jogador(jogador_id)
        if jogador and jogador.get("websocket") is websocket:
            jogador["websocket"] = None
            jogador["conectado"] = False
        if jogadores_core.host_id == jogador_id:
            conectados = conexoes.ids_conectados()
            jogadores_core.host_id = conectados[0] if conectados else None
        await enviar_estado()

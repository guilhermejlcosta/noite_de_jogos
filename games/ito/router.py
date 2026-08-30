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


@router.get("/jogos/ito")
async def pagina():
    return FileResponse(WEB_DIR / "index.html")


@router.get("/jogos/ito/style.css")
async def estilo():
    return FileResponse(WEB_DIR / "style.css", media_type="text/css")


@router.get("/jogos/ito/game.js")
async def javascript():
    return FileResponse(WEB_DIR / "game.js", media_type="application/javascript")


def montar_estado(destino_id):
    revelar = state.fase in ("resultado", "final")
    jogadores = []
    for pid, cadastro in jogadores_core.jogadores.items():
        jogadores.append({
            "id": pid,
            "nome": cadastro["nome"],
            "host": pid == jogadores_core.host_id,
            "conectado": conexoes.conectado(pid),
            "enviou_pista": pid in state.pistas,
        })

    ordem = []
    for pid in state.ordem:
        cadastro = conexoes.jogador(pid)
        if cadastro:
            ordem.append({
                "id": pid,
                "nome": cadastro["nome"],
                "pista": state.pistas.get(pid),
                "numero": state.numeros.get(pid) if revelar else None,
            })

    return {
        "tipo": "estado",
        "versao": state.VERSAO,
        "jogadores": jogadores,
        "sou_host": destino_id == jogadores_core.host_id,
        "jogo_iniciado": state.jogo_iniciado,
        "jogo_finalizado": state.jogo_finalizado,
        "fase": state.fase,
        "tema": game.tema_atual(),
        "numero_secreto": state.numeros.get(destino_id) if state.fase in ("pistas", "ordenando") else None,
        "minha_pista": state.pistas.get(destino_id),
        "ordem": ordem,
        "rodada": state.indice_rodada + 1,
        "total_rodadas": len(state.temas_partida),
        "erros_rodada": state.erros_rodada,
        "pontos_rodada": state.pontos_rodada,
        "pontos_total": state.pontos_total,
        "codigo_recuperacao": (conexoes.jogador(destino_id) or {}).get("codigo"),
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


@router.websocket("/ws/jogos/ito")
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
                    quantidade = int(dados.get("quantidade", 5))
                except (TypeError, ValueError):
                    quantidade = 5
                game.iniciar(participantes, max(3, min(10, quantidade)))
            elif acao == "enviar_pista":
                if not game.enviar_pista(jogador_id, dados.get("pista", "")):
                    await conexoes.enviar_erro(websocket, "Não foi possível registrar essa pista.")
                    continue
            elif acao == "mover":
                if jogador_id != jogadores_core.host_id:
                    continue
                direcao = -1 if dados.get("direcao") == "cima" else 1
                game.mover(str(dados.get("jogador_id", "")), direcao)
            elif acao == "revelar":
                if jogador_id != jogadores_core.host_id:
                    continue
                game.revelar()
            elif acao == "proxima":
                if jogador_id != jogadores_core.host_id:
                    continue
                game.proxima()
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
                await conexoes.enviar_voltar_lobby(state.jogadores_retornando_lobby)
                continue
            else:
                continue
            await enviar_estado()
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        print("Erro no WebSocket do ITO:", repr(exc))
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

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


@router.get("/jogos/mais-provavel")
async def pagina():
    return FileResponse(WEB_DIR / "index.html")


@router.get("/jogos/mais-provavel/style.css")
async def estilo():
    return FileResponse(WEB_DIR / "style.css", media_type="text/css")


@router.get("/jogos/mais-provavel/game.js")
async def javascript():
    return FileResponse(WEB_DIR / "game.js", media_type="application/javascript")


def montar_estado(destino_id):
    revelar = state.fase == "resultado"
    contagem = game.contagem_rodada() if revelar else {}
    lista = []
    for pid, cadastro in jogadores_core.jogadores.items():
        lista.append({
            "id": pid, "nome": cadastro["nome"], "host": pid == jogadores_core.host_id,
            "conectado": conexoes.conectado(pid), "votou": pid in state.votos,
            "votos_rodada": contagem.get(pid, 0) if revelar else None,
            "total_votos": state.total_votos.get(pid, 0),
        })
    meu_voto = state.votos.get(destino_id) if revelar else None
    maior = max(state.total_votos.values(), default=0)
    destaques = [
        conexoes.jogador(pid)["nome"] for pid in state.participantes
        if conexoes.jogador(pid) and state.total_votos.get(pid, 0) == maior
    ] if state.jogo_finalizado else []
    return {
        "tipo": "estado", "versao": state.VERSAO, "jogadores": lista,
        "sou_host": destino_id == jogadores_core.host_id,
        "jogo_iniciado": state.jogo_iniciado, "jogo_finalizado": state.jogo_finalizado,
        "fase": state.fase, "situacao": game.situacao_atual(),
        "numero_rodada": state.indice_situacao + 1,
        "quantidade_rodadas": len(state.situacoes_partida),
        "ja_votei": destino_id in state.votos, "meu_voto": meu_voto,
        "ultima_rodada": bool(state.situacoes_partida) and state.indice_situacao == len(state.situacoes_partida) - 1,
        "destaques": destaques, "maior_total": maior,
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


@router.websocket("/ws/jogos/mais-provavel")
async def websocket_jogo(websocket: WebSocket):
    await websocket.accept()
    jogador_id = None
    try:
        while True:
            dados = await websocket.receive_json()
            acao = dados.get("acao")
            if acao in ("reconectar", "recuperar_codigo"):
                cadastro = jogadores_core.jogador_por_token(str(dados.get("token", "")).strip()) if acao == "reconectar" else jogadores_core.jogador_por_codigo(str(dados.get("codigo", "")).strip())
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
                    quantidade = int(dados.get("quantidade", 10))
                except (TypeError, ValueError):
                    quantidade = 10
                game.iniciar(participantes, max(5, min(30, quantidade)))
            elif acao == "votar":
                escolhido_id = str(dados.get("jogador_id", ""))
                if game.votar(jogador_id, escolhido_id) and game.todos_votaram(conexoes.ids_conectados()):
                    game.revelar()
            elif acao == "encerrar_votacao":
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
                await voltar_todos()
                continue
            else:
                continue
            await enviar_estado()
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        print("Erro no WebSocket do Mais provável:", repr(exc))
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
        if state.fase == "votando" and game.todos_votaram(conexoes.ids_conectados()):
            game.revelar()
        await enviar_estado()

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


@router.get("/jogos/quiz")
async def pagina():
    return FileResponse(WEB_DIR / "index.html")


@router.get("/jogos/quiz/style.css")
async def estilo():
    return FileResponse(WEB_DIR / "style.css", media_type="text/css")


@router.get("/jogos/quiz/game.js")
async def javascript():
    return FileResponse(WEB_DIR / "game.js", media_type="application/javascript")


def montar_estado(destino_id):
    pergunta = (
        game.pergunta_atual() if state.jogo_iniciado or state.jogo_finalizado else None
    )
    revelar = state.fase == "resultado"
    lista = []
    for pid, cadastro in jogadores_core.jogadores.items():
        lista.append(
            {
                "id": pid,
                "nome": cadastro["nome"],
                "host": pid == jogadores_core.host_id,
                "conectado": conexoes.conectado(pid),
                "pontos": state.pontos.get(pid, 0),
                "respondeu": pid in state.respostas,
                "acertou": (
                    (state.respostas.get(pid) == pergunta["correta"])
                    if revelar and pergunta
                    else None
                ),
            }
        )
    minha_resposta = state.respostas.get(destino_id)
    maior_pontuacao = max(state.pontos.values(), default=0)
    vencedores = (
        [
            conexoes.jogador(pid)["nome"]
            for pid in state.participantes
            if conexoes.jogador(pid) and state.pontos.get(pid, 0) == maior_pontuacao
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
        "numero_pergunta": state.indice_pergunta + 1,
        "quantidade_perguntas": len(state.perguntas_partida),
        "tempo_restante": state.tempo_restante,
        "pergunta": pergunta["pergunta"] if pergunta else None,
        "alternativas": pergunta["alternativas"] if pergunta else [],
        "correta": pergunta["correta"] if revelar and pergunta else None,
        "minha_resposta": minha_resposta,
        "ja_respondi": destino_id in state.respostas,
        "ultima_pergunta": (
            bool(state.perguntas_partida)
            and state.indice_pergunta == len(state.perguntas_partida) - 1
        ),
        "vencedores": vencedores,
        "maior_pontuacao": maior_pontuacao,
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


@router.websocket("/ws/jogos/quiz")
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
                    quantidade = int(dados.get("quantidade", 10))
                    tempo = int(dados.get("tempo", 20))
                except (TypeError, ValueError):
                    await conexoes.enviar_erro(websocket, "Configuração inválida.")
                    continue
                quantidade = max(5, min(len(game.PERGUNTAS), quantidade))
                tempo = max(10, min(60, tempo))
                game.iniciar(participantes, quantidade, tempo, enviar_estado)

            elif acao == "responder":
                try:
                    alternativa = int(dados.get("alternativa"))
                except (TypeError, ValueError):
                    continue
                if game.responder(jogador_id, alternativa):
                    if game.todos_responderam(conexoes.ids_conectados()):
                        game.revelar_resultado()

            elif acao == "encerrar_respostas":
                if jogador_id != jogadores_core.host_id or state.fase != "respondendo":
                    continue
                game.revelar_resultado()

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
        print("Erro no WebSocket do Quiz:", repr(exc))
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
        if state.fase == "respondendo" and game.todos_responderam(
            conexoes.ids_conectados()
        ):
            game.revelar_resultado()
        await enviar_estado()

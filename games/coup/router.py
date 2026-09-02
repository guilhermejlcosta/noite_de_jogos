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


@router.get("/jogos/coup")
async def pagina():
    return FileResponse(WEB_DIR / "index.html")


@router.get("/jogos/coup/style.css")
async def estilo():
    return FileResponse(WEB_DIR / "style.css", media_type="text/css")


@router.get("/jogos/coup/game.js")
async def javascript():
    return FileResponse(WEB_DIR / "game.js", media_type="application/javascript")


def montar_estado(destino_id):
    lista = []
    for pid in state.participantes or jogadores_core.jogadores.keys():
        cadastro = conexoes.jogador(pid)
        if not cadastro:
            continue
        dados = state.jogadores.get(pid, {"moedas": 2, "cartas": []})
        cartas = []
        for carta in dados["cartas"]:
            cartas.append(
                {
                    "papel": (
                        carta["papel"]
                        if pid == destino_id or not carta["viva"]
                        else None
                    ),
                    "viva": carta["viva"],
                }
            )
        lista.append(
            {
                "id": pid,
                "nome": cadastro["nome"],
                "host": pid == jogadores_core.host_id,
                "conectado": conexoes.conectado(pid),
                "moedas": dados["moedas"],
                "influencias": sum(1 for c in dados["cartas"] if c["viva"]),
                "cartas": cartas,
            }
        )
    atual = game.jogador_atual_id()
    vencedor = conexoes.jogador(state.vencedor_id)
    return {
        "tipo": "estado",
        "versao": state.VERSAO,
        "jogadores": lista,
        "sou_host": destino_id == jogadores_core.host_id,
        "meu_id": destino_id,
        "jogo_iniciado": state.jogo_iniciado,
        "jogo_finalizado": state.jogo_finalizado,
        "fase": state.fase,
        "jogador_atual_id": atual,
        "acao": state.acao_pendente,
        "mensagem": state.mensagem,
        "historico": state.historico,
        "vencedor": vencedor["nome"] if vencedor else None,
        "codigo_recuperacao": (conexoes.jogador(destino_id) or {}).get("codigo"),
    }


async def enviar_estado():
    falhas = []
    for ws, pid in conexoes.itens():
        try:
            await ws.send_json(montar_estado(pid))
        except Exception:
            falhas.append(ws)
    for ws in falhas:
        conexoes.remover(ws)


@router.websocket("/ws/jogos/coup")
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
            sucesso = True
            erro = None
            if acao == "comecar":
                if jogador_id != jogadores_core.host_id:
                    sucesso = False
                    erro = "Somente o HOST pode iniciar."
                else:
                    participantes = conexoes.ids_conectados()
                    if not 2 <= len(participantes) <= 6:
                        sucesso = False
                        erro = "COUP precisa de 2 a 6 jogadores."
                    else:
                        game.iniciar(participantes)
            elif acao == "agir":
                sucesso, erro = game.agir(
                    jogador_id,
                    str(dados.get("tipo", "")),
                    str(dados.get("alvo", "")) or None,
                )
            elif acao == "continuar":
                sucesso = game.continuar(jogador_id)
            elif acao == "desafiar_acao":
                sucesso = game.desafiar_acao(jogador_id)
            elif acao == "bloquear":
                sucesso = game.bloquear(jogador_id, str(dados.get("papel", "")))
            elif acao == "aceitar_bloqueio":
                sucesso = game.aceitar_bloqueio(jogador_id)
            elif acao == "desafiar_bloqueio":
                sucesso = game.desafiar_bloqueio(jogador_id)
            elif acao == "nova_partida":
                if jogador_id != jogadores_core.host_id or not state.jogo_finalizado:
                    sucesso = False
                else:
                    game.resetar()
            elif acao == "voltar_lobby":
                if jogador_id != jogadores_core.host_id:
                    await conexoes.enviar_erro(
                        websocket, "Somente o HOST pode voltar ao Lobby."
                    )
                    continue
                lobby_core.jogo_selecionado = None
                game.resetar()
                await conexoes.enviar_voltar_lobby(state.jogadores_retornando_lobby)
                continue
            else:
                continue
            if erro:
                await conexoes.enviar_erro(websocket, erro)
            elif not sucesso:
                await conexoes.enviar_erro(
                    websocket, "Essa ação não está disponível agora."
                )
            await enviar_estado()
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        print("Erro no WebSocket do COUP:", repr(exc))
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

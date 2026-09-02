"""Gerenciamento compartilhado das conexões WebSocket de um jogo."""

from __future__ import annotations

from typing import Optional

from fastapi import WebSocket

from core import jogadores as jogadores_core


class ConexoesJogo:
    """Mantém sockets de um jogo sem misturar seu estado com o da sala."""

    def __init__(self):
        self._por_websocket: dict[WebSocket, str] = {}

    def jogador(self, jogador_id: Optional[str]):
        if not jogador_id:
            return None
        return jogadores_core.jogadores.get(jogador_id)

    def id_por_websocket(self, websocket: WebSocket) -> Optional[str]:
        return self._por_websocket.get(websocket)

    def websocket_do_jogador(self, jogador_id: Optional[str]):
        if not jogador_id:
            return None
        return next(
            (
                websocket
                for websocket, id_conectado in self._por_websocket.items()
                if id_conectado == jogador_id
            ),
            None,
        )

    def conectado(self, jogador_id: Optional[str]) -> bool:
        return self.websocket_do_jogador(jogador_id) is not None

    def ids_conectados(self) -> list[str]:
        return list(
            dict.fromkeys(
                jogador_id
                for jogador_id in self._por_websocket.values()
                if self.jogador(jogador_id)
            )
        )

    def itens(self):
        return list(self._por_websocket.items())

    async def associar(self, websocket: WebSocket, jogador: dict):
        antigo = self.websocket_do_jogador(jogador["id"])
        if antigo and antigo is not websocket:
            self.remover(antigo, marcar_offline=False)
            try:
                await antigo.close()
            except Exception:
                pass

        self._por_websocket[websocket] = jogador["id"]
        jogadores_core.websocket_para_jogador[websocket] = jogador["id"]
        jogador["websocket"] = websocket
        jogador["conectado"] = True

    def remover(self, websocket: WebSocket, marcar_offline: bool = True):
        jogador_id = self._por_websocket.pop(websocket, None)
        jogadores_core.websocket_para_jogador.pop(websocket, None)
        if not jogador_id:
            return None

        jogador = self.jogador(jogador_id)
        if marcar_offline and jogador and jogador.get("websocket") is websocket:
            jogador["websocket"] = None
            jogador["conectado"] = False
        return jogador_id

    async def enviar_sessao(self, websocket: WebSocket, jogador: dict):
        await websocket.send_json(
            {
                "tipo": "sessao",
                "token": jogador["token"],
                "nome": jogador["nome"],
                "codigo_recuperacao": jogador["codigo"],
            }
        )

    async def enviar_erro(self, websocket: WebSocket, mensagem: str):
        await websocket.send_json({"tipo": "erro", "mensagem": mensagem})

    async def enviar_voltar_lobby(self, retornando: set[str]):
        conexoes = self.itens()
        retornando.update(jogador_id for _, jogador_id in conexoes)
        for websocket, _ in conexoes:
            try:
                await websocket.send_json({"tipo": "voltar_lobby"})
            except Exception:
                pass

import unittest

from core import jogadores as jogadores_core
from core.conexoes_jogo import ConexoesJogo


class WebSocketFalso:
    def __init__(self):
        self.fechado = False
        self.mensagens = []

    async def close(self):
        self.fechado = True

    async def send_json(self, mensagem):
        self.mensagens.append(mensagem)


class TestConexoesJogo(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        jogadores_core.jogadores.clear()
        jogadores_core.websocket_para_jogador.clear()
        jogadores_core.host_id = None
        self.jogador = {
            "id": "j1",
            "nome": "Ana",
            "token": "token-1",
            "codigo": "1234",
            "websocket": None,
            "conectado": False,
        }
        jogadores_core.jogadores["j1"] = self.jogador
        self.conexoes = ConexoesJogo()

    async def test_associa_e_substitui_socket_antigo(self):
        antigo = WebSocketFalso()
        novo = WebSocketFalso()
        await self.conexoes.associar(antigo, self.jogador)
        await self.conexoes.associar(novo, self.jogador)

        self.assertTrue(antigo.fechado)
        self.assertIs(self.jogador["websocket"], novo)
        self.assertTrue(self.jogador["conectado"])
        self.assertEqual(self.conexoes.id_por_websocket(novo), "j1")
        self.assertIsNone(self.conexoes.id_por_websocket(antigo))

    async def test_fechamento_tardio_nao_desconecta_socket_novo(self):
        antigo = WebSocketFalso()
        novo = WebSocketFalso()
        await self.conexoes.associar(antigo, self.jogador)
        await self.conexoes.associar(novo, self.jogador)

        self.conexoes.remover(antigo)

        self.assertIs(self.jogador["websocket"], novo)
        self.assertTrue(self.jogador["conectado"])

    async def test_envia_sessao_sem_mudar_contrato(self):
        websocket = WebSocketFalso()
        await self.conexoes.enviar_sessao(websocket, self.jogador)
        self.assertEqual(websocket.mensagens, [{
            "tipo": "sessao",
            "token": "token-1",
            "nome": "Ana",
            "codigo_recuperacao": "1234",
        }])

    async def test_retorno_ao_lobby_marca_jogador_e_avisa_socket(self):
        websocket = WebSocketFalso()
        await self.conexoes.associar(websocket, self.jogador)
        retornando = set()
        await self.conexoes.enviar_voltar_lobby(retornando)

        self.assertEqual(retornando, {"j1"})
        self.assertEqual(websocket.mensagens[-1], {"tipo": "voltar_lobby"})


if __name__ == "__main__":
    unittest.main()

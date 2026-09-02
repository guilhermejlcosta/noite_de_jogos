import unittest
from unittest.mock import patch

from games.ito import game, state


class TestIto(unittest.TestCase):
    def tearDown(self):
        game.resetar()

    def test_fluxo_da_rodada_e_pontuacao_perfeita(self):
        with patch(
            "games.ito.game.random.sample", side_effect=[game.TEMAS[:1], [10, 50, 90]]
        ):
            game.iniciar(["a", "b", "c"], 1)

        self.assertEqual(state.fase, "pistas")
        self.assertTrue(game.enviar_pista("a", "formiga"))
        self.assertTrue(game.enviar_pista("b", "cachorro"))
        self.assertTrue(game.enviar_pista("c", "elefante"))
        self.assertEqual(state.fase, "ordenando")
        state.ordem = ["a", "b", "c"]

        self.assertTrue(game.revelar())
        self.assertEqual(state.erros_rodada, 0)
        self.assertEqual(state.pontos_rodada, 3)
        self.assertTrue(game.proxima())
        self.assertTrue(state.jogo_finalizado)

    def test_pista_so_pode_ser_enviada_uma_vez(self):
        with patch(
            "games.ito.game.random.sample", side_effect=[game.TEMAS[:1], [25, 75]]
        ):
            game.iniciar(["a", "b"], 1)
        self.assertTrue(game.enviar_pista("a", "primeira"))
        self.assertFalse(game.enviar_pista("a", "segunda"))
        self.assertEqual(state.pistas["a"], "primeira")


if __name__ == "__main__":
    unittest.main()

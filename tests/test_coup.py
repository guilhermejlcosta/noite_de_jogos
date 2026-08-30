import unittest
from unittest.mock import patch

from games.coup import game, state


class TestCoup(unittest.TestCase):
    def setUp(self):
        game.iniciar(["a", "b"])

    def tearDown(self):
        game.resetar()

    def test_renda_avanca_turno(self):
        self.assertEqual(game.jogador_atual_id(), "a")
        sucesso, _ = game.agir("a", "renda")
        self.assertTrue(sucesso)
        self.assertEqual(state.jogadores["a"]["moedas"], 3)
        self.assertEqual(game.jogador_atual_id(), "b")

    def test_golpe_custa_sete_e_remove_influencia(self):
        state.jogadores["a"]["moedas"] = 7
        with patch("games.coup.game.random.choice", return_value=game.vivos("b")[0]):
            sucesso, _ = game.agir("a", "golpe", "b")
        self.assertTrue(sucesso)
        self.assertEqual(state.jogadores["a"]["moedas"], 0)
        self.assertEqual(len(game.vivos("b")), 1)

    def test_dez_moedas_obrigam_golpe(self):
        state.jogadores["a"]["moedas"] = 10
        sucesso, erro = game.agir("a", "renda")
        self.assertFalse(sucesso)
        self.assertIn("obrigatório", erro)

    def test_cartas_tem_quantidade_correta(self):
        self.assertEqual(len(state.baralho), 11)
        self.assertEqual(len(state.jogadores["a"]["cartas"]), 2)


if __name__ == "__main__":
    unittest.main()

import json
import random
from pathlib import Path

from . import state


with open(Path(__file__).resolve().parent / "data" / "situacoes.json", "r", encoding="utf-8") as arquivo:
    SITUACOES = json.load(arquivo)


def situacao_atual():
    if not state.situacoes_partida or not 0 <= state.indice_situacao < len(state.situacoes_partida):
        return None
    return state.situacoes_partida[state.indice_situacao]


def iniciar(jogadores_ids, quantidade):
    resetar()
    state.participantes = list(jogadores_ids)
    state.situacoes_partida = random.sample(SITUACOES, quantidade)
    state.total_votos = {pid: 0 for pid in state.participantes}
    state.jogo_iniciado = True
    state.fase = "votando"


def votar(jogador_id, escolhido_id):
    if state.fase != "votando":
        return False
    if jogador_id not in state.participantes or escolhido_id not in state.participantes:
        return False
    if jogador_id in state.votos:
        return False
    state.votos[jogador_id] = escolhido_id
    return True


def todos_votaram(ids_conectados):
    esperados = set(state.participantes) & set(ids_conectados)
    return bool(esperados) and esperados.issubset(state.votos)


def revelar():
    if state.fase != "votando":
        return
    for escolhido_id in state.votos.values():
        state.total_votos[escolhido_id] = state.total_votos.get(escolhido_id, 0) + 1
    state.fase = "resultado"


def proxima():
    if state.fase != "resultado":
        return
    state.indice_situacao += 1
    if state.indice_situacao >= len(state.situacoes_partida):
        state.jogo_iniciado = False
        state.jogo_finalizado = True
        state.fase = "final"
        return
    state.votos = {}
    state.fase = "votando"


def contagem_rodada():
    contagem = {pid: 0 for pid in state.participantes}
    for escolhido_id in state.votos.values():
        contagem[escolhido_id] = contagem.get(escolhido_id, 0) + 1
    return contagem


def resetar():
    state.jogo_iniciado = False
    state.jogo_finalizado = False
    state.fase = "aguardando"
    state.participantes = []
    state.situacoes_partida = []
    state.indice_situacao = 0
    state.votos = {}
    state.total_votos = {}

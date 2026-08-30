import json
import random
from pathlib import Path

from . import state


with open(Path(__file__).resolve().parent / "data" / "temas.json", encoding="utf-8") as arquivo:
    TEMAS = json.load(arquivo)


def tema_atual():
    if not state.temas_partida or not 0 <= state.indice_rodada < len(state.temas_partida):
        return None
    return state.temas_partida[state.indice_rodada]


def _preparar_rodada():
    quantidade = len(state.participantes)
    state.numeros = dict(zip(state.participantes, random.sample(range(1, 101), quantidade)))
    state.pistas = {}
    state.ordem = list(state.participantes)
    random.shuffle(state.ordem)
    state.erros_rodada = None
    state.pontos_rodada = None
    state.fase = "pistas"


def iniciar(participantes, quantidade_rodadas):
    resetar()
    state.participantes = list(participantes)
    state.temas_partida = random.sample(TEMAS, min(quantidade_rodadas, len(TEMAS)))
    state.jogo_iniciado = True
    _preparar_rodada()


def enviar_pista(jogador_id, pista):
    pista = " ".join(str(pista).strip().split())[:80]
    if state.fase != "pistas" or jogador_id not in state.participantes or jogador_id in state.pistas or not pista:
        return False
    state.pistas[jogador_id] = pista
    if set(state.participantes).issubset(state.pistas):
        state.fase = "ordenando"
    return True


def mover(jogador_id, direcao):
    if state.fase != "ordenando" or jogador_id not in state.ordem or direcao not in (-1, 1):
        return False
    indice = state.ordem.index(jogador_id)
    destino = indice + direcao
    if not 0 <= destino < len(state.ordem):
        return False
    state.ordem[indice], state.ordem[destino] = state.ordem[destino], state.ordem[indice]
    return True


def revelar():
    if state.fase != "ordenando":
        return False
    numeros = [state.numeros[pid] for pid in state.ordem]
    state.erros_rodada = sum(1 for i in range(len(numeros)) for j in range(i + 1, len(numeros)) if numeros[i] > numeros[j])
    state.pontos_rodada = max(0, len(state.participantes) - state.erros_rodada)
    state.pontos_total += state.pontos_rodada
    state.fase = "resultado"
    return True


def proxima():
    if state.fase != "resultado":
        return False
    state.indice_rodada += 1
    if state.indice_rodada >= len(state.temas_partida):
        state.jogo_iniciado = False
        state.jogo_finalizado = True
        state.fase = "final"
    else:
        _preparar_rodada()
    return True


def resetar():
    state.jogo_iniciado = False
    state.jogo_finalizado = False
    state.fase = "aguardando"
    state.participantes = []
    state.temas_partida = []
    state.indice_rodada = 0
    state.numeros = {}
    state.pistas = {}
    state.ordem = []
    state.erros_rodada = None
    state.pontos_rodada = None
    state.pontos_total = 0

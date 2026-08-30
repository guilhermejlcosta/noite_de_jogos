import json
import random
from pathlib import Path

from . import state


IDENTIDADES_PATH = Path(__file__).resolve().parent / "data" / "identidades.json"

with open(IDENTIDADES_PATH, "r", encoding="utf-8") as arquivo:
    IDENTIDADES = json.load(arquivo)


def iniciar(jogadores_ids):
    resetar()
    ordem = list(jogadores_ids)
    random.shuffle(ordem)
    escolhas = random.sample(IDENTIDADES, len(ordem))
    state.ordem_jogadores = ordem
    state.identidades = dict(zip(ordem, escolhas))
    state.indice_atual = 0
    state.jogador_atual_id = ordem[0]
    state.jogo_iniciado = True


def avancar_turno():
    ativos = [pid for pid in state.ordem_jogadores if pid not in state.descobriram]
    if not ativos:
        state.jogo_iniciado = False
        state.jogo_finalizado = True
        state.jogador_atual_id = None
        return
    atual = state.jogador_atual_id
    if atual not in ativos:
        proximo = ativos[0]
    else:
        proximo = ativos[(ativos.index(atual) + 1) % len(ativos)]
    state.jogador_atual_id = proximo
    state.indice_atual = state.ordem_jogadores.index(proximo)


def marcar_acerto():
    atual = state.jogador_atual_id
    if atual and atual not in state.descobriram:
        state.descobriram.append(atual)
    avancar_turno()


def resetar():
    state.jogo_iniciado = False
    state.jogo_finalizado = False
    state.ordem_jogadores = []
    state.indice_atual = 0
    state.jogador_atual_id = None
    state.identidades = {}
    state.descobriram = []

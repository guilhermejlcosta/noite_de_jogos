import asyncio
import json
import random
from pathlib import Path

from . import state


with open(
    Path(__file__).resolve().parent / "data" / "temas.json", "r", encoding="utf-8"
) as arquivo:
    TEMAS = json.load(arquivo)


def sortear_tema():
    disponiveis = [tema for tema in TEMAS if tema not in state.temas_usados]
    if not disponiveis:
        state.temas_usados = []
        disponiveis = TEMAS.copy()
    tema = random.choice(disponiveis)
    state.temas_usados.append(tema)
    return tema


def cancelar_timer():
    tarefa = state.timer_task
    if tarefa and not tarefa.done():
        tarefa.cancel()
    state.timer_task = None


async def executar_timer(enviar_estado):
    try:
        while state.jogo_iniciado and state.tema_revelado and not state.turno_travado:
            if state.partida_pausada:
                await asyncio.sleep(0.2)
                continue
            await asyncio.sleep(1)
            if (
                not state.jogo_iniciado
                or not state.tema_revelado
                or state.turno_travado
            ):
                return
            if state.partida_pausada:
                continue
            state.tempo_restante = max(0, state.tempo_restante - 1)
            if state.tempo_restante == 0:
                state.turno_travado = True
            await enviar_estado()
    except asyncio.CancelledError:
        pass
    finally:
        if state.timer_task is asyncio.current_task():
            state.timer_task = None


def iniciar_timer(enviar_estado):
    cancelar_timer()
    state.timer_task = asyncio.create_task(executar_timer(enviar_estado))


def preparar_turno(jogador_conectado):
    state.tema_atual = sortear_tema()
    state.tema_revelado = False
    state.tempo_restante = state.tempo_configurado
    state.turno_travado = False
    state.partida_pausada = not jogador_conectado(state.jogador_atual_id)
    state.jogador_pausado_id = state.jogador_atual_id if state.partida_pausada else None


def iniciar(jogadores_ids, tempo, rodadas, jogador_conectado):
    resetar()
    state.tempo_configurado = tempo
    state.tempo_restante = tempo
    state.rodadas_configuradas = rodadas
    state.ordem_jogadores = list(jogadores_ids)
    random.shuffle(state.ordem_jogadores)
    state.pontos = {pid: 0 for pid in state.ordem_jogadores}
    state.jogador_atual_id = state.ordem_jogadores[0]
    state.jogo_iniciado = True
    preparar_turno(jogador_conectado)


def avancar_turno(jogador_conectado):
    cancelar_timer()
    state.indice_atual += 1
    if state.indice_atual >= len(state.ordem_jogadores):
        state.indice_atual = 0
        state.rodada_atual += 1
        if state.rodada_atual > state.rodadas_configuradas:
            state.jogo_iniciado = False
            state.jogo_finalizado = True
            state.jogador_atual_id = None
            state.tema_atual = None
            state.tema_revelado = False
            state.tempo_restante = 0
            return
    state.jogador_atual_id = state.ordem_jogadores[state.indice_atual]
    preparar_turno(jogador_conectado)


def resetar():
    cancelar_timer()
    state.jogo_iniciado = False
    state.jogo_finalizado = False
    state.ordem_jogadores = []
    state.indice_atual = 0
    state.jogador_atual_id = None
    state.rodada_atual = 1
    state.tema_atual = None
    state.tema_revelado = False
    state.temas_usados = []
    state.pontos = {}
    state.tempo_restante = state.tempo_configurado
    state.turno_travado = False
    state.partida_pausada = False
    state.jogador_pausado_id = None

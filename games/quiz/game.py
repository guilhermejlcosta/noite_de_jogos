import asyncio
import json
import random
from pathlib import Path

from . import state


with open(
    Path(__file__).resolve().parent / "data" / "perguntas.json", "r", encoding="utf-8"
) as arquivo:
    PERGUNTAS = json.load(arquivo)


def pergunta_atual():
    if (
        not state.perguntas_partida
        or state.indice_pergunta < 0
        or state.indice_pergunta >= len(state.perguntas_partida)
    ):
        return None
    return state.perguntas_partida[state.indice_pergunta]


def cancelar_timer():
    tarefa = state.timer_task
    if tarefa and tarefa is not asyncio.current_task() and not tarefa.done():
        tarefa.cancel()
    state.timer_task = None


def revelar_resultado():
    if state.fase != "respondendo":
        return
    cancelar_timer()
    correta = pergunta_atual()["correta"]
    for jogador_id, resposta in state.respostas.items():
        if resposta == correta:
            state.pontos[jogador_id] = state.pontos.get(jogador_id, 0) + 1
    state.fase = "resultado"
    state.tempo_restante = 0


async def executar_timer(enviar_estado):
    try:
        while (
            state.jogo_iniciado
            and state.fase == "respondendo"
            and state.tempo_restante > 0
        ):
            await asyncio.sleep(1)
            if not state.jogo_iniciado or state.fase != "respondendo":
                return
            state.tempo_restante -= 1
            if state.tempo_restante == 0:
                revelar_resultado()
            await enviar_estado()
    except asyncio.CancelledError:
        pass
    finally:
        if state.timer_task is asyncio.current_task():
            state.timer_task = None


def iniciar_timer(enviar_estado):
    cancelar_timer()
    state.timer_task = asyncio.create_task(executar_timer(enviar_estado))


def iniciar(jogadores_ids, quantidade, tempo, enviar_estado):
    resetar()
    state.participantes = list(jogadores_ids)
    state.quantidade_configurada = quantidade
    state.tempo_configurado = tempo
    state.perguntas_partida = random.sample(PERGUNTAS, quantidade)
    state.pontos = {pid: 0 for pid in state.participantes}
    state.jogo_iniciado = True
    preparar_pergunta(enviar_estado)


def preparar_pergunta(enviar_estado):
    state.fase = "respondendo"
    state.respostas = {}
    state.tempo_restante = state.tempo_configurado
    iniciar_timer(enviar_estado)


def responder(jogador_id, alternativa):
    if state.fase != "respondendo" or jogador_id not in state.participantes:
        return False
    if jogador_id in state.respostas or alternativa not in range(4):
        return False
    state.respostas[jogador_id] = alternativa
    return True


def todos_responderam(ids_conectados):
    esperados = set(state.participantes) & set(ids_conectados)
    return bool(esperados) and esperados.issubset(state.respostas)


def proxima(enviar_estado):
    if state.fase != "resultado":
        return
    state.indice_pergunta += 1
    if state.indice_pergunta >= len(state.perguntas_partida):
        state.jogo_iniciado = False
        state.jogo_finalizado = True
        state.fase = "final"
        return
    preparar_pergunta(enviar_estado)


def resetar():
    cancelar_timer()
    state.jogo_iniciado = False
    state.jogo_finalizado = False
    state.fase = "aguardando"
    state.participantes = []
    state.perguntas_partida = []
    state.indice_pergunta = 0
    state.tempo_restante = state.tempo_configurado
    state.respostas = {}
    state.pontos = {}

import asyncio
import json
import random
import unicodedata
from pathlib import Path

from . import state


with open(Path(__file__).resolve().parent / "data" / "categorias.json", "r", encoding="utf-8") as arquivo:
    CATEGORIAS = json.load(arquivo)

LETRAS = list("ABCDEFGHIJKLMNOPRSTUV")


def normalizar(texto):
    texto = unicodedata.normalize("NFD", str(texto).strip().casefold())
    return "".join(char for char in texto if unicodedata.category(char) != "Mn")


def cancelar_timer():
    tarefa = state.timer_task
    if tarefa and tarefa is not asyncio.current_task() and not tarefa.done():
        tarefa.cancel()
    state.timer_task = None


async def executar_timer(enviar_estado):
    try:
        while state.jogo_iniciado and state.fase == "preenchendo" and state.tempo_restante > 0:
            await asyncio.sleep(1)
            if not state.jogo_iniciado or state.fase != "preenchendo":
                return
            state.tempo_restante -= 1
            if state.tempo_restante == 0:
                encerrar_rodada()
            await enviar_estado()
    except asyncio.CancelledError:
        pass
    finally:
        if state.timer_task is asyncio.current_task():
            state.timer_task = None


def iniciar_timer(enviar_estado):
    cancelar_timer()
    state.timer_task = asyncio.create_task(executar_timer(enviar_estado))


def sortear_letra():
    disponiveis = [letra for letra in LETRAS if letra not in state.letras_usadas]
    if not disponiveis:
        state.letras_usadas = []
        disponiveis = LETRAS.copy()
    letra = random.choice(disponiveis)
    state.letras_usadas.append(letra)
    return letra


def iniciar(jogadores_ids, rodadas, tempo, enviar_estado):
    resetar()
    state.participantes = list(jogadores_ids)
    state.rodadas_configuradas = rodadas
    state.tempo_configurado = tempo
    state.pontos_totais = {pid: 0 for pid in state.participantes}
    state.jogo_iniciado = True
    preparar_rodada(enviar_estado)


def preparar_rodada(enviar_estado):
    state.fase = "preenchendo"
    state.letra_atual = sortear_letra()
    state.tempo_restante = state.tempo_configurado
    state.respostas = {}
    state.invalidas = set()
    state.pontos_rodada = {pid: 0 for pid in state.participantes}
    iniciar_timer(enviar_estado)


def salvar_respostas(jogador_id, respostas):
    if state.fase != "preenchendo" or jogador_id not in state.participantes:
        return False
    categorias_ids = {categoria["id"] for categoria in CATEGORIAS}
    limpas = {cid: str(respostas.get(cid, "")).strip()[:60] for cid in categorias_ids}
    state.respostas[jogador_id] = limpas
    return True


def encerrar_rodada():
    if state.fase != "preenchendo":
        return
    cancelar_timer()
    state.fase = "revisao"
    state.tempo_restante = 0
    calcular_pontos()


def alternar_invalida(jogador_id, categoria_id):
    if state.fase != "revisao" or jogador_id not in state.participantes:
        return
    chave = (jogador_id, categoria_id)
    if chave in state.invalidas:
        state.invalidas.remove(chave)
    else:
        state.invalidas.add(chave)
    calcular_pontos()


def calcular_pontos():
    state.pontos_rodada = {pid: 0 for pid in state.participantes}
    for categoria in CATEGORIAS:
        cid = categoria["id"]
        valores = {}
        for pid in state.participantes:
            resposta = state.respostas.get(pid, {}).get(cid, "")
            valor = normalizar(resposta)
            valida = bool(valor) and valor.startswith(state.letra_atual.casefold()) and (pid, cid) not in state.invalidas
            if valida:
                valores[pid] = valor
        for pid, valor in valores.items():
            repeticoes = sum(1 for outro in valores.values() if outro == valor)
            state.pontos_rodada[pid] += 5 if repeticoes > 1 else 10


def proxima(enviar_estado):
    if state.fase != "revisao":
        return
    for pid in state.participantes:
        state.pontos_totais[pid] = state.pontos_totais.get(pid, 0) + state.pontos_rodada.get(pid, 0)
    if state.rodada_atual >= state.rodadas_configuradas:
        state.jogo_iniciado = False
        state.jogo_finalizado = True
        state.fase = "final"
        return
    state.rodada_atual += 1
    preparar_rodada(enviar_estado)


def resetar():
    cancelar_timer()
    state.jogo_iniciado = False
    state.jogo_finalizado = False
    state.fase = "aguardando"
    state.participantes = []
    state.rodada_atual = 1
    state.letra_atual = None
    state.letras_usadas = []
    state.respostas = {}
    state.invalidas = set()
    state.pontos_rodada = {}
    state.pontos_totais = {}
    state.tempo_restante = state.tempo_configurado

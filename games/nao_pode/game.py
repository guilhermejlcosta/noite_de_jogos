import asyncio
import json
import random

from pathlib import Path

import core.jogadores as jogadores_core

import games.nao_pode.state as state


# ============================================================
# CARTAS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

CARTAS_PATH = (
    BASE_DIR
    / "data"
    / "cartas.json"
)


with open(
    CARTAS_PATH,
    "r",
    encoding="utf-8"
) as arquivo:

    cartas = json.load(
        arquivo
    )


def sortear_carta():

    disponiveis = [

        carta

        for carta in cartas

        if carta
        not in state.cartas_usadas

    ]


    if not disponiveis:

        state.cartas_usadas = []

        disponiveis = (
            cartas.copy()
        )


    carta = random.choice(
        disponiveis
    )


    state.cartas_usadas.append(
        carta
    )


    return carta


# ============================================================
# TIMER
# ============================================================

def cancelar_timer():

    if (

        state.timer_task

        and

        not state.timer_task.done()

    ):

        state.timer_task.cancel()


    state.timer_task = None


async def executar_cronometro(
    enviar_estado_callback
):

    try:

        while (

            state.jogo_iniciado

            and

            not state.jogo_finalizado

            and

            state.carta_revelada

            and

            not state.turno_travado

            and

            not state.partida_pausada

            and

            state.tempo_restante > 0

        ):

            await asyncio.sleep(
                1
            )


            if (

                not state.jogo_iniciado

                or

                state.jogo_finalizado

                or

                not state.carta_revelada

                or

                state.turno_travado

                or

                state.partida_pausada

            ):

                break


            state.tempo_restante -= 1


            if (
                state.tempo_restante
                <= 0
            ):

                state.tempo_restante = 0

                state.turno_travado = True


            await enviar_estado_callback()


    except asyncio.CancelledError:

        pass


    finally:

        state.timer_task = None


def iniciar_timer(
    enviar_estado_callback
):

    cancelar_timer()


    if (

        state.jogo_iniciado

        and

        not state.jogo_finalizado

        and

        state.carta_revelada

        and

        not state.turno_travado

        and

        not state.partida_pausada

        and

        state.tempo_restante > 0

    ):

        state.timer_task = (
            asyncio.create_task(

                executar_cronometro(
                    enviar_estado_callback
                )

            )
        )


# ============================================================
# DESCONEXÃO
# ============================================================

def pausar_turno_por_desconexao(
    player_id
):

    if (

        state.jogo_iniciado

        and

        not state.jogo_finalizado

        and

        state.jogador_atual_id
        ==
        player_id

        and

        not state.turno_travado

    ):

        cancelar_timer()

        state.partida_pausada = True

        state.jogador_pausado_id = (
            player_id
        )


def verificar_pausa():

    if (

        state.jogo_iniciado

        and

        not state.jogo_finalizado

        and

        state.jogador_atual_id

        and

        not jogadores_core
        .jogador_conectado(
            state.jogador_atual_id
        )

        and

        not state.turno_travado

    ):

        cancelar_timer()

        state.partida_pausada = True

        state.jogador_pausado_id = (
            state.jogador_atual_id
        )

    else:

        state.partida_pausada = False

        state.jogador_pausado_id = None


def retomar_jogador(
    player_id,
    enviar_estado_callback
):

    if (

        state.jogo_iniciado

        and

        not state.jogo_finalizado

        and

        state.jogador_atual_id
        ==
        player_id

        and

        state.partida_pausada

        and

        state.jogador_pausado_id
        ==
        player_id

    ):

        state.partida_pausada = False

        state.jogador_pausado_id = None


        if state.carta_revelada:

            iniciar_timer(
                enviar_estado_callback
            )


# ============================================================
# TURNO
# ============================================================

def preparar_turno():

    state.carta_atual = (
        sortear_carta()
    )

    state.carta_revelada = False

    state.tempo_restante = (
        state.tempo_configurado
    )

    state.turno_travado = False


    verificar_pausa()


async def avancar_turno():

    cancelar_timer()


    state.indice_atual += 1


    if (
        state.indice_atual
        >=
        len(
            state.ordem_jogadores
        )
    ):

        state.indice_atual = 0


        if (
            state.rodada_atual
            >=
            state.rodadas_configuradas
        ):

            state.jogo_finalizado = True

            state.jogador_atual_id = None

            state.carta_atual = None

            state.carta_revelada = False

            state.tempo_restante = 0

            state.turno_travado = True

            state.partida_pausada = False

            state.jogador_pausado_id = None

            return


        state.rodada_atual += 1


    state.jogador_atual_id = (
        state.ordem_jogadores[
            state.indice_atual
        ]
    )


    preparar_turno()


# ============================================================
# NOVA PARTIDA
# ============================================================

def resetar_para_nova_partida():

    cancelar_timer()


    state.jogo_iniciado = False

    state.jogo_finalizado = False


    state.ordem_jogadores = []

    state.indice_atual = 0

    state.jogador_atual_id = None


    state.rodada_atual = 1


    state.carta_atual = None

    state.carta_revelada = False

    state.cartas_usadas = []


    state.tempo_restante = (
        state.tempo_configurado
    )

    state.turno_travado = False


    state.partida_pausada = False

    state.jogador_pausado_id = None


    remover = [

        player_id

        for (
            player_id,
            jogador
        )

        in jogadores_core
        .jogadores
        .items()

        if not jogador[
            "conectado"
        ]

    ]


    for player_id in remover:

        jogadores_core.jogadores.pop(player_id, None)


    for jogador in (
        jogadores_core
        .jogadores
        .values()
    ):

        jogador["pontos"] = 0


    jogadores_core.escolher_novo_host()
import random


# ============================================================
# JOGADORES
# ============================================================

jogadores = {}

websocket_para_jogador = {}

host_id = None


# ============================================================
# RECUPERAÇÃO
# ============================================================

def gerar_codigo_recuperacao():

    usados = {
        jogador["codigo"]
        for jogador in jogadores.values()
    }

    while True:

        codigo = (
            f"{random.randint(0, 9999):04d}"
        )

        if codigo not in usados:
            return codigo


def jogador_por_token(
    token
):

    for jogador in jogadores.values():

        if jogador["token"] == token:
            return jogador

    return None


def jogador_por_codigo(
    codigo
):

    for jogador in jogadores.values():

        if jogador["codigo"] == codigo:
            return jogador

    return None


# ============================================================
# CONSULTAS
# ============================================================

def nome_jogador(
    player_id
):

    jogador = jogadores.get(
        player_id
    )

    if jogador:
        return jogador["nome"]

    return None


def jogador_conectado(
    player_id
):

    jogador = jogadores.get(
        player_id
    )

    return bool(

        jogador

        and

        jogador["conectado"]

        and

        jogador["websocket"]
        is not None

    )


def ids_jogadores_conectados():

    return [

        player_id

        for (
            player_id,
            jogador
        )

        in jogadores.items()

        if jogador["conectado"]

    ]


# ============================================================
# WEBSOCKET
# ============================================================

def associar_websocket(
    websocket,
    jogador
):

    jogador["conectado"] = True

    jogador["websocket"] = websocket

    websocket_para_jogador[
        websocket
    ] = jogador["id"]


def desassociar_websocket(
    websocket
):

    player_id = (
        websocket_para_jogador
        .pop(
            websocket,
            None
        )
    )

    if not player_id:
        return None

    jogador = jogadores.get(
        player_id
    )

    if (

        jogador

        and

        jogador["websocket"]
        is websocket

    ):

        jogador["conectado"] = False

        jogador["websocket"] = None

    return player_id


async def fechar_conexao_antiga(
    jogador,
    nova_conexao
):

    antiga = jogador.get(
        "websocket"
    )

    if (

        antiga

        and

        antiga is not nova_conexao

    ):

        websocket_para_jogador.pop(
            antiga,
            None
        )

        try:

            await antiga.close()

        except Exception:

            pass


async def enviar_sessao(
    websocket,
    jogador
):

    await websocket.send_json({

        "tipo":
            "sessao",

        "token":
            jogador["token"],

        "nome":
            jogador["nome"],

        "codigo_recuperacao":
            jogador["codigo"]

    })


# ============================================================
# HOST
# ============================================================

def escolher_novo_host():

    global host_id

    if jogador_conectado(
        host_id
    ):

        return

    conectados = (
        ids_jogadores_conectados()
    )

    host_id = (

        conectados[0]

        if conectados

        else None

    )
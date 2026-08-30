import uuid

from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
)

import core.jogadores as jogadores_core


router = APIRouter()


# ============================================================
# ESTADO DO LOBBY
# ============================================================

jogo_selecionado = None


# ============================================================
# JOGOS DISPONÍVEIS
# ============================================================

JOGOS = [

    {
        "id": "nao_pode",
        "nome": "Não Pode",
        "icone": "🚫",
        "descricao": "Explique a palavra sem usar as palavras proibidas.",
        "disponivel": True,
        "url": "/jogos/nao-pode",
    },

    {
        "id": "mimica",
        "nome": "Mímica",
        "icone": "🎭",
        "descricao": "Faça sua equipe adivinhar sem falar.",
        "disponivel": True,
        "url": "/jogos/mimica",
    },

    {
        "id": "quem_sou_eu",
        "nome": "Quem Sou Eu?",
        "icone": "🤔",
        "descricao": "Descubra quem ou o que você é.",
        "disponivel": True,
        "url": "/jogos/quem-sou-eu",
    },

    {
        "id": "mais_provavel",
        "nome": "Mais provável de...",
        "icone": "👉",
        "descricao": "Vote em quem mais combina com a situação.",
        "disponivel": True,
        "url": "/jogos/mais-provavel",
    },

    {
        "id": "stop",
        "nome": "Stop / Adedonha",
        "icone": "✏️",
        "descricao": "Categorias, letras e respostas contra o tempo.",
        "disponivel": True,
        "url": "/jogos/stop",
    },

    {
        "id": "quiz",
        "nome": "Quiz",
        "icone": "🧠",
        "descricao": "Perguntas, respostas e pontuação.",
        "disponivel": True,
        "url": "/jogos/quiz",
    },

    {
        "id": "ito",
        "nome": "ITO",
        "icone": "🎯",
        "descricao": "Dê pistas para representar seu número secreto.",
        "disponivel": True,
        "url": "/jogos/ito",
    },

    {
        "id": "coup",
        "nome": "COUP",
        "icone": "🃏",
        "descricao": "Blefe, personagens e desafios.",
        "disponivel": True,
        "url": "/jogos/coup",
    },

]


# Texto exibido pelo guia de regras no lobby. Mantê-lo no servidor
# garante que todos os aparelhos recebam a mesma versão das regras.
REGRAS_JOGOS = {
    "nao_pode": {
        "objetivo": "Faça o jogador da vez adivinhar a palavra da carta sem dizer nenhuma das palavras proibidas.",
        "como_jogar": ["O jogador da vez revela sua carta.", "Ele explica a palavra durante o tempo da rodada.", "O HOST marca acerto ou erro e o turno avança."],
        "exemplo": "Para a palavra 'Praia', se 'mar' e 'areia' forem proibidas, será preciso descrevê-la usando outras ideias.",
    },
    "mimica": {
        "objetivo": "Faça os outros jogadores descobrirem o tema usando apenas gestos.",
        "como_jogar": ["O jogador da vez vê o tema secreto.", "Ele faz a mímica sem falar, escrever ou apontar letras.", "O HOST registra o resultado antes do tempo terminar."],
        "exemplo": "Para representar 'nadar', imite os movimentos dos braços sem dizer nenhuma palavra.",
    },
    "quem_sou_eu": {
        "objetivo": "Descubra a identidade secreta atribuída a você.",
        "como_jogar": ["Cada pessoa vê as identidades dos outros, mas não a própria.", "Faça perguntas que possam ser respondidas com sim ou não.", "Use as respostas para descobrir quem ou o que você é."],
        "exemplo": "Pergunte: 'Sou uma pessoa real?' ou 'Apareço em filmes?'.",
    },
    "mais_provavel": {
        "objetivo": "Vote em quem mais combina com cada situação apresentada.",
        "como_jogar": ["Leia a situação da rodada.", "Cada pessoa vota secretamente em um jogador.", "Os votos são revelados juntos e acumulados até o resultado final."],
        "exemplo": "Em 'Quem é mais provável de esquecer o próprio aniversário?', escolha a pessoa que mais combina.",
    },
    "stop": {
        "objetivo": "Preencha as categorias com respostas iniciadas pela letra sorteada.",
        "como_jogar": ["Uma letra é sorteada para todos.", "Preencha uma resposta válida em cada categoria.", "Resposta única vale 10, repetida vale 5 e inválida vale 0 pontos."],
        "exemplo": "Com a letra B: Nome = Bruno, Fruta = Banana, Marca = BMW.",
    },
    "quiz": {
        "objetivo": "Responda corretamente mais perguntas e alcance a maior pontuação.",
        "como_jogar": ["Uma pergunta e suas alternativas aparecem na tela.", "Cada jogador escolhe sua resposta.", "O jogo revela a correta, contabiliza os pontos e avança."],
        "exemplo": "Se a pergunta for 'Qual é a capital do Canadá?', selecione 'Ottawa'.",
    },
    "ito": {
        "objetivo": "Organizem cooperativamente as pistas seguindo os números secretos, do menor para o maior.",
        "como_jogar": ["Cada pessoa recebe um número secreto entre 1 e 100.", "Dê uma pista adequada ao tema e à posição do seu número na escala.", "O HOST organiza as pistas; depois os números são revelados e o jogo calcula os erros."],
        "exemplo": "No tema 'Comidas: ruim → deliciosa', o número 90 pode receber a pista 'pizza'.",
    },
    "coup": {
        "objetivo": "Seja a última pessoa com pelo menos uma influência viva.",
        "como_jogar": ["Use ações de personagens, mesmo sem possuir a carta: blefar é permitido.", "Outros podem desafiar sua declaração ou bloquear determinadas ações.", "Quem perde um desafio ou sofre um ataque perde influência; com 10 moedas, o Golpe é obrigatório."],
        "exemplo": "Você pode declarar Duque para receber 3 moedas. Se for desafiado e não tiver um Duque, perde uma influência.",
    },
}

for jogo in JOGOS:
    jogo["regras"] = REGRAS_JOGOS.get(jogo["id"])


# ============================================================
# CONSULTAS
# ============================================================

def obter_jogo(
    jogo_id
):

    for jogo in JOGOS:

        if (
            jogo["id"]
            ==
            jogo_id
        ):

            return jogo

    return None


# ============================================================
# ESTADO DO LOBBY
# ============================================================

async def enviar_estado_lobby():

    falhas = []


    for (
        viewer_id,
        viewer
    ) in list(
        jogadores_core
        .jogadores
        .items()
    ):

        websocket = viewer.get(
            "websocket"
        )


        if (

            not viewer[
                "conectado"
            ]

            or

            websocket is None

        ):

            continue


        lista_jogadores = []


        for (
            player_id,
            jogador
        ) in (
            jogadores_core
            .jogadores
            .items()
        ):

            item = {

                "id":
                    player_id,

                "nome":
                    jogador["nome"],

                "host":
                    (
                        player_id
                        ==
                        jogadores_core.host_id
                    ),

                "conectado":
                    jogador[
                        "conectado"
                    ],

            }


            lista_jogadores.append(
                item
            )


        estado = {

            "tipo":
                "estado_lobby",

            "jogadores":
                lista_jogadores,

            "sou_host":
                (
                    viewer_id
                    ==
                    jogadores_core.host_id
                ),

            "codigo_recuperacao":
                viewer[
                    "codigo"
                ],

            "jogos":
                JOGOS,

            "jogo_selecionado":
                jogo_selecionado,

        }


        try:

            await websocket.send_json(
                estado
            )

        except Exception:

            falhas.append(
                websocket
            )


    # Remove sockets que falharam.

    for websocket in falhas:

        jogadores_core.desassociar_websocket(
            websocket
        )


# ============================================================
# WEBSOCKET DO LOBBY
# ============================================================

@router.websocket(
    "/ws/lobby"
)
async def websocket_lobby(
    websocket: WebSocket
):

    global jogo_selecionado


    await websocket.accept()


    try:

        while True:

            dados = (
                await websocket
                .receive_json()
            )


            acao = dados.get(
                "acao"
            )


            # =================================================
            # ENTRAR
            # =================================================

            if acao == "entrar":

                # Não deixa jogador novo entrar
                # enquanto algum jogo já está aberto.

                if (
                    jogo_selecionado
                    is not None
                ):

                    await websocket.send_json({

                        "tipo":
                            "erro",

                        "mensagem":
                            (
                                "Um jogo já está em andamento."
                            )

                    })

                    continue


                nome = str(
                    dados.get(
                        "nome",
                        ""
                    )
                ).strip()


                if not nome:

                    continue


                nomes_existentes = [

                    jogador[
                        "nome"
                    ].lower()

                    for jogador
                    in jogadores_core
                    .jogadores
                    .values()

                ]


                if (
                    nome.lower()
                    in nomes_existentes
                ):

                    await websocket.send_json({

                        "tipo":
                            "erro",

                        "mensagem":
                            (
                                "Esse nome já está sendo usado."
                            )

                    })

                    continue


                player_id = (
                    uuid.uuid4().hex
                )


                jogador = {

                    "id":
                        player_id,

                    "nome":
                        nome,

                    "token":
                        uuid.uuid4().hex,

                    "codigo":
                        jogadores_core
                        .gerar_codigo_recuperacao(),

                    "pontos":
                        0,

                    "conectado":
                        True,

                    "websocket":
                        websocket,

                }


                jogadores_core.jogadores[
                    player_id
                ] = jogador


                jogadores_core.associar_websocket(
                    websocket,
                    jogador
                )


                if (
                    jogadores_core.host_id
                    is None
                ):

                    jogadores_core.host_id = (
                        player_id
                    )


                print(
                    f"[LOBBY] "
                    f"{nome} entrou. "
                    f"Código: "
                    f"{jogador['codigo']}"
                )


                await jogadores_core.enviar_sessao(
                    websocket,
                    jogador
                )


                await enviar_estado_lobby()


            # =================================================
            # RECONECTAR
            # =================================================

            elif (
                acao
                ==
                "reconectar"
            ):

                token = str(
                    dados.get(
                        "token",
                        ""
                    )
                ).strip()


                jogador = (
                    jogadores_core
                    .jogador_por_token(
                        token
                    )
                )


                if not jogador:

                    await websocket.send_json({

                        "tipo":
                            "sessao_invalida"

                    })

                    continue


                await jogadores_core.fechar_conexao_antiga(
                    jogador,
                    websocket
                )


                jogadores_core.associar_websocket(
                    websocket,
                    jogador
                )


                if (
                    jogadores_core.host_id
                    is None
                ):

                    jogadores_core.host_id = (
                        jogador["id"]
                    )


                await jogadores_core.enviar_sessao(
                    websocket,
                    jogador
                )


                await enviar_estado_lobby()


            # =================================================
            # RECUPERAR PELO CÓDIGO
            # =================================================

            elif (
                acao
                ==
                "recuperar_codigo"
            ):

                codigo = str(
                    dados.get(
                        "codigo",
                        ""
                    )
                ).strip()


                jogador = (
                    jogadores_core
                    .jogador_por_codigo(
                        codigo
                    )
                )


                if not jogador:

                    await websocket.send_json({

                        "tipo":
                            "erro",

                        "mensagem":
                            (
                                "Código de recuperação "
                                "não encontrado."
                            )

                    })

                    continue


                await jogadores_core.fechar_conexao_antiga(
                    jogador,
                    websocket
                )


                # Ao recuperar por código,
                # gera um novo token.

                jogador["token"] = (
                    uuid.uuid4().hex
                )


                jogadores_core.associar_websocket(
                    websocket,
                    jogador
                )


                if (
                    jogadores_core.host_id
                    is None
                ):

                    jogadores_core.host_id = (
                        jogador["id"]
                    )


                await jogadores_core.enviar_sessao(
                    websocket,
                    jogador
                )


                await enviar_estado_lobby()


            # =================================================
            # SELECIONAR JOGO
            # =================================================

            elif (
                acao
                ==
                "selecionar_jogo"
            ):

                player_id = (
                    jogadores_core
                    .websocket_para_jogador
                    .get(
                        websocket
                    )
                )


                # Somente HOST.

                if (
                    player_id
                    !=
                    jogadores_core.host_id
                ):

                    continue


                jogo_id = str(
                    dados.get(
                        "jogo",
                        ""
                    )
                ).strip()


                jogo = obter_jogo(
                    jogo_id
                )


                if not jogo:

                    continue


                if not jogo[
                    "disponivel"
                ]:

                    continue


                conectados = (
                    jogadores_core
                    .ids_jogadores_conectados()
                )


                if (
                    len(conectados)
                    <
                    2
                ):

                    await websocket.send_json({

                        "tipo":
                            "erro",

                        "mensagem":
                            (
                                "São necessários pelo menos "
                                "2 jogadores."
                            )

                    })

                    continue


                jogo_selecionado = (
                    jogo_id
                )


                print(
                    f"[LOBBY] "
                    f"Jogo selecionado: "
                    f"{jogo_id}"
                )


                await enviar_estado_lobby()


    # ========================================================
    # DESCONECTOU DO LOBBY
    # ========================================================

    except WebSocketDisconnect:

        player_id = (
            jogadores_core
            .desassociar_websocket(
                websocket
            )
        )


        if not player_id:

            return


        # Se nenhum jogo foi escolhido,
        # significa que a pessoa realmente
        # saiu do lobby.
        #
        # Então removemos da sala.

        if (
            jogo_selecionado
            is None
        ):

            era_host = (
                player_id
                ==
                jogadores_core.host_id
            )


            jogadores_core.jogadores.pop(
                player_id,
                None
            )


            if era_host:

                jogadores_core.escolher_novo_host()


            await enviar_estado_lobby()


        # Se já existe jogo selecionado,
        # NÃO removemos.
        #
        # O navegador está apenas saindo
        # do lobby para entrar no jogo.

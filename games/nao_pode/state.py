VERSAO = "0.10-modular"

jogo_iniciado = False
jogo_finalizado = False

ordem_jogadores = []
indice_atual = 0
jogador_atual_id = None

tempo_configurado = 60
rodadas_configuradas = 5
rodada_atual = 1

carta_atual = None
carta_revelada = False
cartas_usadas = []

tempo_restante = 60
turno_travado = False

partida_pausada = False
jogador_pausado_id = None

timer_task = None


# ============================================================
# RETORNO PARA NOITE DE JOGOS
# ============================================================

# Quando o HOST manda todos voltarem ao lobby,
# guardamos temporariamente os IDs dos jogadores.
#
# Isso evita que a desconexão causada pelo redirecionamento
# seja interpretada como uma queda real do jogador.
#
# Principalmente:
# o HOST não perde o cargo durante o redirecionamento.

jogadores_retornando_lobby = set()
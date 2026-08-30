VERSAO = "0.1"

jogo_iniciado = False
jogo_finalizado = False
fase = "aguardando"
participantes = []
rodada_atual = 1
rodadas_configuradas = 3
tempo_configurado = 90
tempo_restante = 90
letra_atual = None
letras_usadas = []
respostas = {}
invalidas = set()
pontos_rodada = {}
pontos_totais = {}
timer_task = None
jogadores_retornando_lobby = set()

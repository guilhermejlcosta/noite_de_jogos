VERSAO = "0.1"

jogo_iniciado = False
jogo_finalizado = False
fase = "aguardando"
participantes = []
perguntas_partida = []
indice_pergunta = 0
quantidade_configurada = 10
tempo_configurado = 20
tempo_restante = 20
respostas = {}
pontos = {}
timer_task = None
jogadores_retornando_lobby = set()

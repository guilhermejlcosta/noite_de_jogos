import random

from . import state


PAPEIS = ("Duque", "Assassino", "Capitão", "Embaixador", "Condessa")
ACOES = {
    "renda": {"nome": "Renda", "alvo": False},
    "ajuda": {"nome": "Ajuda externa", "alvo": False},
    "imposto": {"nome": "Imposto", "alvo": False, "papel": "Duque"},
    "roubar": {"nome": "Roubar", "alvo": True, "papel": "Capitão"},
    "trocar": {"nome": "Trocar influências", "alvo": False, "papel": "Embaixador"},
    "assassinar": {"nome": "Assassinar", "alvo": True, "papel": "Assassino"},
    "golpe": {"nome": "Golpe", "alvo": True},
}


def vivos(jogador_id):
    return [c for c in state.jogadores.get(jogador_id, {}).get("cartas", []) if c["viva"]]


def ativo(jogador_id):
    return bool(vivos(jogador_id))


def jogador_atual_id():
    if not state.participantes:
        return None
    return state.participantes[state.indice_turno]


def _registrar(texto):
    state.mensagem = texto
    state.historico.append(texto)
    state.historico = state.historico[-8:]


def iniciar(participantes):
    resetar()
    state.participantes = list(participantes)
    state.baralho = [papel for papel in PAPEIS for _ in range(3)]
    random.shuffle(state.baralho)
    state.jogadores = {
        pid: {"moedas": 2, "cartas": [{"papel": state.baralho.pop(), "viva": True} for _ in range(2)]}
        for pid in state.participantes
    }
    state.jogo_iniciado = True
    state.fase = "turno"
    _registrar("A partida começou.")


def _perder_influencia(jogador_id):
    cartas = vivos(jogador_id)
    if not cartas:
        return None
    carta = random.choice(cartas)
    carta["viva"] = False
    return carta["papel"]


def _comprovar(jogador_id, papel):
    carta = next((c for c in vivos(jogador_id) if c["papel"] == papel), None)
    if not carta:
        return False
    state.baralho.append(carta["papel"])
    random.shuffle(state.baralho)
    carta["papel"] = state.baralho.pop()
    return True


def _verificar_fim():
    sobreviventes = [pid for pid in state.participantes if ativo(pid)]
    if len(sobreviventes) <= 1:
        state.jogo_iniciado = False
        state.jogo_finalizado = True
        state.fase = "final"
        state.vencedor_id = sobreviventes[0] if sobreviventes else None
        return True
    return False


def _encerrar_turno():
    state.acao_pendente = None
    if _verificar_fim():
        return
    for _ in state.participantes:
        state.indice_turno = (state.indice_turno + 1) % len(state.participantes)
        if ativo(jogador_atual_id()):
            break
    state.fase = "turno"


def _executar():
    acao = state.acao_pendente
    if not acao:
        return
    ator, alvo, tipo = acao["ator"], acao.get("alvo"), acao["tipo"]
    if tipo == "ajuda":
        state.jogadores[ator]["moedas"] += 2
    elif tipo == "imposto":
        state.jogadores[ator]["moedas"] += 3
    elif tipo == "roubar" and ativo(alvo):
        valor = min(2, state.jogadores[alvo]["moedas"])
        state.jogadores[alvo]["moedas"] -= valor
        state.jogadores[ator]["moedas"] += valor
    elif tipo == "trocar":
        cartas = vivos(ator)
        papeis = [c["papel"] for c in cartas]
        papeis.extend(state.baralho.pop() for _ in range(min(2, len(state.baralho))))
        random.shuffle(papeis)
        for carta in cartas:
            carta["papel"] = papeis.pop()
        state.baralho.extend(papeis)
        random.shuffle(state.baralho)
    elif tipo in ("assassinar", "golpe") and ativo(alvo):
        revelada = _perder_influencia(alvo)
        _registrar(f"Uma influência de {alvo} foi perdida ({revelada}).")
    _encerrar_turno()


def agir(ator, tipo, alvo=None):
    if state.fase != "turno" or ator != jogador_atual_id() or tipo not in ACOES:
        return False, "Ação indisponível."
    moedas = state.jogadores[ator]["moedas"]
    if moedas >= 10 and tipo != "golpe":
        return False, "Com 10 moedas ou mais, o Golpe é obrigatório."
    if ACOES[tipo]["alvo"] and (alvo == ator or not ativo(alvo)):
        return False, "Escolha um adversário ativo."
    custos = {"assassinar": 3, "golpe": 7}
    if moedas < custos.get(tipo, 0):
        return False, "Moedas insuficientes."
    state.jogadores[ator]["moedas"] -= custos.get(tipo, 0)
    if tipo == "renda":
        state.jogadores[ator]["moedas"] += 1
        _registrar("Renda recebida.")
        _encerrar_turno()
        return True, None
    state.acao_pendente = {"tipo": tipo, "ator": ator, "alvo": alvo, "papel": ACOES[tipo].get("papel"), "bloqueador": None, "papel_bloqueio": None}
    _registrar(f"Ação declarada: {ACOES[tipo]['nome']}.")
    if tipo == "golpe":
        _executar()
    elif tipo == "ajuda":
        state.fase = "reacao_alvo"
    else:
        state.fase = "reacao_acao"
    return True, None


def continuar(jogador_id):
    acao = state.acao_pendente
    if not acao or jogador_id != acao["ator"]:
        return False
    if state.fase == "reacao_acao":
        if acao["tipo"] in ("roubar", "assassinar"):
            state.fase = "reacao_alvo"
        else:
            _executar()
        return True
    if state.fase == "reacao_alvo":
        _executar()
        return True
    return False


def desafiar_acao(desafiante):
    acao = state.acao_pendente
    if state.fase != "reacao_acao" or not acao or desafiante == acao["ator"] or not ativo(desafiante):
        return False
    ator, papel = acao["ator"], acao["papel"]
    if _comprovar(ator, papel):
        perdida = _perder_influencia(desafiante)
        _registrar(f"O desafio falhou. O desafiante perdeu {perdida}.")
        if _verificar_fim(): return True
        return continuar(ator)
    perdida = _perder_influencia(ator)
    _registrar(f"O blefe foi descoberto. O autor perdeu {perdida}.")
    _encerrar_turno()
    return True


def bloquear(jogador_id, papel):
    acao = state.acao_pendente
    if state.fase != "reacao_alvo" or not acao or not ativo(jogador_id):
        return False
    permitidos = {"ajuda": ("Duque",), "roubar": ("Capitão", "Embaixador"), "assassinar": ("Condessa",)}
    if papel not in permitidos.get(acao["tipo"], ()): return False
    if acao["tipo"] != "ajuda" and jogador_id != acao["alvo"]: return False
    if jogador_id == acao["ator"]: return False
    acao["bloqueador"], acao["papel_bloqueio"] = jogador_id, papel
    state.fase = "reacao_bloqueio"
    _registrar(f"Um bloqueio com {papel} foi declarado.")
    return True


def aceitar_bloqueio(jogador_id):
    if state.fase != "reacao_bloqueio" or jogador_id != state.acao_pendente["ator"]: return False
    _registrar("O bloqueio foi aceito.")
    _encerrar_turno()
    return True


def desafiar_bloqueio(jogador_id):
    acao = state.acao_pendente
    if state.fase != "reacao_bloqueio" or not acao or jogador_id != acao["ator"]: return False
    bloqueador, papel = acao["bloqueador"], acao["papel_bloqueio"]
    if _comprovar(bloqueador, papel):
        perdida = _perder_influencia(jogador_id)
        _registrar(f"O bloqueio era verdadeiro. O autor perdeu {perdida}.")
        _encerrar_turno()
    else:
        perdida = _perder_influencia(bloqueador)
        _registrar(f"O bloqueio era blefe. O bloqueador perdeu {perdida}.")
        if _verificar_fim(): return True
        _executar()
    return True


def resetar():
    state.jogo_iniciado=False; state.jogo_finalizado=False; state.fase="aguardando"
    state.participantes=[]; state.jogadores={}; state.baralho=[]; state.indice_turno=0
    state.acao_pendente=None; state.mensagem=""; state.historico=[]; state.vencedor_id=None

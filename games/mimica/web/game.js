let socket = null,
    meuNome = null,
    voltando = false,
    reconexao = false;
const TOKEN_KEY = "noiteDeJogosToken",
    el = id => document.getElementById(id),
    mostrar = (id, sim) => el(id).classList.toggle("hidden", !sim);

function enviar(d) {
    if (socket && socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify(d))
}

function conectar() {
    if (voltando || (socket && socket.readyState <= WebSocket.OPEN)) return;
    const p = location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(`${p}://${location.host}/ws/jogos/mimica`);
    socket.onopen = () => {
        const token = localStorage.getItem(TOKEN_KEY);
        el("status").textContent = "Recuperando sua sessão...";
        if (token) enviar({
            acao: "reconectar",
            token
        });
        else {
            mostrar("entrada", true);
            el("status").textContent = "Use seu código de recuperação."
        }
    };
    socket.onmessage = e => processar(JSON.parse(e.data));
    socket.onclose = () => {
        socket = null;
        if (voltando || reconexao) return;
        el("status").textContent = "Conexão perdida. Reconectando...";
        reconexao = true;
        setTimeout(() => {
            reconexao = false;
            conectar()
        }, 2000)
    }
}

function processar(d) {
    if (d.tipo === "erro") return alert(d.mensagem);
    if (d.tipo === "sessao") {
        localStorage.setItem(TOKEN_KEY, d.token);
        meuNome = d.nome;
        el("status").textContent = `Conectado como ${meuNome}`;
        mostrar("entrada", false);
        return
    }
    if (d.tipo === "sessao_invalida") {
        localStorage.removeItem(TOKEN_KEY);
        mostrar("entrada", true);
        el("status").textContent = "Sessão antiga não encontrada.";
        return
    }
    if (d.tipo === "voltar_lobby") {
        voltando = true;
        if (socket) {
            socket.onclose = null;
            socket.close()
        }
        location.href = "/";
        return
    }
    if (d.tipo === "estado") renderizar(d)
}

function lista(container, jogadores) {
    const ordenados = [...jogadores].sort((a, b) => b.pontos - a.pontos);
    container.replaceChildren(...ordenados.map(j => {
        const linha = document.createElement("div");
        linha.className = `linha${j.conectado?"":" offline"}`;
        const nome = document.createElement("strong");
        nome.textContent = `${j.nome}${j.host?" · HOST":""}`;
        const pontos = document.createElement("span");
        pontos.textContent = `${j.pontos} ponto${j.pontos===1?"":"s"}`;
        linha.append(nome, pontos);
        return linha
    }))
}

function tempo(s) {
    return `${String(Math.floor(s/60)).padStart(2,"0")}:${String(s%60).padStart(2,"0")}`
}

function renderizar(d) {
    if (!d.jogadores.some(j => j.nome === meuNome)) return;
    el("meuCodigo").textContent = d.codigo_recuperacao || "----";
    mostrar("sala", !d.jogo_iniciado && !d.jogo_finalizado);
    mostrar("partida", d.jogo_iniciado);
    mostrar("final", d.jogo_finalizado);
    mostrar("voltar", d.sou_host);
    lista(el("jogadoresSala"), d.jogadores);
    mostrar("configuracao", d.sou_host);
    mostrar("aguarde", !d.sou_host);
    if (d.jogo_iniciado) {
        el("rodada").textContent = `${d.rodada_atual}/${d.rodadas_configuradas}`;
        el("cronometro").textContent = tempo(d.tempo_restante);
        el("jogadorAtual").textContent = d.jogador_atual || "—";
        mostrar("tema", !!d.tema);
        el("tema").textContent = d.tema || "";
        mostrar("revelar", d.sou_jogador_atual && !d.tema_revelado && !d.partida_pausada);
        mostrar("pausa", d.partida_pausada);
        mostrar("pular", d.sou_host && d.partida_pausada);
        mostrar("controles", d.sou_host && d.tema_revelado && !d.partida_pausada);
        if (d.turno_travado) el("orientacao").textContent = "Tempo encerrado. O HOST deve registrar o resultado.";
        else if (d.sou_jogador_atual && !d.tema_revelado) el("orientacao").textContent = "Quando estiver pronto, revele o tema e comece a mímica.";
        else if (d.sou_jogador_atual) el("orientacao").textContent = "Faça a mímica sem falar nem apontar letras.";
        else el("orientacao").textContent = `Tente adivinhar a mímica de ${d.jogador_atual}.`;
        lista(el("placar"), d.jogadores)
    }
    if (d.jogo_finalizado) {
        lista(el("placarFinal"), d.jogadores);
        mostrar("nova", d.sou_host)
    }
}

function recuperar() {
    enviar({
        acao: "recuperar_codigo",
        codigo: el("codigo").value.trim()
    })
}

function comecar() {
    enviar({
        acao: "comecar",
        tempo: parseInt(el("tempo").value, 10),
        rodadas: parseInt(el("rodadas").value, 10)
    })
}

function revelar() {
    enviar({
        acao: "revelar"
    })
}

function resultado(acertou) {
    enviar({
        acao: "resultado",
        acertou
    })
}

function pular() {
    enviar({
        acao: "pular_desconectado"
    })
}

function novaPartida() {
    enviar({
        acao: "nova_partida"
    })
}

function voltarLobby() {
    enviar({
        acao: "voltar_lobby"
    })
}
el("codigo").addEventListener("keydown", e => {
    if (e.key === "Enter") recuperar()
});
conectar();

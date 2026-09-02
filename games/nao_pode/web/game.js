let socket = null;
let meuNome = null;
let meuCodigo = null;
let reconexaoAgendada = false;
let voltandoLobby = false;

let ultimoJogadorAtual = null;
let ultimoSegundoSom = null;
let tempoAnterior = null;

let audioContext = null;
let sonsLigados = true;

const TOKEN_KEY = "noiteDeJogosToken";

// ============================================================
// ÁUDIO
// ============================================================

function ativarAudio() {
    if (!sonsLigados) {
        return;
    }

    try {
        if (!audioContext) {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;

            if (!AudioCtx) {
                return;
            }

            audioContext = new AudioCtx();
        }

        if (audioContext.state === "suspended") {
            audioContext.resume();
        }
    } catch (erro) {
        console.log("Áudio indisponível:", erro);
    }
}

function tocarTom(
    frequencia,
    duracao,
    volume = 0.10,
    tipo = "sine",
    atraso = 0
) {
    if (!sonsLigados || !audioContext) {
        return;
    }

    const inicio = audioContext.currentTime + atraso;
    const oscilador = audioContext.createOscillator();
    const ganho = audioContext.createGain();

    oscilador.type = tipo;
    oscilador.frequency.setValueAtTime(frequencia, inicio);

    ganho.gain.setValueAtTime(0.0001, inicio);
    ganho.gain.exponentialRampToValueAtTime(
        volume,
        inicio + 0.015
    );
    ganho.gain.exponentialRampToValueAtTime(
        0.0001,
        inicio + duracao
    );

    oscilador.connect(ganho);
    ganho.connect(audioContext.destination);

    oscilador.start(inicio);
    oscilador.stop(inicio + duracao + 0.03);
}

function somTrocaJogador() {
    ativarAudio();

    tocarTom(440, .13, .07, "sine", 0);
    tocarTom(660, .15, .08, "sine", .10);
    tocarTom(880, .18, .09, "sine", .22);
}

function somContagem(segundos) {
    ativarAudio();

    let frequencia = 480;

    if (segundos <= 5) {
        frequencia = 650;
    }

    if (segundos <= 2) {
        frequencia = 820;
    }

    tocarTom(
        frequencia,
        .11,
        .075,
        "square"
    );
}

function somTempoEsgotado() {
    ativarAudio();

    tocarTom(220, .28, .12, "sawtooth", 0);
    tocarTom(170, .35, .12, "sawtooth", .20);
}

function alternarSom() {
    sonsLigados = !sonsLigados;

    if (sonsLigados) {
        ativarAudio();
    }

    atualizarBotoesSom();
}

function atualizarBotoesSom() {
    const texto = sonsLigados ?
        "🔊 Sons ligados" :
        "🔇 Sons desligados";

    [
        "botaoSomSala",
        "botaoSomJogo"
    ]
    .forEach(id => {
        const botao = document.getElementById(id);

        if (botao) {
            botao.innerText = texto;
        }
    });
}

// ============================================================
// ANIMAÇÕES
// ============================================================

function animarTrocaJogador() {
    const area = document.getElementById("areaVez");

    if (!area) {
        return;
    }

    area.classList.remove("troca-turno");
    void area.offsetWidth;
    area.classList.add("troca-turno");

    setTimeout(
        function() {
            area.classList.remove("troca-turno");
        },
        700
    );
}

// ============================================================
// CONEXÃO
// ============================================================

function socketAberto() {
    return (
        socket &&
        socket.readyState === WebSocket.OPEN
    );
}

function mostrarRecuperacao() {
    document.getElementById("entradaNova").style.display = "none";
    document.getElementById("recuperacao").style.display = "block";
}

function esconderRecuperacao() {
    document.getElementById("recuperacao").style.display = "none";
    document.getElementById("entradaNova").style.display = "block";
}

function mostrarEntrada() {
    document.getElementById("entrada").style.display = "block";
    document.getElementById("sala").style.display = "none";
    document.getElementById("jogo").style.display = "none";
    document.getElementById("final").style.display = "none";
}

function agendarReconexao() {
    if (voltandoLobby || reconexaoAgendada) {
        return;
    }

    reconexaoAgendada = true;

    setTimeout(
        function() {
            reconexaoAgendada = false;

            if (!voltandoLobby) {
                conectar();
            }
        },
        2000
    );
}

function conectar() {
    if (voltandoLobby) {
        return;
    }

    if (
        socket &&
        (
            socket.readyState === WebSocket.OPEN ||
            socket.readyState === WebSocket.CONNECTING
        )
    ) {
        return;
    }

    const protocolo = location.protocol === "https:" ?
        "wss" :
        "ws";

    socket = new WebSocket(
        protocolo +
        "://" +
        location.host +
        "/ws/jogos/nao-pode"
    );

    socket.onopen = function() {
        const token = localStorage.getItem(TOKEN_KEY);

        if (token) {
            document.getElementById("status").innerText =
                "🔄 Reconectando sua sessão...";

            socket.send(
                JSON.stringify({
                    acao: "reconectar",
                    token: token
                })
            );
        } else {
            document.getElementById("status").innerText =
                "🟢 Conectado ao servidor";
        }
    };

    socket.onclose = function() {
        if (voltandoLobby) {
            return;
        }

        const status = document.getElementById("status");

        if (status) {
            status.innerText =
                "🔴 Conexão perdida. Tentando reconectar...";
        }

        agendarReconexao();
    };

    socket.onmessage = function(event) {
        const dados = JSON.parse(event.data);

        if (dados.tipo === "erro") {
            alert(dados.mensagem);
            return;
        }

        if (dados.tipo === "sessao") {
            localStorage.setItem(
                TOKEN_KEY,
                dados.token
            );

            meuNome = dados.nome;
            meuCodigo = dados.codigo_recuperacao;

            document.getElementById("status").innerText =
                "🟢 Sessão conectada";

            return;
        }

        if (dados.tipo === "sessao_invalida") {
            localStorage.removeItem(TOKEN_KEY);

            meuNome = null;
            meuCodigo = null;

            mostrarEntrada();

            document.getElementById("status").innerText =
                "Sessão antiga não encontrada. Entre novamente.";

            return;
        }

        if (dados.tipo === "voltar_lobby") {
            voltandoLobby = true;
            reconexaoAgendada = false;

            if (socket) {
                socket.onclose = null;

                try {
                    socket.close();
                } catch (erro) {
                    console.log(
                        "Não foi possível fechar o socket:",
                        erro
                    );
                }
            }

            window.location.href = "/";
            return;
        }

        if (dados.tipo === "estado") {
            atualizarEstado(dados);
        }
    };
}

// ============================================================
// AÇÕES
// ============================================================

function entrar() {
    ativarAudio();

    const nome = document
        .getElementById("nome")
        .value
        .trim();

    if (!nome) {
        alert("Digite seu nome.");
        return;
    }

    if (!socketAberto()) {
        alert("Ainda não conectado ao servidor.");
        return;
    }

    socket.send(
        JSON.stringify({
            acao: "entrar",
            nome: nome
        })
    );
}

function recuperarComCodigo() {
    ativarAudio();

    const codigo = document
        .getElementById("codigoRecuperacao")
        .value
        .trim();

    if (!/^\d{4}$/.test(codigo)) {
        alert("Digite um código de 4 números.");
        return;
    }

    if (!socketAberto()) {
        alert("Ainda não conectado ao servidor.");
        return;
    }

    socket.send(
        JSON.stringify({
            acao: "recuperar_codigo",
            codigo: codigo
        })
    );
}

function comecarJogo() {
    ativarAudio();

    const tempo = parseInt(
        document.getElementById("tempoPartida").value,
        10
    );

    const rodadas = parseInt(
        document.getElementById("quantidadeRodadas").value,
        10
    );

    if (!socketAberto()) {
        alert("Sem conexão com o servidor.");
        return;
    }

    socket.send(
        JSON.stringify({
            acao: "comecar",
            tempo: tempo,
            rodadas: rodadas
        })
    );
}

function revelarCarta() {
    ativarAudio();

    if (!socketAberto()) {
        return;
    }

    socket.send(
        JSON.stringify({
            acao: "revelar"
        })
    );
}

function resultado(acertou) {
    ativarAudio();

    if (!socketAberto()) {
        return;
    }

    socket.send(
        JSON.stringify({
            acao: "resultado",
            acertou: acertou
        })
    );
}

function pularDesconectado() {
    ativarAudio();

    if (!socketAberto()) {
        return;
    }

    socket.send(
        JSON.stringify({
            acao: "pular_desconectado"
        })
    );
}

function novaPartida() {
    ativarAudio();

    if (!socketAberto()) {
        return;
    }

    socket.send(
        JSON.stringify({
            acao: "nova_partida"
        })
    );
}

function voltarLobby() {
    ativarAudio();

    if (!socketAberto()) {
        alert("Sem conexão com o servidor.");
        return;
    }

    socket.send(
        JSON.stringify({
            acao: "voltar_lobby"
        })
    );
}

// ============================================================
// ESTADO
// ============================================================

function atualizarEstado(dados) {
    meuCodigo = dados.codigo_recuperacao || meuCodigo;

    const eu = dados.jogadores.find(
        jogador => jogador.nome === meuNome
    );

    if (!eu) {
        return;
    }

    document.getElementById("entrada").style.display = "none";

    document.getElementById("meuCodigoSala").innerText =
        meuCodigo || "----";

    document.getElementById("meuCodigoJogo").innerText =
        meuCodigo || "----";

    if (dados.jogo_finalizado) {
        document.getElementById("sala").style.display = "none";
        document.getElementById("jogo").style.display = "none";
        document.getElementById("final").style.display = "block";

        atualizarFinal(dados);
        return;
    }

    document.getElementById("final").style.display = "none";

    if (!dados.jogo_iniciado) {
        ultimoJogadorAtual = null;
        ultimoSegundoSom = null;
        tempoAnterior = null;

        document.getElementById("sala").style.display = "block";
        document.getElementById("jogo").style.display = "none";

        atualizarSala(dados);
    } else {
        document.getElementById("sala").style.display = "none";
        document.getElementById("jogo").style.display = "block";

        atualizarJogo(dados);
    }
}

// ============================================================
// SALA
// ============================================================

function atualizarSala(dados) {
    const lista = document.getElementById("listaJogadores");

    lista.innerHTML = "";

    dados.jogadores.forEach(jogador => {
        const div = document.createElement("div");
        div.className = "jogador";

        let nome = jogador.nome;

        if (jogador.nome === meuNome) {
            nome += " (você)";
        }

        let extras = "";

        if (jogador.host) {
            extras +=
                '<div class="host">' +
                '👑 HOST' +
                '</div>';
        }

        if (jogador.codigo_recuperacao) {
            extras +=
                '<div class="codigo">' +
                'Código: ' +
                jogador.codigo_recuperacao +
                '</div>';
        }

        div.innerHTML =
            '<div class="linha-jogador">' +
            '<div>👤 ' +
            nome +
            extras +
            '</div>' +
            '<div>' +
            (
                jogador.conectado ?
                "🟢" :
                "🔴"
            ) +
            '</div>' +
            '</div>';

        lista.appendChild(div);
    });

    const configHost = document.getElementById("configHost");
    const botaoComecar = document.getElementById("botaoComecar");
    const aviso = document.getElementById("avisoHost");

    const conectados = dados.jogadores.filter(
        jogador => jogador.conectado
    );

    if (dados.sou_host) {
        configHost.style.display = "block";

        botaoComecar.disabled = conectados.length < 2;

        aviso.innerText = conectados.length < 2 ?
            "Aguardando pelo menos mais 1 jogador..." :
            "Você é o HOST. Configure e inicie a partida.";
    } else {
        configHost.style.display = "none";
        aviso.innerText =
            "Aguardando o HOST configurar e iniciar a partida.";
    }
}

// ============================================================
// TEMPO
// ============================================================

function formatarTempo(segundos) {
    segundos = Math.max(0, segundos || 0);

    const minutos = Math.floor(segundos / 60);
    const resto = segundos % 60;

    return (
        String(minutos).padStart(2, "0") +
        ":" +
        String(resto).padStart(2, "0")
    );
}

// ============================================================
// JOGO
// ============================================================

function atualizarJogo(dados) {
    if (
        dados.jogador_atual &&
        dados.jogador_atual !== ultimoJogadorAtual
    ) {
        ultimoJogadorAtual = dados.jogador_atual;
        ultimoSegundoSom = null;
        tempoAnterior = null;

        animarTrocaJogador();
        somTrocaJogador();
    }

    document.getElementById("rodadaInfo").innerText =
        dados.rodada_atual +
        " / " +
        dados.rodadas_configuradas;

    document.getElementById("tempoConfigInfo").innerText =
        dados.tempo_configurado +
        "s";

    document.getElementById("jogadorAtual").innerText =
        dados.jogador_atual || "-";

    const areaVez = document.getElementById("areaVez");

    if (dados.sou_jogador_atual) {
        areaVez.classList.add("minhaVez");
    } else {
        areaVez.classList.remove("minhaVez");
    }

    // ========================================================
    // TIMER
    // ========================================================

    const cronometro = document.getElementById("cronometro");

    if (!dados.carta_revelada) {
        cronometro.innerText = "--:--";
        cronometro.className = "timer timer-parado";

        ultimoSegundoSom = null;
        tempoAnterior = null;
    } else {
        cronometro.innerText = formatarTempo(
            dados.tempo_restante
        );

        cronometro.className = dados.tempo_restante <= 10 ?
            "timer timer-acabando" :
            "timer";

        if (
            !dados.partida_pausada &&
            dados.tempo_restante <= 10 &&
            dados.tempo_restante > 0 &&
            ultimoSegundoSom !== dados.tempo_restante
        ) {
            ultimoSegundoSom = dados.tempo_restante;
            somContagem(dados.tempo_restante);
        }

        if (
            dados.tempo_restante === 0 &&
            tempoAnterior !== 0
        ) {
            somTempoEsgotado();
        }

        tempoAnterior = dados.tempo_restante;
    }

    // ========================================================
    // PAUSA
    // ========================================================

    const areaPausa = document.getElementById("areaPausa");
    const botaoPular = document.getElementById(
        "botaoPularDesconectado"
    );

    if (dados.partida_pausada) {
        areaPausa.style.display = "block";

        document.getElementById("textoPausa").innerText =
            dados.jogador_pausado +
            " desconectou. " +
            "O cronômetro foi pausado e continuará do mesmo ponto se a pessoa voltar.";

        botaoPular.style.display = dados.sou_host ?
            "block" :
            "none";

        botaoPular.innerText =
            "⏭ PULAR " +
            String(
                dados.jogador_pausado || "JOGADOR"
            ).toUpperCase();
    } else {
        areaPausa.style.display = "none";
        botaoPular.style.display = "none";
    }

    // ========================================================
    // TEMPO ESGOTADO
    // ========================================================

    document.getElementById("avisoTempo").style.display =
        (
            dados.turno_travado &&
            !dados.partida_pausada
        ) ?
        "block" :
        "none";

    // ========================================================
    // REVELAR
    // ========================================================

    const areaRevelar = document.getElementById("areaRevelar");

    areaRevelar.style.display =
        (
            dados.sou_jogador_atual &&
            dados.jogador_atual_conectado &&
            !dados.carta_revelada &&
            !dados.turno_travado &&
            !dados.partida_pausada
        ) ?
        "block" :
        "none";

    // ========================================================
    // CARTA
    // ========================================================

    const carta = document.getElementById("carta");
    const escondida = document.getElementById("cartaEscondida");

    if (dados.carta) {
        carta.style.display = "block";
        escondida.style.display = "none";

        document.getElementById("palavra").innerText =
            dados.carta.palavra;

        const proibidas = document.getElementById("proibidas");
        proibidas.innerHTML = "";

        dados.carta.proibidas.forEach(palavra => {
            const div = document.createElement("div");

            div.className = "proibida";
            div.innerText = "❌ " + palavra;

            proibidas.appendChild(div);
        });
    } else {
        carta.style.display = "none";

        if (
            dados.sou_jogador_atual &&
            !dados.carta_revelada &&
            !dados.partida_pausada
        ) {
            escondida.style.display = "none";
        } else {
            escondida.style.display = "block";

            const texto = document.getElementById("textoEscondido");

            if (dados.partida_pausada) {
                texto.innerText =
                    "Aguardando a reconexão de " +
                    dados.jogador_pausado +
                    ".";
            } else if (!dados.carta_revelada) {
                texto.innerText =
                    "Aguardando " +
                    dados.jogador_atual +
                    " revelar a carta.";
            } else if (dados.turno_travado) {
                texto.innerText =
                    "O tempo terminou. Aguardando o HOST definir o resultado.";
            } else {
                texto.innerText =
                    "Somente " +
                    dados.jogador_atual +
                    " consegue ver a carta.";
            }
        }
    }

    // ========================================================
    // CONTROLES DO HOST
    // ========================================================

    document.getElementById("controlesHost").style.display =
        (
            dados.sou_host &&
            dados.carta_revelada &&
            !dados.partida_pausada
        ) ?
        "block" :
        "none";

    atualizarPlacar(
        dados.jogadores,
        "placar"
    );
}

// ============================================================
// PLACAR
// ============================================================

function atualizarPlacar(
    jogadores,
    elementoId
) {
    const placar = document.getElementById(elementoId);

    placar.innerHTML = "";

    const ordenados = [...jogadores].sort(
        (a, b) => {
            if (b.pontos !== a.pontos) {
                return b.pontos - a.pontos;
            }

            return a.nome.localeCompare(b.nome);
        }
    );

    const maiorPontuacao = ordenados.length > 0 ?
        ordenados[0].pontos :
        0;

    ordenados.forEach(
        (jogador, indice) => {
            const div = document.createElement("div");
            div.className = "placar-item";

            if (
                elementoId === "placarFinal" &&
                jogador.pontos === maiorPontuacao
            ) {
                div.classList.add("lider");
            }

            const status = jogador.conectado ?
                "🟢" :
                "🔴";

            div.innerHTML =
                "<span>" +
                status +
                " " +
                (indice + 1) +
                "º - " +
                jogador.nome +
                "</span>" +
                "<strong>" +
                jogador.pontos +
                "</strong>";

            placar.appendChild(div);
        }
    );
}

// ============================================================
// FINAL
// ============================================================

function garantirBotaoVoltarLobby() {
    let botao = document.getElementById("botaoVoltarLobby");

    if (botao) {
        return botao;
    }

    const botaoNovaPartida = document.getElementById(
        "botaoNovaPartida"
    );

    if (!botaoNovaPartida) {
        return null;
    }

    botao = document.createElement("button");

    botao.id = "botaoVoltarLobby";
    botao.type = "button";
    botao.innerText = "↩ VOLTAR AO LOBBY";
    botao.onclick = voltarLobby;

    botao.style.marginTop = "10px";
    botao.style.background = "#4b5563";
    botao.style.color = "white";

    botaoNovaPartida.insertAdjacentElement(
        "afterend",
        botao
    );

    return botao;
}

function atualizarFinal(dados) {
    const ordenados = [...dados.jogadores].sort(
        (a, b) => b.pontos - a.pontos
    );

    const maiorPontuacao = ordenados.length > 0 ?
        ordenados[0].pontos :
        0;

    const vencedores = ordenados
        .filter(
            jogador => jogador.pontos === maiorPontuacao
        )
        .map(
            jogador => jogador.nome
        );

    document.getElementById("vencedor").innerText =
        vencedores.length === 1 ?
        "🥇 " + vencedores[0] :
        "🤝 Empate: " + vencedores.join(" e ");

    atualizarPlacar(
        dados.jogadores,
        "placarFinal"
    );

    document.getElementById("botaoNovaPartida").style.display =
        dados.sou_host ?
        "block" :
        "none";

    const botaoVoltarLobby = garantirBotaoVoltarLobby();

    if (botaoVoltarLobby) {
        botaoVoltarLobby.style.display = dados.sou_host ?
            "block" :
            "none";
    }

    document.getElementById("avisoNovaPartida").innerText =
        dados.sou_host ?
        "Você pode iniciar outra partida ou voltar ao lobby para escolher outro jogo." :
        "Aguardando o HOST iniciar uma nova partida ou voltar ao lobby.";
}

// ============================================================
// ENTER
// ============================================================

document
    .getElementById("nome")
    .addEventListener(
        "keydown",
        function(event) {
            if (event.key === "Enter") {
                entrar();
            }
        }
    );

document
    .getElementById("codigoRecuperacao")
    .addEventListener(
        "keydown",
        function(event) {
            if (event.key === "Enter") {
                recuperarComCodigo();
            }
        }
    );

atualizarBotoesSom();
conectar();

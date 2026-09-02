console.log(
    "[NOITE DE JOGOS] lobby.js carregado"
);


// ============================================================
// VARIÁVEIS
// ============================================================

let socket = null;

let meuNome = null;

let meuCodigo = null;

let reconexaoAgendada = false;


// Token compartilhado entre o lobby
// e todos os jogos.

const TOKEN_KEY =
    "noiteDeJogosToken";


// ============================================================
// STATUS
// ============================================================

function atualizarStatus(texto) {

    const elemento =
        document.getElementById(
            "status"
        );


    if (elemento) {

        elemento.innerText =
            texto;

    }

}


// ============================================================
// VERIFICAR WEBSOCKET
// ============================================================

function socketAberto() {

    return (

        socket !== null

        &&

        socket.readyState ===
        WebSocket.OPEN

    );

}


// ============================================================
// CONECTAR
// ============================================================

function conectar() {

    console.log(
        "[NOITE DE JOGOS] conectar()"
    );


    // Evita criar duas conexões.

    if (
        socket !== null &&
        (
            socket.readyState ===
            WebSocket.OPEN

            ||

            socket.readyState ===
            WebSocket.CONNECTING
        )
    ) {

        return;

    }


    const protocolo =

        window.location.protocol ===
        "https:"

        ?

        "wss"

        :

        "ws";


    const endereco =

        protocolo

        +

        "://"

        +

        window.location.host

        +

        "/ws/lobby";


    console.log(
        "[NOITE DE JOGOS] WebSocket:",
        endereco
    );


    atualizarStatus(
        "🔄 Conectando ao servidor..."
    );


    socket =
        new WebSocket(
            endereco
        );


    // ========================================================
    // ABRIU CONEXÃO
    // ========================================================

    socket.onopen =
        function() {

            console.log(
                "[NOITE DE JOGOS] WebSocket conectado"
            );


            atualizarStatus(
                "🟢 Conectado ao servidor"
            );


            // Verifica se já existe uma sessão salva.

            const token =
                localStorage.getItem(
                    TOKEN_KEY
                );


            if (token) {

                console.log(
                    "[NOITE DE JOGOS] Tentando reconectar sessão"
                );


                atualizarStatus(
                    "🔄 Recuperando sua sessão..."
                );


                enviar({

                    acao: "reconectar",

                    token: token

                });

            }

        };


    // ========================================================
    // RECEBEU MENSAGEM
    // ========================================================

    socket.onmessage =
        function(event) {

            console.log(
                "[NOITE DE JOGOS] Mensagem:",
                event.data
            );


            let dados;


            try {

                dados =
                    JSON.parse(
                        event.data
                    );

            } catch (erro) {

                console.error(
                    "[NOITE DE JOGOS] JSON inválido:",
                    erro
                );


                return;

            }


            processarMensagem(
                dados
            );

        };


    // ========================================================
    // ERRO
    // ========================================================

    socket.onerror =
        function(erro) {

            console.error(
                "[NOITE DE JOGOS] Erro no WebSocket:",
                erro
            );


            atualizarStatus(
                "🔴 Erro de conexão"
            );

        };


    // ========================================================
    // DESCONECTOU
    // ========================================================

    socket.onclose =
        function() {

            console.log(
                "[NOITE DE JOGOS] WebSocket desconectado"
            );


            socket = null;


            atualizarStatus(
                "🔴 Conexão perdida. Reconectando..."
            );


            agendarReconexao();

        };

}


// ============================================================
// RECONEXÃO AUTOMÁTICA
// ============================================================

function agendarReconexao() {

    if (
        reconexaoAgendada
    ) {

        return;

    }


    reconexaoAgendada =
        true;


    setTimeout(

        function() {

            reconexaoAgendada =
                false;


            conectar();

        },

        2000

    );

}


// ============================================================
// ENVIAR MENSAGEM
// ============================================================

function enviar(dados) {

    if (
        !socketAberto()
    ) {

        console.warn(
            "[NOITE DE JOGOS] WebSocket não conectado"
        );


        return false;

    }


    socket.send(

        JSON.stringify(
            dados
        )

    );


    return true;

}


// ============================================================
// PROCESSAR MENSAGEM
// ============================================================

function processarMensagem(dados) {

    console.log(
        "[NOITE DE JOGOS] Tipo:",
        dados.tipo
    );


    // ========================================================
    // ERRO
    // ========================================================

    if (
        dados.tipo ===
        "erro"
    ) {

        alert(
            dados.mensagem
        );


        return;

    }


    // ========================================================
    // SESSÃO CRIADA / RECUPERADA
    // ========================================================

    if (
        dados.tipo ===
        "sessao"
    ) {

        meuNome =
            dados.nome;


        meuCodigo =
            dados.codigo_recuperacao;


        localStorage.setItem(

            TOKEN_KEY,

            dados.token

        );


        console.log(
            "[NOITE DE JOGOS] Sessão ativa:",
            meuNome
        );


        return;

    }


    // ========================================================
    // TOKEN ANTIGO / INVÁLIDO
    // ========================================================

    if (
        dados.tipo ===
        "sessao_invalida"
    ) {

        console.log(
            "[NOITE DE JOGOS] Sessão inválida"
        );


        localStorage.removeItem(
            TOKEN_KEY
        );


        meuNome =
            null;


        meuCodigo =
            null;


        mostrarEntrada();


        atualizarStatus(
            "🟢 Conectado. Entre novamente."
        );


        return;

    }


    // ========================================================
    // ESTADO DO LOBBY
    // ========================================================

    if (
        dados.tipo ===
        "estado_lobby"
    ) {

        atualizarLobby(
            dados
        );


        return;

    }

}


// ============================================================
// ENTRAR NA SALA
// ============================================================

function entrar() {

    console.log(
        "[NOITE DE JOGOS] Botão entrar"
    );


    const campoNome =
        document.getElementById(
            "nome"
        );


    if (!campoNome) {

        console.error(
            "Campo nome não encontrado."
        );


        return;

    }


    const nome =
        campoNome
        .value
        .trim();


    if (!nome) {

        alert(
            "Digite seu nome."
        );


        return;

    }


    if (
        !socketAberto()
    ) {

        alert(
            "Ainda não conectado ao servidor."
        );


        return;

    }


    atualizarStatus(
        "Entrando na sala..."
    );


    enviar({

        acao: "entrar",

        nome: nome

    });

}


// ============================================================
// MOSTRAR RECUPERAÇÃO
// ============================================================

function mostrarRecuperacao() {

    const entradaNova =
        document.getElementById(
            "entradaNova"
        );


    const recuperacao =
        document.getElementById(
            "recuperacao"
        );


    if (entradaNova) {

        entradaNova.style.display =
            "none";

    }


    if (recuperacao) {

        recuperacao.style.display =
            "block";

    }

}


// ============================================================
// ESCONDER RECUPERAÇÃO
// ============================================================

function esconderRecuperacao() {

    const entradaNova =
        document.getElementById(
            "entradaNova"
        );


    const recuperacao =
        document.getElementById(
            "recuperacao"
        );


    if (recuperacao) {

        recuperacao.style.display =
            "none";

    }


    if (entradaNova) {

        entradaNova.style.display =
            "block";

    }

}


// ============================================================
// RECUPERAR COM CÓDIGO
// ============================================================

function recuperarComCodigo() {

    const campo =
        document.getElementById(
            "codigoRecuperacao"
        );


    if (!campo) {

        return;

    }


    const codigo =
        campo
        .value
        .trim();


    if (
        !/^\d{4}$/.test(
            codigo
        )
    ) {

        alert(
            "Digite um código de 4 números."
        );


        return;

    }


    if (
        !socketAberto()
    ) {

        alert(
            "Ainda não conectado ao servidor."
        );


        return;

    }


    enviar({

        acao: "recuperar_codigo",

        codigo: codigo

    });

}


// ============================================================
// MOSTRAR ENTRADA
// ============================================================

function mostrarEntrada() {

    const entrada =
        document.getElementById(
            "entrada"
        );


    const lobby =
        document.getElementById(
            "lobby"
        );


    if (entrada) {

        entrada.style.display =
            "block";

    }


    if (lobby) {

        lobby.style.display =
            "none";

    }

}


// ============================================================
// MOSTRAR LOBBY
// ============================================================

function mostrarLobby() {

    const entrada =
        document.getElementById(
            "entrada"
        );


    const lobby =
        document.getElementById(
            "lobby"
        );


    if (entrada) {

        entrada.style.display =
            "none";

    }


    if (lobby) {

        lobby.style.display =
            "block";

    }

}


// ============================================================
// ATUALIZAR LOBBY
// ============================================================

function atualizarLobby(dados) {

    console.log(
        "[NOITE DE JOGOS] Atualizando lobby"
    );


    // Localiza o jogador deste navegador.

    let eu =
        null;


    for (
        let i = 0; i < dados.jogadores.length; i++
    ) {

        const jogador =
            dados.jogadores[i];


        if (
            jogador.nome ===
            meuNome
        ) {

            eu =
                jogador;


            break;

        }

    }


    // Pode acontecer por alguns milissegundos
    // durante reconexão.

    if (!eu) {

        console.warn(
            "[NOITE DE JOGOS] Jogador ainda não localizado"
        );


        return;

    }


    mostrarLobby();


    // ========================================================
    // CÓDIGO
    // ========================================================

    meuCodigo =

        dados.codigo_recuperacao

        ||

        meuCodigo;


    const campoCodigo =
        document.getElementById(
            "meuCodigo"
        );


    if (campoCodigo) {

        campoCodigo.innerText =

            meuCodigo

            ||

            "----";

    }


    // ========================================================
    // JOGADORES
    // ========================================================

    atualizarJogadores(
        dados
    );


    // ========================================================
    // JOGOS
    // ========================================================

    atualizarJogos(
        dados
    );


    // ========================================================
    // HOST ESCOLHEU UM JOGO
    // ========================================================

    if (
        dados.jogo_selecionado
    ) {

        abrirJogoSelecionado(
            dados
        );

    }

}


// ============================================================
// LISTA DE JOGADORES
// ============================================================

function atualizarJogadores(dados) {

    const lista =
        document.getElementById(
            "listaJogadores"
        );


    if (!lista) {

        return;

    }


    lista.innerHTML =
        "";


    for (
        let i = 0; i < dados.jogadores.length; i++
    ) {

        const jogador =
            dados.jogadores[i];


        const linha =
            document.createElement(
                "div"
            );


        linha.className =
            "jogador";


        // ====================================================
        // LADO ESQUERDO
        // ====================================================

        const esquerda =
            document.createElement(
                "div"
            );


        const nome =
            document.createElement(
                "div"
            );


        nome.className =
            "jogador-nome";


        let textoNome =
            jogador.nome;


        if (
            jogador.nome ===
            meuNome
        ) {

            textoNome +=
                " (você)";

        }


        nome.innerText =
            textoNome;


        esquerda.appendChild(
            nome
        );


        // ====================================================
        // HOST
        // ====================================================

        if (
            jogador.host
        ) {

            const host =
                document.createElement(
                    "div"
                );


            host.className =
                "host";


            host.innerText =
                "👑 HOST";


            esquerda.appendChild(
                host
            );

        }


        // ====================================================
        // STATUS
        // ====================================================

        const status =
            document.createElement(
                "div"
            );


        status.innerText =

            jogador.conectado

            ?

            "🟢"

            :

            "🔴";


        linha.appendChild(
            esquerda
        );


        linha.appendChild(
            status
        );


        lista.appendChild(
            linha
        );

    }

}


// ============================================================
// LISTA DE JOGOS
// ============================================================

function atualizarJogos(dados) {

    const lista =
        document.getElementById(
            "listaJogos"
        );


    const aviso =
        document.getElementById(
            "avisoHost"
        );


    if (
        !lista ||
        !aviso
    ) {

        return;

    }


    lista.innerHTML =
        "";


    // ========================================================
    // QUANTIDADE CONECTADA
    // ========================================================

    let conectados =
        0;


    for (
        let i = 0; i < dados.jogadores.length; i++
    ) {

        if (
            dados.jogadores[i]
            .conectado
        ) {

            conectados++;

        }

    }


    // ========================================================
    // AVISO
    // ========================================================

    if (
        dados.sou_host
    ) {

        if (
            conectados >= 2
        ) {

            aviso.innerText =
                "👑 Você é o HOST. Escolha o jogo.";

        } else {

            aviso.innerText =
                "Aguardando pelo menos mais 1 jogador.";

        }

    } else {

        aviso.innerText =
            "Aguardando o HOST escolher o jogo.";

    }


    // ========================================================
    // CRIAR CARDS
    // ========================================================

    for (
        let i = 0; i < dados.jogos.length; i++
    ) {

        criarCardJogo(

            dados.jogos[i],

            dados.sou_host,

            conectados,

            lista

        );

    }

}


// ============================================================
// CRIAR CARD DE JOGO
// ============================================================

function criarCardJogo(
    jogo,
    souHost,
    conectados,
    lista
) {

    const card =
        document.createElement(
            "div"
        );


    card.className =
        "jogo-card";


    if (
        jogo.disponivel
    ) {

        card.classList.add(
            "disponivel"
        );

    } else {

        card.classList.add(
            "indisponivel"
        );

    }


    // ========================================================
    // ÍCONE
    // ========================================================

    const icone =
        document.createElement(
            "div"
        );


    icone.className =
        "jogo-icone";


    icone.innerText =
        jogo.icone;


    // ========================================================
    // NOME
    // ========================================================

    const nome =
        document.createElement(
            "div"
        );


    nome.className =
        "jogo-nome";


    nome.innerText =
        jogo.nome;


    // ========================================================
    // DESCRIÇÃO
    // ========================================================

    const descricao =
        document.createElement(
            "div"
        );


    descricao.className =
        "jogo-descricao";


    descricao.innerText =
        jogo.descricao;


    card.appendChild(
        icone
    );


    card.appendChild(
        nome
    );


    card.appendChild(
        descricao
    );


    // ========================================================
    // BOTÃO DE REGRAS
    // ========================================================

    if (
        jogo.regras
    ) {

        const botaoRegras =
            document.createElement(
                "button"
            );


        botaoRegras.type =
            "button";


        botaoRegras.className =
            "botao-regras";


        botaoRegras.innerText =
            "Regras do jogo";


        botaoRegras.onclick =
            function(evento) {

                // Evita que o clique no botão
                // também selecione o jogo.

                evento.stopPropagation();


                abrirRegras(
                    jogo
                );

            };


        card.appendChild(
            botaoRegras
        );

    }


    // ========================================================
    // EM BREVE
    // ========================================================

    if (
        !jogo.disponivel
    ) {

        const breve =
            document.createElement(
                "div"
            );


        breve.className =
            "em-breve";


        breve.innerText =
            "EM BREVE";


        card.appendChild(
            breve
        );

    }


    // ========================================================
    // HOST PODE CLICAR
    // ========================================================

    if (
        jogo.disponivel &&
        souHost &&
        conectados >= 2
    ) {

        card.onclick =
            function() {

                selecionarJogo(
                    jogo.id
                );

            };

    }


    lista.appendChild(
        card
    );

}


// ============================================================
// GUIA DE REGRAS
// ============================================================

function abrirRegras(jogo) {

    if (
        !jogo ||
        !jogo.regras
    ) {

        console.warn(
            "[NOITE DE JOGOS] Regras não disponíveis."
        );


        return;

    }


    const regras =
        jogo.regras;


    // ========================================================
    // ELEMENTOS DO MODAL
    // ========================================================

    const modal =
        document.getElementById(
            "modalRegras"
        );


    const icone =
        document.getElementById(
            "iconeRegras"
        );


    const titulo =
        document.getElementById(
            "tituloRegras"
        );


    const objetivo =
        document.getElementById(
            "objetivoRegras"
        );


    const exemplo =
        document.getElementById(
            "exemploRegras"
        );


    const passos =
        document.getElementById(
            "passosRegras"
        );


    // ========================================================
    // PROTEÇÃO
    // ========================================================

    // Se algum elemento não existir,
    // não derruba o JavaScript inteiro do lobby.

    if (
        !modal ||
        !icone ||
        !titulo ||
        !objetivo ||
        !exemplo ||
        !passos
    ) {

        console.error(
            "[NOITE DE JOGOS] Elementos do modal de regras não encontrados."
        );


        return;

    }


    // ========================================================
    // PREENCHER MODAL
    // ========================================================

    icone.innerText =
        jogo.icone;


    titulo.innerText =
        jogo.nome;


    objetivo.innerText =
        regras.objetivo;


    exemplo.innerText =
        regras.exemplo;


    // ========================================================
    // PASSOS
    // ========================================================

    passos.replaceChildren();


    if (
        Array.isArray(
            regras.como_jogar
        )
    ) {

        for (
            const texto of regras.como_jogar
        ) {

            const item =
                document.createElement(
                    "li"
                );


            item.innerText =
                texto;


            passos.appendChild(
                item
            );

        }

    }


    // ========================================================
    // ABRIR MODAL
    // ========================================================

    modal.classList.remove(
        "oculto"
    );

}


// ============================================================
// FECHAR REGRAS
// ============================================================

function fecharRegras() {

    const modal =
        document.getElementById(
            "modalRegras"
        );


    if (!modal) {

        return;

    }


    modal.classList.add(
        "oculto"
    );

}


// ============================================================
// EVENTOS DO MODAL
// ============================================================

const botaoFecharRegras =
    document.getElementById(
        "fecharRegras"
    );


if (botaoFecharRegras) {

    botaoFecharRegras.addEventListener(

        "click",

        fecharRegras

    );

}


// ============================================================
// CLICAR FORA DO MODAL
// ============================================================

const modalRegras =
    document.getElementById(
        "modalRegras"
    );


if (modalRegras) {

    modalRegras.addEventListener(

        "click",

        function(evento) {

            if (
                evento.target ===
                this
            ) {

                fecharRegras();

            }

        }

    );

}


// ============================================================
// ESC PARA FECHAR
// ============================================================

document.addEventListener(

    "keydown",

    function(evento) {

        if (
            evento.key ===
            "Escape"
        ) {

            fecharRegras();

        }

    }

);


// ============================================================
// SELECIONAR JOGO
// ============================================================

function selecionarJogo(jogoId) {

    console.log(
        "[NOITE DE JOGOS] Selecionando jogo:",
        jogoId
    );


    if (
        !socketAberto()
    ) {

        alert(
            "Servidor desconectado."
        );


        return;

    }


    enviar({

        acao: "selecionar_jogo",

        jogo: jogoId

    });

}


// ============================================================
// ABRIR JOGO SELECIONADO
// ============================================================

function abrirJogoSelecionado(dados) {

    for (
        let i = 0; i < dados.jogos.length; i++
    ) {

        const jogo =
            dados.jogos[i];


        if (
            jogo.id ===
            dados.jogo_selecionado
        ) {

            if (
                jogo.url
            ) {

                console.log(
                    "[NOITE DE JOGOS] Abrindo:",
                    jogo.url
                );


                window.location.href =
                    jogo.url;

            }


            return;

        }

    }

}


// ============================================================
// ENTER NO CAMPO NOME
// ============================================================

const campoNome =
    document.getElementById(
        "nome"
    );


if (campoNome) {

    campoNome.addEventListener(

        "keydown",

        function(event) {

            if (
                event.key ===
                "Enter"
            ) {

                entrar();

            }

        }

    );

}


// ============================================================
// ENTER NO CÓDIGO
// ============================================================

const campoCodigo =
    document.getElementById(
        "codigoRecuperacao"
    );


if (campoCodigo) {

    campoCodigo.addEventListener(

        "keydown",

        function(event) {

            if (
                event.key ===
                "Enter"
            ) {

                recuperarComCodigo();

            }

        }

    );

}


// ============================================================
// INICIAR
// ============================================================

console.log(
    "[NOITE DE JOGOS] Iniciando lobby..."
);


conectar();

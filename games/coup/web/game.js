let socket=null,meuNome=null,voltando=false,reconexao=false;const TOKEN_KEY="noiteDeJogosToken",el=id=>document.getElementById(id),mostrar=(id,v)=>el(id).classList.toggle("hidden",!v),enviar=d=>socket?.readyState===WebSocket.OPEN&&socket.send(JSON.stringify(d));
function conectar(){if(voltando||(socket&&socket.readyState<=1))return;el("status").textContent="Conectando...";const p=location.protocol==="https:"?"wss":"ws";socket=new WebSocket(`${p}://${location.host}/ws/jogos/coup`);socket.onopen=()=>{const token=localStorage.getItem(TOKEN_KEY);if(token){el("status").textContent="Recuperando sua sessão...";enviar({acao:"reconectar",token})}else{mostrar("entrada",true);el("status").textContent="Use seu código de recuperação."}};socket.onmessage=e=>processar(JSON.parse(e.data));socket.onerror=()=>{el("status").textContent="Não foi possível conectar ao jogo."};socket.onclose=()=>{socket=null;if(voltando||reconexao)return;el("status").textContent="Conexão perdida. Reconectando...";reconexao=true;setTimeout(()=>{reconexao=false;conectar()},2000)}}
function processar(d){if(d.tipo==="erro")return alert(d.mensagem);if(d.tipo==="sessao"){localStorage.setItem(TOKEN_KEY,d.token);meuNome=d.nome;el("status").textContent=`Conectado como ${meuNome}`;mostrar("entrada",false);return}if(d.tipo==="sessao_invalida"){localStorage.removeItem(TOKEN_KEY);mostrar("entrada",true);el("status").textContent="Sessão não encontrada. Use seu código de recuperação.";return}if(d.tipo==="voltar_lobby"){voltando=true;socket.onclose=null;socket.close();location.href="/";return}if(d.tipo==="estado")render(d)}
function botao(texto,fn,classe=""){const b=document.createElement("button");b.textContent=texto;b.className=classe;b.onclick=fn;return b}
function alvoSelect(d){const s=document.createElement("select");s.id="alvo";d.jogadores.filter(j=>j.id!==d.meu_id&&j.influencias>0).forEach(j=>{const o=document.createElement("option");o.value=j.id;o.textContent=j.nome;s.append(o)});return s}
function acao(d,tipo,nome,alvo=false,classe=""){const b=botao(nome,()=>enviar({acao:"agir",tipo,alvo:alvo?el("alvo").value:null}),classe);el("acoes").append(b)}
function montarAcoes(d, eu) {
  el("acoes").replaceChildren();
  el("reacoes").replaceChildren();

  if (d.fase === "turno" && d.jogador_atual_id === d.meu_id && eu.influencias) {
    el("acoes").append(alvoSelect(d));
    acao(d, "renda", "Renda +1");
    acao(d, "ajuda", "Ajuda externa +2");
    acao(d, "imposto", "Imposto +3 (Duque)");
    acao(d, "roubar", "Roubar 2 (Capitão)", true);
    acao(d, "trocar", "Trocar (Embaixador)");
    acao(d, "assassinar", "Assassinar −3", true, "danger");
    acao(d, "golpe", "Golpe −7", true, "danger");
  }

  const pendente = d.acao;
  if (!pendente) return;

  if (d.fase === "reacao_acao" && d.meu_id !== pendente.ator && eu.influencias) {
    el("reacoes").append(botao(
      `Desafiar ${pendente.papel}`,
      () => enviar({ acao: "desafiar_acao" }),
      "danger"
    ));
  }

  if ((d.fase === "reacao_acao" || d.fase === "reacao_alvo") && d.meu_id === pendente.ator) {
    el("reacoes").append(botao("Continuar ação", () => enviar({ acao: "continuar" })));
  }

  if (d.fase === "reacao_alvo" && d.meu_id !== pendente.ator && eu.influencias) {
    if (pendente.tipo === "ajuda") {
      el("reacoes").append(botao("Bloquear com Duque", () => enviar({ acao: "bloquear", papel: "Duque" })));
    }
    if (pendente.alvo === d.meu_id && pendente.tipo === "roubar") {
      el("reacoes").append(
        botao("Bloquear: Capitão", () => enviar({ acao: "bloquear", papel: "Capitão" })),
        botao("Bloquear: Embaixador", () => enviar({ acao: "bloquear", papel: "Embaixador" }))
      );
    }
    if (pendente.alvo === d.meu_id && pendente.tipo === "assassinar") {
      el("reacoes").append(botao("Bloquear com Condessa", () => enviar({ acao: "bloquear", papel: "Condessa" })));
    }
  }

  if (d.fase === "reacao_bloqueio" && d.meu_id === pendente.ator) {
    el("reacoes").append(
      botao("Aceitar bloqueio", () => enviar({ acao: "aceitar_bloqueio" })),
      botao(`Desafiar ${pendente.papel_bloqueio}`, () => enviar({ acao: "desafiar_bloqueio" }), "danger")
    );
  }
}
function linhaJogador(j,d){const div=document.createElement("div");div.className=`linha${j.id===d.jogador_atual_id?" atual":""}${j.influencias?"":" eliminado"}${j.conectado?"":" offline"}`;const info=document.createElement("div");info.className="jogador-info";const n=document.createElement("strong");n.textContent=`${j.nome}${j.host?" · HOST":""}`;const c=document.createElement("small");c.textContent=`${j.moedas} moeda(s)`;info.append(n,c);const inf=document.createElement("span");inf.className="influencias";inf.textContent="●".repeat(j.influencias)+"○".repeat(2-j.influencias);div.append(info,inf);return div}
function render(d){const eu=d.jogadores.find(j=>j.id===d.meu_id);if(!eu)return;el("meuCodigo").textContent=d.codigo_recuperacao||"----";mostrar("sala",!d.jogo_iniciado&&!d.jogo_finalizado);mostrar("partida",d.jogo_iniciado);mostrar("final",d.jogo_finalizado);mostrar("voltar",d.sou_host);mostrar("comecar",d.sou_host);mostrar("aguarde",!d.sou_host);el("jogadoresSala").replaceChildren(...d.jogadores.map(j=>linhaJogador(j,d)));if(d.jogo_iniciado){const atual=d.jogadores.find(j=>j.id===d.jogador_atual_id);el("vez").textContent=atual?`Vez de ${atual.nome}`:"";el("fase").textContent=d.fase.replaceAll("_"," ");el("mensagem").textContent=d.mensagem;el("minhasCartas").replaceChildren(...eu.cartas.map(c=>{const x=document.createElement("div");x.className=`carta${c.viva?"":" perdida"}`;x.textContent=c.papel||"Influência";return x}));el("jogadores").replaceChildren(...d.jogadores.map(j=>linhaJogador(j,d)));el("historico").replaceChildren(...d.historico.map(t=>{const p=document.createElement("p");p.textContent=t;return p}));montarAcoes(d,eu)}if(d.jogo_finalizado){el("vencedor").textContent=d.vencedor?`🏆 ${d.vencedor} venceu!`:"Partida encerrada";mostrar("nova",d.sou_host)}}
function recuperar(){enviar({acao:"recuperar_codigo",codigo:el("codigo").value.trim()})}function comecar(){enviar({acao:"comecar"})}function novaPartida(){enviar({acao:"nova_partida"})}function voltarLobby(){enviar({acao:"voltar_lobby"})}el("codigo").addEventListener("keydown",e=>{if(e.key==="Enter")recuperar()});conectar();

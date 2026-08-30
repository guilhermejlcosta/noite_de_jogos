# Noite de Jogos

Uma plataforma de jogos de festa para rodar localmente: uma pessoa hospeda o servidor e todos entram pelo navegador do celular, na mesma rede Wi-Fi.

O projeto usa FastAPI e WebSockets para manter a sala, a partida e as pontuações sincronizadas em tempo real.

## Jogos disponíveis

| Jogo | Descrição |
| --- | --- |
| Não Pode | Explique uma palavra sem dizer os termos proibidos. |
| Mímica | Faça os outros adivinharem usando apenas gestos. |
| Quem Sou Eu? | Descubra a identidade secreta atribuída a você. |
| Mais provável de... | Vote em quem mais combina com cada situação. |
| Stop / Adedonha | Preencha categorias com palavras iniciadas pela letra sorteada. |
| Quiz | Responda perguntas de múltipla escolha contra o tempo. |
| ITO | Organizem pistas numa escala de 1 a 100 sem revelar os números. |
| COUP | Blefe, desafie e elimine as influências adversárias. |

## Recursos

- Lobby compartilhado com seleção de jogo pelo HOST.
- Acesso de vários celulares na mesma rede.
- Atualizações em tempo real por WebSocket.
- Reconexão automática no mesmo navegador e recuperação por código de 4 dígitos em outro aparelho.
- Troca de HOST quando necessário e retorno coletivo ao lobby.
- Dados dos jogos em arquivos JSON, fáceis de ampliar.

## Requisitos

- Python 3.9 ou superior.
- Celulares e computador na mesma rede local para jogar em grupo.

## Instalação e execução

No PowerShell, dentro da pasta do projeto:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Abra `http://localhost:8000` no computador. Para os celulares, descubra o IPv4 do computador com `ipconfig` e abra, por exemplo, `http://192.168.1.10:8000`.

Se o Windows pedir permissão de firewall, permita o acesso em redes privadas. Mantenha o terminal do servidor aberto durante a noite de jogos.

## Como jogar

1. O primeiro participante entra no lobby e se torna HOST.
2. Os demais entram usando o mesmo endereço no navegador.
3. O HOST escolhe um jogo e inicia a partida.
4. Cada participante deve guardar o próprio código de recuperação de quatro dígitos.
5. Ao término, o HOST pode iniciar outra partida ou mandar todos de volta ao lobby.

## Regras resumidas

As instruções detalhadas também aparecem no guia do lobby e, quando aplicável, dentro do próprio jogo.

### Não Pode

O jogador da vez revela uma carta e tenta fazer o grupo adivinhar a palavra, sem usar nenhuma palavra proibida. O HOST registra acerto ou erro antes de avançar o turno.

### Mímica

O jogador da vez recebe um tema secreto e o representa apenas com gestos: não vale falar, escrever ou apontar letras. O HOST confirma se houve acerto.

### Quem Sou Eu?

Cada pessoa vê as identidades dos outros, mas não a sua. Faça perguntas que possam ser respondidas com “sim” ou “não” até descobrir sua própria identidade.

### Mais provável de...

Uma situação é exibida e todos votam secretamente em uma pessoa. Os votos são revelados juntos e formam a pontuação da rodada.

### Stop / Adedonha

Uma letra é sorteada. Preencha todas as categorias com palavras que comecem com ela. Respostas únicas valem 10 pontos, repetidas valem 5 e respostas invalidadas valem 0.

### Quiz

Todos respondem a pergunta de múltipla escolha antes do tempo acabar. Respostas corretas somam pontos e vence quem terminar com a maior pontuação.

### ITO

Cada jogador recebe secretamente um número de 1 a 100 e cria uma pista conforme o tema. O HOST ordena as pistas; ao revelar os números, o jogo calcula os erros de ordem. É cooperativo.

### COUP

Cada pessoa começa com duas influências e duas moedas. Use ações, bloqueios e desafios — é permitido blefar sobre as cartas que possui. Quem perder todas as influências sai; vence a última pessoa restante. Com 10 moedas, o Golpe é obrigatório.

## Estrutura do projeto

```text
app.py                  # Aplicação FastAPI e registro das rotas
core/                   # Lobby, jogadores e gerenciamento de conexões
games/                  # Lógica, estado, dados e interface de cada jogo
tests/                  # Testes automatizados
web/                    # Interface do lobby e arquivos estáticos comuns
```

## Testes

Com o ambiente virtual ativado:

```powershell
python -m unittest discover -s tests -v
```

## Dados e expansão

Os conteúdos dos jogos ficam em `games/<jogo>/data/` em arquivos JSON. Para criar um novo jogo, adicione seu estado, lógica, rota WebSocket e interface, registre a rota em `app.py` e inclua o jogo na lista em `core/lobby.py`.

## Estado atual

O projeto está em desenvolvimento ativo. A suíte automatizada cobre gerenciamento de conexões, ITO e regras centrais de COUP; recomenda-se testar manualmente cada jogo com mais de um aparelho antes de uma partida.

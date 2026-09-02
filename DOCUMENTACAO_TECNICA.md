# Guia técnico do projeto

Este documento apresenta o encaixe das partes do projeto para quem está começando. O servidor é iniciado por `app.py`; os participantes usam o navegador, e cada mudança importante é enviada em tempo real pelo WebSocket.

## Visão geral

```text
Navegador (web/ e games/*/web/)
        | WebSocket / requisição HTTP
        v
app.py (cria o FastAPI e registra as rotas)
        v
core/ (lobby, jogadores e conexões)
        v
games/<nome>/router.py (comunicação do jogo)
        v
games/<nome>/game.py + state.py (regras e estado da partida)
        v
games/<nome>/data/*.json (conteúdo editável: cartas, temas e perguntas)
```

## Pastas e responsabilidades

- `app.py`: ponto de entrada. Cria a aplicação FastAPI, disponibiliza arquivos estáticos e conecta o lobby e todos os jogos.
- `core/jogadores.py`: cadastro compartilhado dos participantes, HOST, token e código de recuperação.
- `core/lobby.py`: sala de espera, lista de jogos e seleção feita pelo HOST.
- `core/conexoes_jogo.py`: utilitário que liga um WebSocket ao jogador correto dentro de uma partida.
- `games/<nome>/router.py`: recebe as mensagens do navegador, valida quem pode executar cada ação e devolve o estado atualizado.
- `games/<nome>/game.py`: regras puras da partida, como iniciar rodada, registrar ação, calcular pontos e finalizar.
- `games/<nome>/state.py`: variáveis que representam a partida atual. Elas são reiniciadas ao iniciar ou encerrar um jogo.
- `games/<nome>/web/`: tela específica do jogo. `index.html` define a estrutura, `style.css` a aparência e `game.js` a interação com o servidor.
- `web/`: tela e scripts do lobby, usados antes de uma partida.
- `tests/`: verificações automatizadas para regras e conexões.

## Fluxo de uma ação

1. A pessoa clica em um botão na página; o arquivo JavaScript envia uma mensagem com uma `acao`.
2. O `router.py` do lobby ou do jogo recebe a mensagem pelo WebSocket.
3. O roteador confirma que o jogador existe e, quando necessário, que é o HOST.
4. O roteador chama uma função em `game.py`, que altera apenas o estado de `state.py`.
5. O roteador monta um estado apropriado para cada participante. Informações secretas só são incluídas para quem pode vê-las.
6. O estado é enviado de volta e a interface é redesenhada no navegador.

## Como alterar conteúdo sem mexer nas regras

Os arquivos em `games/*/data/` são JSON. Eles contêm apenas os dados dos jogos e não executam código. Mantenha a sintaxe JSON válida: chaves e textos usam aspas duplas, itens são separados por vírgula e JSON não permite comentários. Para adicionar cartas, temas, perguntas ou categorias, siga o formato dos itens já existentes.

## Convenções usadas

- Indentação de quatro espaços em código, HTML e CSS; JSON usa dois espaços.
- `router.py` faz a camada de comunicação; não deve concentrar regras complexas.
- `game.py` concentra regras; evita depender diretamente de WebSocket ou HTML.
- `state.py` conserva o estado temporário de uma única partida.
- Comentários descrevem decisões, permissões e informações que precisam permanecer secretas. Nomes de funções e variáveis descrevem a ação ou dado diretamente.

## Verificação após mudanças

No diretório do projeto, instale as dependências e execute:

```powershell
python -m pytest
```

Para iniciar o servidor local:

```powershell
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

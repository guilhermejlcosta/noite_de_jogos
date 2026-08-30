# 🎮 NÃO PODE — Servidor local

Este projeto roda no computador e permite que os jogadores acessem pelo navegador do celular usando a mesma rede Wi‑Fi.

## Estrutura esperada

```text
nao_pode/
├── app.py
├── cartas.json
└── venv/
```

## 1. Abrir o projeto

Abra o Prompt de Comando (CMD) e entre na pasta do projeto.

Exemplo:

```bat
cd %USERPROFILE%\Documents\nao_pode
```

Se a pasta estiver em outro local, altere o caminho.

## 2. Ativar o ambiente virtual

No CMD:

```bat
venv\Scripts\activate
```

Quando estiver ativo, o começo da linha deverá mostrar algo parecido com:

```text
(venv) C:\Users\Guilherme\Documents\nao_pode>
```

## 3. Instalar dependências

Só é necessário fazer isso na primeira instalação ou se o ambiente virtual for recriado.

```bat
python -m pip install fastapi uvicorn websockets
```

## 4. Iniciar o servidor

Com a `venv` ativada:

```bat
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

O terminal deverá mostrar algo parecido com:

```text
Uvicorn running on http://0.0.0.0:8000
```

Não feche esse terminal enquanto estiver jogando.

## 5. Abrir no computador

No navegador do computador:

```text
http://localhost:8000
```

## 6. Descobrir o IP do computador

Abra outro CMD:

```bat
ipconfig
```

Procure o adaptador de rede real que possui Gateway Padrão.

No ambiente usado durante o desenvolvimento, o computador estava em:

```text
192.168.15.5
```

O endereço pode mudar depois que o roteador ou computador reiniciar.

## 7. Abrir nos celulares

Os celulares precisam estar na mesma rede local do computador.

Exemplo:

```text
http://192.168.15.5:8000
```

Troque `192.168.15.5` pelo IPv4 atual do computador.

## 8. Se o celular não conseguir acessar

### Teste no próprio computador

Primeiro confirme:

```text
http://localhost:8000
```

Depois:

```text
http://IP_DO_COMPUTADOR:8000
```

### Conferir o firewall

O Windows precisa permitir conexões TCP de entrada na porta 8000 em rede privada.

PowerShell como Administrador:

```powershell
New-NetFirewallRule -DisplayName "Nao Pode - FastAPI" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Private
```

### Conferir se a rede é privada

PowerShell:

```powershell
Get-NetConnectionProfile
```

Se a Ethernet estiver como `Public`, pode ser alterada para `Private`:

```powershell
Set-NetConnectionProfile -InterfaceAlias "Ethernet" -NetworkCategory Private
```

## 9. Encerrar o servidor

No terminal onde o Uvicorn está executando:

```text
CTRL + C
```

## 10. Sair da venv

```bat
deactivate
```

## 11. Começar novamente em outro dia

Normalmente basta:

```bat
cd %USERPROFILE%\Documents\nao_pode
venv\Scripts\activate
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Depois consultar o IP se necessário:

```bat
ipconfig
```

---

# Como o jogo funciona

1. Todos entram pelo navegador.
2. O primeiro jogador conectado vira HOST.
3. O HOST define:
   - tempo por jogador;
   - quantidade de rodadas.
4. O servidor sorteia a ordem.
5. O jogador da vez toca em **REVELAR CARTA**.
6. Só ele recebe a palavra e as palavras proibidas.
7. O cronômetro começa.
8. Nos últimos 10 segundos, os aparelhos emitem sons de tensão.
9. O HOST seleciona **ACERTOU** ou **ERROU**.
10. O turno avança automaticamente.
11. Depois que todos jogam, começa a próxima rodada.
12. Ao final das rodadas configuradas, é exibido o placar final.

# Reconexão

Cada jogador recebe um código de recuperação de 4 dígitos.

Se o navegador ou Wi‑Fi cair no mesmo celular, a aplicação tenta reconectar automaticamente.

Se precisar usar outro celular:

1. abra o endereço do jogo;
2. escolha **RECONECTAR COM CÓDIGO**;
3. informe o código de 4 dígitos.

O jogador mantém pontuação, posição e participação na partida.

Se o jogador da vez desconectar, a partida é pausada. O HOST pode aguardar a reconexão ou escolher **PULAR JOGADOR**.

# Sons

A versão 0.8 gera os sons diretamente pelo navegador — não existem arquivos MP3 para copiar.

Há:

- som de troca de jogador;
- som de contagem regressiva nos últimos 10 segundos;
- som diferente quando o tempo chega a zero;
- botão para ligar/desligar os sons.

Alguns navegadores móveis bloqueiam áudio antes da primeira interação. Ao tocar em **Entrar**, **Começar jogo**, **Revelar carta** ou outro botão, o áudio é habilitado.

# Arquivo de cartas

O arquivo `cartas.json` deve ficar na mesma pasta que o `app.py`.

Exemplo:

```json
[
  {
    "palavra": "PIZZA",
    "proibidas": [
      "queijo",
      "massa",
      "forno",
      "redonda",
      "italiana"
    ]
  }
]
```

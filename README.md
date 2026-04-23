# inventario-server

Sistema de inventario de ativos com dois componentes:

- `app/`: API central em FastAPI com login, dashboard web e exportacao de dados.
- `agent/`: coletor em Python que roda na maquina cliente, captura informacoes do Windows e envia para a API.

## Visao Geral

O fluxo do projeto funciona assim:

1. O `agent` coleta dados da maquina local, como hostname, usuario, CPU, RAM, IP, serial, BIOS, disco e ultimo boot.
2. Esses dados sao enviados via `POST /checkin` para a API central.
3. A API valida o token do agent e cria ou atualiza o ativo no banco.
4. O painel web permite buscar ativos, visualizar detalhes e exportar o inventario em CSV ou Excel.

## Recursos

- Cadastro e atualizacao automatica de ativos por serial.
- Painel web com autenticacao por usuario e senha.
- Busca por hostname, usuario, serial, fabricante, modelo e IP.
- Exportacao dos dados em `CSV` e `XLSX`.
- Pagina de detalhes de cada ativo.
- Agent com log local de execucao.

## Estrutura Do Projeto

```text
inventario-server/
├── app/
│   ├── auth.py
│   ├── config.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   └── templates/
├── agent/
│   ├── agent.py
│   ├── collector.py
│   ├── sender.py
│   ├── config.json
│   └── agent.log
├── create_user.py
├── requirements.txt
└── README.md
```

## Tecnologias

- Python 3
- FastAPI
- SQLAlchemy
- Jinja2
- OpenPyXL
- Requests
- Psutil
- WMI

## Requisitos

Antes de iniciar, voce precisa de:

- Python 3 instalado
- Banco de dados acessivel pela `DATABASE_URL`
- Ambiente Windows para executar o `agent`, porque a coleta usa `wmi`

## Instalacao

Crie um ambiente virtual e instale as dependencias:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Se voce estiver configurando o agent em Windows, ajuste os comandos conforme o shell usado.

## Variaveis De Ambiente

Crie um arquivo `.env` na raiz do projeto com:

```env
DATABASE_URL=postgresql://usuario:senha@localhost:5432/inventario
AGENT_TOKEN=seu_token_do_agent
SECRET_KEY=sua_chave_secreta
```

### Significado Das Variaveis

- `DATABASE_URL`: conexao usada pela API para acessar o banco.
- `AGENT_TOKEN`: token esperado no header `X-Agent-Token` do endpoint `/checkin`.
- `SECRET_KEY`: chave reservada para configuracoes internas da aplicacao.

## Executando A API

Com o ambiente ativo e o `.env` configurado:

```bash
uvicorn app.main:app --reload
```

A aplicacao ficara disponivel em:

- `http://127.0.0.1:8000`
- tela de login: `http://127.0.0.1:8000/login`

## Criando O Usuario Inicial

O script `create_user.py` cria um usuario administrativo padrao, caso ele ainda nao exista:

```bash
python3 create_user.py
```

Credenciais atuais definidas no script:

- usuario: `admin`
- senha: `admin123`

Se quiser, altere esses valores no arquivo [create_user.py](/home/void-pedro/Documents/projetos/inventario-server/create_user.py) antes de executar.

## Configurando O Agent

O agent usa o arquivo [agent/config.json](/home/void-pedro/Documents/projetos/inventario-server/agent/config.json):

```json
{
  "api_url": "http://127.0.0.1:8000/checkin",
  "timeout": 10,
  "agent_token": "seu_token_do_agent"
}
```

### Campos Do `config.json`

- `api_url`: endpoint de check-in da API central.
- `timeout`: tempo maximo da requisicao HTTP.
- `agent_token`: token enviado no header `X-Agent-Token`.

O valor de `agent_token` precisa ser o mesmo configurado em `AGENT_TOKEN` no `.env` da API.

## Executando O Agent

No host Windows que sera inventariado:

```bash
python agent/agent.py
```

Durante a execucao, o agent:

- coleta os dados da maquina em `agent/collector.py`
- envia o payload em `agent/sender.py`
- registra eventos em `agent/agent.log`

## Endpoints Principais

### Publicos

- `GET /`: health-check simples da API
- `GET /login`: renderiza a tela de login
- `POST /login`: autentica usuario no painel

### Protegidos Por Sessao

- `GET /dashboard`: lista e filtra ativos
- `GET /assets/{asset_id}`: exibe os detalhes de um ativo
- `GET /export/csv`: exporta o inventario em CSV
- `GET /export/xlsx`: exporta o inventario em Excel
- `POST /logout`: encerra a sessao do usuario

### Protegido Por Token Do Agent

- `POST /checkin`: recebe dados do agent e cria ou atualiza o ativo

## Logica Do Check-In

O endpoint `/checkin` funciona desta forma:

- se o payload vier com `serial` e ele ja existir no banco, o ativo e atualizado
- se o serial nao existir, um novo ativo e criado
- a coluna `ultima_comunicacao` e atualizada com o horario atual do servidor

## Campos Coletados Pelo Agent

Entre os principais campos enviados para a API estao:

- hostname
- usuario
- cpu
- ram
- sistema
- ip
- serial
- fabricante
- modelo
- motherboard
- bios_version
- arquitetura
- versao_windows
- mac_address
- disco_total_gb
- disco_livre_gb
- ultimo_boot

## Observacoes Importantes

- O `agent` foi implementado com foco em Windows por causa do uso de `wmi`.
- A autenticacao do painel atualmente usa cookie com `session_user`.
- As tabelas sao criadas automaticamente na inicializacao da API com `Base.metadata.create_all(...)`.
- O projeto hoje esta pronto para uso interno e pode ser expandido com permissoes, logs mais robustos e agendamento do agent.

## Arquivos Principais

- [app/main.py](/home/void-pedro/Documents/projetos/inventario-server/app/main.py): rotas da API, login, dashboard, exportacoes e check-in
- [app/models.py](/home/void-pedro/Documents/projetos/inventario-server/app/models.py): modelos `Asset` e `User`
- [app/schemas.py](/home/void-pedro/Documents/projetos/inventario-server/app/schemas.py): schemas Pydantic da API
- [app/auth.py](/home/void-pedro/Documents/projetos/inventario-server/app/auth.py): hash e validacao de senha
- [agent/collector.py](/home/void-pedro/Documents/projetos/inventario-server/agent/collector.py): coleta dos dados da maquina
- [agent/sender.py](/home/void-pedro/Documents/projetos/inventario-server/agent/sender.py): envio HTTP para a API
- [agent/agent.py](/home/void-pedro/Documents/projetos/inventario-server/agent/agent.py): ponto de entrada do agent

## Proximos Passos Sugeridos

- mover as credenciais padrao do `create_user.py` para variaveis de ambiente
- adicionar expiracao e assinatura mais forte para a sessao web
- criar agendamento automatico do agent no Windows
- separar dependencias da API e do agent em arquivos distintos

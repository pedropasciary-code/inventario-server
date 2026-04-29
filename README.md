# inventario-server

Sistema de inventario de ativos com API central, painel web e agent Windows.

## Visao Geral

O projeto possui dois componentes principais:

- `app/`: API em FastAPI com login, dashboard, detalhes de ativos e exportacao de dados.
- `agent/`: coletor Windows em Python que captura informacoes da maquina e envia para a API.

Fluxo de funcionamento:

1. O `agent` coleta dados locais como hostname, usuario, CPU, RAM, IP, serial, BIOS, disco e ultimo boot.
2. Os dados sao enviados via `POST /checkin` para a API central.
3. A API valida o header `X-Agent-Token` usando o valor de `AGENT_TOKEN`.
4. O ativo e criado ou atualizado no banco, usando serial, MAC Address ou hostname como chave de identificacao.
5. O painel web permite buscar, abrir detalhes e exportar o inventario em CSV ou XLSX.

## Recursos

- Cadastro e atualizacao automatica de ativos por serial, MAC Address ou hostname.
- Painel web com login por usuario e senha.
- Busca por hostname, usuario, serial, fabricante, modelo e IP.
- Dashboard com paginacao, filtro por status e ordenacao por colunas principais.
- Status real por ultima comunicacao: comunicando, atrasado ou inativo.
- Detalhe do ativo com interfaces de rede coletadas pelo agent.
- Histórico dos últimos check-ins no detalhe do ativo.
- Auditoria basica de login, logout, exportacoes e check-ins rejeitados.
- Exportacao em `CSV` e `XLSX` respeitando filtros, ordenacao e status.
- Pagina de detalhes para cada ativo.
- Agent com log rotativo local.
- Agent com selecao de interface principal e envio das interfaces de rede coletadas.
- Retry automatico de envio HTTP.
- Salvamento de payloads falhos em `failed_payloads` para reenvio posterior.
- Instalador Windows com tarefa agendada no logon.

## Estrutura Do Projeto

```text
inventario-server/
├── app/
│   ├── static/
│   ├── templates/
│   ├── auth.py
│   ├── config.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   └── schemas.py
├── agent/
│   ├── agent.py
│   ├── collector.py
│   ├── sender.py
│   └── config.example.json
├── agent-deploy/
│   ├── README.txt
│   ├── config.example.json
│   ├── install_agent.bat
│   ├── install_agent.ps1
│   └── rdp-agent.exe
├── dist/
│   └── rdp-agent.exe
├── create_user.py
├── install_agent.ps1
├── rdp-agent.spec
├── requirements-agent.txt
├── requirements.txt
└── README.md
```

## Tecnologias

- Python 3
- Alembic
- FastAPI
- SQLAlchemy
- Jinja2
- OpenPyXL
- Psycopg
- Requests
- Psutil
- WMI
- PyInstaller

## Requisitos

- Python 3 instalado.
- Banco de dados acessivel pela `DATABASE_URL`.
- Ambiente Windows para executar o `agent`, porque a coleta usa `wmi`.
- Permissao administrativa no Windows para instalar a tarefa agendada do agent.

## Instalacao Da API

No Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

O arquivo `requirements.txt` contem apenas as dependencias da API e das tarefas de banco/exportacao. As dependencias do agent Windows ficam em `requirements-agent.txt`.

Em Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Em servidores Linux/macOS, nao instale `requirements-agent.txt`, pois ele inclui dependencias especificas de Windows.

## Variaveis De Ambiente

Copie `.env.example` para `.env` na raiz do projeto e ajuste os valores:

```env
DATABASE_URL=postgresql://usuario:senha@localhost:5432/inventario
AGENT_TOKEN=seu_token_do_agent
SECRET_KEY=sua_chave_secreta
SESSION_COOKIE_SECURE=false
APP_TIMEZONE=America/Sao_Paulo
```

- `DATABASE_URL`: conexao usada pela API para acessar o banco.
- `AGENT_TOKEN`: token esperado no header `X-Agent-Token` do endpoint `/checkin`.
- `SECRET_KEY`: chave usada para assinar a sessao web.
- `SESSION_COOKIE_SECURE`: use `true` quando a API estiver publicada com HTTPS.
- `APP_TIMEZONE`: fuso usado para formatar datas no painel web.

## Executando A API

Com o ambiente ativo e o `.env` configurado, aplique as migrations do banco:

```bash
alembic upgrade head
```

Depois inicie a API:

```bash
uvicorn app.main:app --reload
```

URLs principais:

- API: `http://127.0.0.1:8000`
- Login: `http://127.0.0.1:8000/login`
- Dashboard: `http://127.0.0.1:8000/dashboard`

As tabelas e indices sao gerenciados pelo Alembic. A aplicacao nao cria mais tabelas automaticamente no startup.

## Criando O Usuario Inicial

O script `create_user.py` cria um usuario do painel sem senha hardcoded.
Modo interativo:

```bash
python create_user.py
```

Tambem e possivel informar usuario por argumento e senha por variavel de ambiente:

```bash
INVENTARIO_ADMIN_PASSWORD="senha-forte-aqui" python create_user.py --username admin
```

A senha precisa ter pelo menos 8 caracteres. O script nao imprime a senha criada.

## Configurando O Agent

O agent usa o arquivo `agent/config.json` em desenvolvimento ou `config.json` na pasta instalada.
Use `agent/config.example.json` como modelo e crie uma copia local chamada `config.json`:

```json
{
  "api_url": "http://127.0.0.1:8000/checkin",
  "timeout": 10,
  "agent_token": "seu_token_do_agent",
  "agent_version": "1.0.0",
  "max_retries": 3,
  "retry_delay_seconds": 5
}
```

- `api_url`: endpoint de check-in da API central.
- `timeout`: tempo maximo da requisicao HTTP em segundos.
- `agent_token`: token enviado no header `X-Agent-Token`.
- `agent_version`: versao informada junto com cada check-in.
- `max_retries`: numero maximo de tentativas de envio.
- `retry_delay_seconds`: intervalo entre tentativas quando o envio falha.

O valor de `agent_token` precisa ser igual ao `AGENT_TOKEN` configurado no `.env` da API.

## Executando O Agent Em Desenvolvimento

No host Windows que sera inventariado:

```powershell
python -m venv .venv-agent
.\.venv-agent\Scripts\Activate.ps1
pip install -r requirements-agent.txt
python agent\agent.py
```

Durante a execucao, o agent:

- coleta dados em `agent/collector.py`
- envia o payload em `agent/sender.py`
- registra eventos em `agent/agent.log`
- salva falhas em `agent/failed_payloads`
- reenvia payloads pendentes na proxima execucao

Para diagnosticar configuracao, coleta local e conectividade sem enviar check-in:

```powershell
python agent\agent.py --diagnose
```

## Instalando O Agent No Windows

O projeto possui dois instaladores:

- `install_agent.ps1`: instala usando `dist/rdp-agent.exe` e `agent/config.json` a partir da raiz do projeto.
- `agent-deploy/install_agent.bat`: instala a partir do pacote distribuivel em `agent-deploy`.

Para instalar pelo pacote distribuivel:

1. Edite `agent-deploy/config.json` e ajuste `api_url` para o endereco real do servidor.
2. Confirme que `agent_token` e igual ao `AGENT_TOKEN` do servidor.
3. Execute `agent-deploy/install_agent.bat` como administrador.
4. O agent sera copiado para `C:\RDPSystemAgent`.
5. A tarefa agendada `RDP System Agent` sera criada para executar no logon.

Para testar apos instalar:

```powershell
C:\RDPSystemAgent\rdp-agent.exe
```

Verifique o log em:

```text
C:\RDPSystemAgent\agent.log
```

## Empacotando O Agent

O arquivo `rdp-agent.spec` define o build do executavel com PyInstaller.

Exemplo:

```powershell
pip install -r requirements-agent.txt
pyinstaller rdp-agent.spec
```

O executavel gerado fica em `dist/rdp-agent.exe`.

## Testes Automatizados

As dependencias de teste ficam em `requirements-dev.txt`.

```bash
pip install -r requirements-dev.txt
pytest
```

Os testes usam SQLite em memoria e sobrescrevem a dependencia de banco da API, sem alterar o PostgreSQL configurado no `.env`.

O workflow `.github/workflows/tests.yml` executa automaticamente `py_compile`, `alembic heads` e `pytest` em pushes para `main` e em pull requests.

## Endpoints Principais

Publicos:

- `GET /`: health-check simples da API.
- `GET /login`: renderiza a tela de login.
- `POST /login`: autentica usuario no painel.

Protegidos por sessao:

- `GET /dashboard`: lista, filtra, ordena e pagina ativos.
- `GET /assets/{asset_id}`: exibe detalhes de um ativo.
- `GET /export/csv`: exporta o inventario em CSV.
- `GET /export/xlsx`: exporta o inventario em Excel.
- `POST /logout`: encerra a sessao.

Protegido por token do agent:

- `POST /checkin`: recebe dados do agent e cria ou atualiza o ativo.

## Migrations Do Banco

As migrations ficam em `migrations/versions`.

Comandos uteis:

```bash
alembic upgrade head
alembic current
alembic history
```

A migration inicial cria as tabelas `assets` e `users` quando elas ainda nao existem. Em bancos que ja tinham tabelas criadas pela versao antiga da aplicacao, ela apenas garante os indices esperados e registra a versao do Alembic.

## Logica Do Check-In

O endpoint `/checkin` identifica ativos nesta ordem:

1. `serial`, quando informado.
2. `mac_address`, quando o serial nao foi suficiente ou nao veio no payload.
3. `hostname`, apenas como fallback quando nao houver serial/MAC e quando o hostname nao for ambiguo.

Se `serial` e `mac_address` apontarem para ativos diferentes, a API retorna `409 Conflict` para evitar mesclar maquinas distintas. Se o payload nao trouxer nenhum dos tres identificadores, a API retorna `422`.

Antes de comparar ou salvar, a API normaliza `serial` e `mac_address` para reduzir duplicidades por diferenca de caixa, espacos ou separador de MAC.

## Campos Coletados Pelo Agent

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
- network_interfaces
- disco_total_gb
- disco_livre_gb
- ultimo_boot
- agent_version

## Historico De Check-Ins

A cada `POST /checkin`, a API grava um snapshot em `asset_checkins` com os principais identificadores e o payload recebido. A pagina de detalhe do ativo exibe os 10 check-ins mais recentes para ajudar auditoria e suporte.

## Auditoria Basica

A tabela `audit_events` registra eventos relevantes da API para investigacao operacional:

- `login_success` e `login_failed`
- `logout`
- `export_csv` e `export_xlsx`
- `checkin_rejected`, incluindo rejeicoes por identidade ausente ou conflito de identidade

Os detalhes adicionais ficam em `details_json`, junto com usuario quando houver sessao web e IP de origem da requisicao.

## Arquivos Principais

- `app/main.py`: rotas da API, login, dashboard, exportacoes e check-in.
- `app/models.py`: modelos `Asset`, `AssetCheckin`, `AuditEvent` e `User`.
- `migrations/versions`: migrations Alembic do banco.
- `app/schemas.py`: schemas Pydantic da API.
- `app/auth.py`: hash e validacao de senha.
- `agent/collector.py`: coleta dos dados da maquina.
- `agent/sender.py`: envio HTTP para a API.
- `agent/agent.py`: ponto de entrada do agent, log e reenvio de payloads falhos.
- `requirements.txt`: dependencias da API e das migrations.
- `requirements-agent.txt`: dependencias do agent Windows e do empacotamento.
- `requirements-dev.txt`: dependencias para executar testes automatizados.
- `tests/`: testes dos fluxos principais da API e do dashboard.
- `install_agent.ps1`: instalador local a partir da raiz do projeto.
- `agent-deploy/install_agent.ps1`: instalador do pacote distribuivel.

## Observacoes Importantes

- O `agent` foi implementado para Windows.
- Use `requirements.txt` para instalar a API e `requirements-agent.txt` para executar ou empacotar o agent.
- A autenticacao do painel usa sessao assinada com `SECRET_KEY`.
- Rode `alembic upgrade head` antes de iniciar a API em um banco novo.
- O script `create_user.py` cria usuario por prompt, argumento ou variaveis de ambiente.
- Nao publique tokens reais em repositorios compartilhados.
- Arquivos `config.json`, logs, executaveis e pastas `build/`/`dist/` sao gerados/localizados por ambiente e ficam fora do Git.

## Proximos Passos Sugeridos

- adicionar testes especificos da coleta WMI em ambiente Windows

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
4. O ativo e criado ou atualizado no banco, usando o serial como chave de identificacao quando disponivel.
5. O painel web permite buscar, abrir detalhes e exportar o inventario em CSV ou XLSX.

## Recursos

- Cadastro e atualizacao automatica de ativos por serial.
- Painel web com login por usuario e senha.
- Busca por hostname, usuario, serial, fabricante, modelo e IP.
- Exportacao em `CSV` e `XLSX`.
- Pagina de detalhes para cada ativo.
- Agent com log rotativo local.
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

Em Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Variaveis De Ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
DATABASE_URL=postgresql://usuario:senha@localhost:5432/inventario
AGENT_TOKEN=seu_token_do_agent
SECRET_KEY=sua_chave_secreta
```

- `DATABASE_URL`: conexao usada pela API para acessar o banco.
- `AGENT_TOKEN`: token esperado no header `X-Agent-Token` do endpoint `/checkin`.
- `SECRET_KEY`: chave reservada para configuracoes internas da aplicacao.

## Executando A API

Com o ambiente ativo e o `.env` configurado:

```bash
uvicorn app.main:app --reload
```

URLs principais:

- API: `http://127.0.0.1:8000`
- Login: `http://127.0.0.1:8000/login`
- Dashboard: `http://127.0.0.1:8000/dashboard`

As tabelas sao criadas automaticamente na inicializacao da API com `Base.metadata.create_all(...)`.

## Criando O Usuario Inicial

O script `create_user.py` cria o usuario administrativo padrao se ele ainda nao existir:

```bash
python create_user.py
```

Credenciais atuais definidas no script:

- usuario: `admin`
- senha: `admin123`

Altere esses valores em `create_user.py` antes de executar em um ambiente real.

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
python agent\agent.py
```

Durante a execucao, o agent:

- coleta dados em `agent/collector.py`
- envia o payload em `agent/sender.py`
- registra eventos em `agent/agent.log`
- salva falhas em `agent/failed_payloads`
- reenvia payloads pendentes na proxima execucao

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
pyinstaller rdp-agent.spec
```

O executavel gerado fica em `dist/rdp-agent.exe`.

## Endpoints Principais

Publicos:

- `GET /`: health-check simples da API.
- `GET /login`: renderiza a tela de login.
- `POST /login`: autentica usuario no painel.

Protegidos por sessao:

- `GET /dashboard`: lista e filtra ativos.
- `GET /assets/{asset_id}`: exibe detalhes de um ativo.
- `GET /export/csv`: exporta o inventario em CSV.
- `GET /export/xlsx`: exporta o inventario em Excel.
- `POST /logout`: encerra a sessao.

Protegido por token do agent:

- `POST /checkin`: recebe dados do agent e cria ou atualiza o ativo.

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
- disco_total_gb
- disco_livre_gb
- ultimo_boot
- agent_version

## Arquivos Principais

- `app/main.py`: rotas da API, login, dashboard, exportacoes e check-in.
- `app/models.py`: modelos `Asset` e `User`.
- `app/schemas.py`: schemas Pydantic da API.
- `app/auth.py`: hash e validacao de senha.
- `agent/collector.py`: coleta dos dados da maquina.
- `agent/sender.py`: envio HTTP para a API.
- `agent/agent.py`: ponto de entrada do agent, log e reenvio de payloads falhos.
- `install_agent.ps1`: instalador local a partir da raiz do projeto.
- `agent-deploy/install_agent.ps1`: instalador do pacote distribuivel.

## Observacoes Importantes

- O `agent` foi implementado para Windows.
- A autenticacao do painel usa cookie `session_user`.
- O script `create_user.py` ainda possui credenciais padrao e deve ser ajustado antes de uso real.
- Nao publique tokens reais em repositorios compartilhados.
- Arquivos `config.json`, logs, executaveis e pastas `build/`/`dist/` sao gerados/localizados por ambiente e ficam fora do Git.

## Proximos Passos Sugeridos

- mover as credenciais padrao do `create_user.py` para variaveis de ambiente
- adicionar expiracao e assinatura mais forte para a sessao web
- separar dependencias da API e do agent em arquivos distintos
- adicionar testes automatizados para rotas principais e coleta do agent

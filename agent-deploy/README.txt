RDP SYSTEM - Pacote de Deploy do Agent

Este pacote instala o agent Windows que coleta informacoes da maquina e envia
o inventario para a API central do RDP SYSTEM.

Arquivos do pacote:
- rdp-agent.exe: executavel do agent.
- config.json: configuracao de conexao com a API.
- config.example.json: modelo seguro para criar um config.json novo.
- install_agent.ps1: script PowerShell que instala o agent e cria a tarefa agendada.
- install_agent.bat: atalho para executar o instalador PowerShell.
- README.txt: instrucoes deste pacote.

Antes de instalar:
1. Se config.json ainda nao existir, copie config.example.json para config.json.
2. Edite o arquivo config.json.
3. Ajuste api_url para o endereco do servidor, mantendo o caminho /checkin.
   Exemplo: http://192.168.0.10:8000/checkin
4. Confirme que agent_token e igual ao AGENT_TOKEN configurado no servidor.
5. Ajuste timeout, max_retries e retry_delay_seconds se a rede for lenta.

Campos do config.json:
- api_url: endpoint da API que recebe o check-in do agent.
- timeout: limite de espera de cada requisicao HTTP, em segundos.
- agent_token: token enviado no header X-Agent-Token.
- agent_version: versao do agent enviada junto com o inventario.
- max_retries: quantidade maxima de tentativas por envio.
- retry_delay_seconds: pausa entre tentativas quando ocorre falha.

Como instalar:
1. Clique com o botao direito em install_agent.bat.
2. Escolha "Executar como administrador".
3. O agent sera instalado em C:\RDPSystemAgent.
4. A tarefa agendada "RDP System Agent" sera criada para rodar no logon.

O que o instalador faz:
- Cria a pasta C:\RDPSystemAgent se ela ainda nao existir.
- Copia rdp-agent.exe para C:\RDPSystemAgent\rdp-agent.exe.
- Copia config.json para C:\RDPSystemAgent\config.json.
- Cria a pasta C:\RDPSystemAgent\failed_payloads.
- Remove uma tarefa agendada antiga com o mesmo nome, se existir.
- Cria uma nova tarefa agendada para executar o agent no logon.

Como testar:
- Execute C:\RDPSystemAgent\rdp-agent.exe.
- Verifique o arquivo C:\RDPSystemAgent\agent.log.
- Acesse o dashboard do servidor e confirme se o ativo apareceu ou foi atualizado.

Reenvio de falhas:
- Se a coleta for concluida mas o envio falhar, o agent salva o payload em
  C:\RDPSystemAgent\failed_payloads.
- Na proxima execucao, o agent tenta reenviar esses payloads antes de enviar a
  coleta atual.
- Payloads reenviados com sucesso sao removidos automaticamente.

Observacoes:
- O servidor da API precisa estar acessivel pela maquina cliente.
- Firewalls e proxies podem bloquear o acesso ao endpoint configurado em api_url.
- O token do config.json deve ser igual ao token configurado no servidor.
- Nao compartilhe config.json com tokens reais fora do ambiente autorizado.

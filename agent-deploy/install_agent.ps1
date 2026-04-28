$ErrorActionPreference = "Stop"

# Resolve caminhos a partir da pasta do pacote distribuível.
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Define onde o agent será instalado e o nome da tarefa agendada.
$targetDir = "C:\RDPSystemAgent"
$taskName = "RDP System Agent"

# Arquivos esperados no pacote de deploy.
$exeSource = Join-Path $packageRoot "rdp-agent.exe"
$configSource = Join-Path $packageRoot "config.json"

# Caminhos finais usados pelo Windows para executar o agent.
$exeTarget = Join-Path $targetDir "rdp-agent.exe"
$configTarget = Join-Path $targetDir "config.json"

Write-Host "Iniciando instalacao do RDP System Agent..." -ForegroundColor Cyan

if (-not (Test-Path $exeSource)) {
    throw "Executavel nao encontrado em: $exeSource"
}

if (-not (Test-Path $configSource)) {
    throw "Arquivo config.json nao encontrado em: $configSource"
}

# Cria a pasta de instalação quando ainda não existir.
if (-not (Test-Path $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir | Out-Null
    Write-Host "Pasta criada: $targetDir"
}
else {
    Write-Host "Pasta ja existe: $targetDir"
}

# Atualiza o executável instalado com a versão que veio no pacote.
Copy-Item -Path $exeSource -Destination $exeTarget -Force
Write-Host "Executavel copiado para: $exeTarget"

# Atualiza a configuração usada para conectar na API.
Copy-Item -Path $configSource -Destination $configTarget -Force
Write-Host "Config copiada para: $configTarget"

# Pasta onde o agent guarda payloads que não puderam ser enviados.
$failedPayloadsDir = Join-Path $targetDir "failed_payloads"
if (-not (Test-Path $failedPayloadsDir)) {
    New-Item -ItemType Directory -Path $failedPayloadsDir | Out-Null
    Write-Host "Pasta criada: $failedPayloadsDir"
}

# Remove tarefa antiga para recriar com os caminhos e parâmetros atuais.
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "Tarefa anterior removida: $taskName"
}

# Ação executada no logon: iniciar o agent dentro da pasta de instalação.
$action = New-ScheduledTaskAction `
    -Execute $exeTarget `
    -WorkingDirectory $targetDir

# Dispara o inventário sempre que o usuário fizer logon.
$trigger = New-ScheduledTaskTrigger -AtLogOn

# Usa o usuário atual com privilégio elevado para permitir coleta completa.
$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Highest

# Mantém a tarefa apta a executar em cenários comuns de notebook/retorno do sistema.
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable

try {
    # Registra a tarefa agendada no Windows.
    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Principal $principal `
        -Settings $settings `
        -Description "Executa o agent de inventario da RDP System no logon" `
        -ErrorAction Stop | Out-Null

    Write-Host "Tarefa criada com sucesso: $taskName" -ForegroundColor Green
    Write-Host "Instalacao concluida com sucesso." -ForegroundColor Green
    Write-Host "Agent instalado em: $targetDir"
}
catch {
    Write-Host "Falha ao criar a tarefa agendada: $($_.Exception.Message)" -ForegroundColor Red
    throw
}

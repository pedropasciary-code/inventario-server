$ErrorActionPreference = "Stop"

# Resolve caminhos a partir da pasta do projeto para copiar o exe e a config.
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceDistDir = Join-Path $projectRoot "dist"
$sourceConfigFile = Join-Path $projectRoot "agent\config.json"

# Define onde o agent ficará instalado e qual tarefa agendada será criada.
$targetDir = "C:\RDPSystemAgent"
$taskName = "RDP System Agent"

# Caminhos de origem e destino dos arquivos principais do agent.
$exeSource = Join-Path $sourceDistDir "rdp-agent.exe"
$exeTarget = Join-Path $targetDir "rdp-agent.exe"
$configTarget = Join-Path $targetDir "config.json"

Write-Host "Iniciando instalacao do RDP System Agent..." -ForegroundColor Cyan

if (-not (Test-Path $exeSource)) {
    throw "Executavel nao encontrado em: $exeSource"
}

if (-not (Test-Path $sourceConfigFile)) {
    throw "Arquivo config.json nao encontrado em: $sourceConfigFile"
}

# Cria a pasta de destino caso a máquina ainda não tenha o agent instalado.
if (-not (Test-Path $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir | Out-Null
    Write-Host "Pasta criada: $targetDir"
}
else {
    Write-Host "Pasta ja existe: $targetDir"
}

# Copia o executável e a configuração que o agent usará em produção.
Copy-Item -Path $exeSource -Destination $exeTarget -Force
Write-Host "Executavel copiado: $exeTarget"

Copy-Item -Path $sourceConfigFile -Destination $configTarget -Force
Write-Host "Config copiada: $configTarget"

# Garante a pasta onde o agent salva payloads que falharam para retry posterior.
$failedPayloadsDir = Join-Path $targetDir "failed_payloads"
if (-not (Test-Path $failedPayloadsDir)) {
    New-Item -ItemType Directory -Path $failedPayloadsDir | Out-Null
    Write-Host "Pasta criada: $failedPayloadsDir"
}

# Remove uma tarefa antiga antes de registrar a versão atual da instalação.
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "Tarefa anterior removida: $taskName"
}

# Define a ação executada pela tarefa: iniciar o exe na pasta de instalação.
$action = New-ScheduledTaskAction `
    -Execute $exeTarget `
    -WorkingDirectory $targetDir

# Dispara o agent a cada logon do usuário.
$trigger = New-ScheduledTaskTrigger -AtLogOn

# Executa com o usuário atual e privilégio elevado para coletar dados completos.
$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Highest

# Permite iniciar mesmo em notebook na bateria e quando a máquina voltar disponível.
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable

try {
    # Registra a tarefa no Agendador do Windows.
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

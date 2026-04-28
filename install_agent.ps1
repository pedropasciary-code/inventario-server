$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceDistDir = Join-Path $projectRoot "dist"
$sourceConfigFile = Join-Path $projectRoot "agent\config.json"

$targetDir = "C:\RDPSystemAgent"
$taskName = "RDP System Agent"

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

# Cria pasta de destino
if (-not (Test-Path $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir | Out-Null
    Write-Host "Pasta criada: $targetDir"
}
else {
    Write-Host "Pasta ja existe: $targetDir"
}

# Copia arquivos principais
Copy-Item -Path $exeSource -Destination $exeTarget -Force
Write-Host "Executavel copiado: $exeTarget"

Copy-Item -Path $sourceConfigFile -Destination $configTarget -Force
Write-Host "Config copiada: $configTarget"

# Garante pasta de payloads falhos
$failedPayloadsDir = Join-Path $targetDir "failed_payloads"
if (-not (Test-Path $failedPayloadsDir)) {
    New-Item -ItemType Directory -Path $failedPayloadsDir | Out-Null
    Write-Host "Pasta criada: $failedPayloadsDir"
}

# Remove tarefa anterior, se existir
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "Tarefa anterior removida: $taskName"
}

# Cria nova tarefa no logon
$action = New-ScheduledTaskAction `
    -Execute $exeTarget `
    -WorkingDirectory $targetDir

$trigger = New-ScheduledTaskTrigger -AtLogOn

$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Highest

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable

try {
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
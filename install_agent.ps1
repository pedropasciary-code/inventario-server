$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceAgentDir = Join-Path $projectRoot "agent"
$targetDir = "C:\RDPSystemAgent"
$taskName = "RDP System Agent"
$pythonPath = "C:\Users\void-pedro\AppData\Local\Python\pythoncore-3.14-64\python.exe"
$agentScript = Join-Path $targetDir "agent.py"

Write-Host "Iniciando instalacao do RDP System Agent..." -ForegroundColor Cyan

if (-not (Test-Path $pythonPath)) {
    throw "Python do ambiente virtual nao encontrado em: $pythonPath"
}

if (-not (Test-Path $sourceAgentDir)) {
    throw "Pasta do agent nao encontrada em: $sourceAgentDir"
}

# Cria pasta de destino
if (-not (Test-Path $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir | Out-Null
    Write-Host "Pasta criada: $targetDir"
} else {
    Write-Host "Pasta ja existe: $targetDir"
}

# Copia arquivos do agent
$filesToCopy = @(
    "agent.py",
    "collector.py",
    "sender.py",
    "config.json"
)

foreach ($file in $filesToCopy) {
    $sourceFile = Join-Path $sourceAgentDir $file
    $targetFile = Join-Path $targetDir $file

    if (-not (Test-Path $sourceFile)) {
        throw "Arquivo nao encontrado: $sourceFile"
    }

    Copy-Item -Path $sourceFile -Destination $targetFile -Force
    Write-Host "Arquivo copiado: $file"
}

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
    -Execute $pythonPath `
    -Argument $agentScript `
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

Write-Host "Tarefa criada com sucesso: $taskName" -ForegroundColor Green
Write-Host "Instalacao concluida com sucesso." -ForegroundColor Green
Write-Host "Agent instalado em: $targetDir"
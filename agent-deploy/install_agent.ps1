$ErrorActionPreference = "Stop"

$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

$targetDir = "C:\RDPSystemAgent"
$taskName = "RDP System Agent"

$exeSource = Join-Path $packageRoot "rdp-agent.exe"
$configSource = Join-Path $packageRoot "config.json"

$exeTarget = Join-Path $targetDir "rdp-agent.exe"
$configTarget = Join-Path $targetDir "config.json"
$backupDir = Join-Path $targetDir "backup"

function Ensure-Directory($path) {
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path | Out-Null
        Write-Host "Pasta criada: $path"
    }
}

function Backup-File($path, $prefix) {
    if (Test-Path $path) {
        Ensure-Directory $backupDir
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $extension = [System.IO.Path]::GetExtension($path)
        $backupPath = Join-Path $backupDir "$prefix`_$timestamp$extension"
        Copy-Item -Path $path -Destination $backupPath -Force
        Write-Host "Backup criado: $backupPath"
    }
}

Write-Host "Iniciando instalacao do RDP System Agent..." -ForegroundColor Cyan

if (-not (Test-Path $exeSource)) {
    throw "Executavel nao encontrado em: $exeSource"
}

if (-not (Test-Path $configSource)) {
    throw "Arquivo config.json nao encontrado em: $configSource"
}

Ensure-Directory $targetDir

Backup-File $exeTarget "rdp-agent"
Copy-Item -Path $exeSource -Destination $exeTarget -Force
Write-Host "Executavel copiado para: $exeTarget"

if (Test-Path $configTarget) {
    Backup-File $configTarget "config"
    Write-Host "Config existente preservada: $configTarget"
}
else {
    Copy-Item -Path $configSource -Destination $configTarget -Force
    Write-Host "Config copiada para: $configTarget"
}

Ensure-Directory (Join-Path $targetDir "failed_payloads")
Ensure-Directory (Join-Path $targetDir "dead_letter_payloads")

$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "Tarefa anterior removida: $taskName"
}

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

    $registeredTask = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
    if (-not $registeredTask) {
        throw "Tarefa agendada nao encontrada apos registro: $taskName"
    }

    Write-Host "Tarefa criada com sucesso: $taskName" -ForegroundColor Green
    Write-Host "Instalacao concluida com sucesso." -ForegroundColor Green
    Write-Host "Agent instalado em: $targetDir"
}
catch {
    Write-Host "Falha ao criar a tarefa agendada: $($_.Exception.Message)" -ForegroundColor Red
    throw
}

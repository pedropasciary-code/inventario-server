param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$pidFile = Join-Path $projectRoot "runtime\api.pid"

if (-not (Test-Path $pidFile)) {
    Write-Host "Arquivo de PID nao encontrado. Nada para parar."
    return
}

$pidValue = (Get-Content $pidFile -ErrorAction Stop | Select-Object -First 1)
if (-not $pidValue) {
    Remove-Item $pidFile -Force
    Write-Host "Arquivo de PID vazio removido."
    return
}

$process = Get-Process -Id ([int]$pidValue) -ErrorAction SilentlyContinue
if (-not $process) {
    Remove-Item $pidFile -Force
    Write-Host "Processo $pidValue nao encontrado. PID removido."
    return
}

if ($Force) {
    Stop-Process -Id $process.Id -Force
}
else {
    Stop-Process -Id $process.Id
}

Remove-Item $pidFile -Force
Write-Host "API parada. PID $pidValue encerrado."

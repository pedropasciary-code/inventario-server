param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$SkipMigrations
)

$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$python = Join-Path $projectRoot "venv\Scripts\python.exe"
$runtimeDir = Join-Path $projectRoot "runtime"
$logsDir = Join-Path $projectRoot "logs"
$pidFile = Join-Path $runtimeDir "api.pid"
$stdoutLog = Join-Path $logsDir "api.out.log"
$stderrLog = Join-Path $logsDir "api.err.log"

if (-not (Test-Path $python)) {
    throw "Python do venv nao encontrado: $python"
}

New-Item -ItemType Directory -Force -Path $runtimeDir, $logsDir | Out-Null

if (Test-Path $pidFile) {
    $existingPid = (Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($existingPid) {
        $existingProcess = Get-Process -Id ([int]$existingPid) -ErrorAction SilentlyContinue
        if ($existingProcess) {
            throw "API ja parece estar em execucao com PID $existingPid. Use scripts\stop_api.ps1 antes de iniciar novamente."
        }
    }
    Remove-Item $pidFile -Force
}

if (-not $SkipMigrations) {
    Push-Location $projectRoot
    try {
        & $python -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) {
            throw "alembic upgrade head falhou com codigo $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
}

$arguments = @(
    "-m", "uvicorn",
    "app.main:app",
    "--host", $HostAddress,
    "--port", [string]$Port
)

$process = Start-Process `
    -FilePath $python `
    -ArgumentList $arguments `
    -WorkingDirectory $projectRoot `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -WindowStyle Hidden `
    -PassThru

Set-Content -Path $pidFile -Value $process.Id
Write-Host "API iniciada em http://${HostAddress}:$Port/ com PID $($process.Id)"
Write-Host "Logs: $stdoutLog e $stderrLog"

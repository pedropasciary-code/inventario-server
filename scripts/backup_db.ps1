param(
    [string]$DatabaseUrl = $env:DATABASE_URL,
    [string]$OutputDir = "backups",
    [ValidateSet("custom", "plain")]
    [string]$Format = "custom"
)

$ErrorActionPreference = "Stop"

function Load-EnvDatabaseUrl {
    if ($DatabaseUrl) {
        return $DatabaseUrl
    }

    $envPath = Join-Path (Get-Location) ".env"
    if (-not (Test-Path $envPath)) {
        throw "DATABASE_URL nao definido no ambiente e arquivo .env nao encontrado."
    }

    foreach ($line in Get-Content $envPath) {
        if ($line -match '^\s*DATABASE_URL\s*=\s*(.+?)\s*$') {
            return $matches[1].Trim('"').Trim("'")
        }
    }

    throw "DATABASE_URL nao encontrado no ambiente nem no arquivo .env."
}

function Get-PostgresParts([string]$Url) {
    $uri = [System.Uri]$Url
    if ($uri.Scheme -notin @("postgresql", "postgres")) {
        throw "DATABASE_URL deve usar postgresql:// ou postgres://."
    }

    $credentials = $uri.UserInfo.Split(":", 2)
    if ($credentials.Count -lt 2) {
        throw "DATABASE_URL deve conter usuario e senha."
    }

    return [pscustomobject]@{
        Host = $uri.Host
        Port = if ($uri.Port -gt 0) { $uri.Port } else { 5432 }
        User = [System.Uri]::UnescapeDataString($credentials[0])
        Password = [System.Uri]::UnescapeDataString($credentials[1])
        Database = $uri.AbsolutePath.TrimStart("/")
    }
}

function Assert-CommandAvailable([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name nao encontrado no PATH. Instale PostgreSQL Client Tools ou adicione a pasta bin do PostgreSQL ao PATH."
    }
}

$url = Load-EnvDatabaseUrl
$parts = Get-PostgresParts $url
Assert-CommandAvailable "pg_dump"

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$extension = if ($Format -eq "custom") { "dump" } else { "sql" }
$outputPath = Join-Path $OutputDir "$($parts.Database)_$timestamp.$extension"

$env:PGPASSWORD = $parts.Password
try {
    $args = @(
        "-h", $parts.Host,
        "-p", [string]$parts.Port,
        "-U", $parts.User,
        "-d", $parts.Database,
        "-f", $outputPath
    )

    if ($Format -eq "custom") {
        $args = @("-Fc") + $args
    }
    else {
        $args = @("-Fp") + $args
    }

    & pg_dump @args
    if ($LASTEXITCODE -ne 0) {
        throw "pg_dump falhou com codigo $LASTEXITCODE."
    }
}
finally {
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
}

Write-Host "Backup criado: $outputPath"

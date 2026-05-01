param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile,
    [string]$DatabaseUrl = $env:DATABASE_URL,
    [switch]$Clean
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

if (-not (Test-Path $BackupFile)) {
    throw "Arquivo de backup nao encontrado: $BackupFile"
}

$url = Load-EnvDatabaseUrl
$parts = Get-PostgresParts $url
$resolvedBackup = (Resolve-Path $BackupFile).Path
$extension = [System.IO.Path]::GetExtension($resolvedBackup).ToLowerInvariant()

$env:PGPASSWORD = $parts.Password
try {
    if ($extension -eq ".sql") {
        Assert-CommandAvailable "psql"
        if ($Clean) {
            Write-Warning "A opcao -Clean e ignorada para backups .sql. Gere o .sql com DROP statements se precisar limpar antes."
        }
        & psql -h $parts.Host -p $parts.Port -U $parts.User -d $parts.Database -f $resolvedBackup
    }
    else {
        Assert-CommandAvailable "pg_restore"
        $args = @(
            "-h", $parts.Host,
            "-p", [string]$parts.Port,
            "-U", $parts.User,
            "-d", $parts.Database
        )
        if ($Clean) {
            $args += @("--clean", "--if-exists")
        }
        $args += $resolvedBackup
        & pg_restore @args
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Restore falhou com codigo $LASTEXITCODE."
    }
}
finally {
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
}

Write-Host "Restore concluido no banco: $($parts.Database)"

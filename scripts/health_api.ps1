param(
    [string]$Url = "http://127.0.0.1:8000/",
    [int]$TimeoutSeconds = 10
)

$ErrorActionPreference = "Stop"

try {
    $response = Invoke-RestMethod -Uri $Url -TimeoutSec $TimeoutSeconds
}
catch {
    throw "Health check falhou em ${Url}: $($_.Exception.Message)"
}

if ($response.status -ne "ok") {
    throw "Health check respondeu, mas status inesperado: $($response | ConvertTo-Json -Compress)"
}

Write-Host "API OK: $Url"

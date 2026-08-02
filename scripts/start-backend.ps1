param(
  [int]$Port = 8000,
  [string]$DbPath = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"

if (-not $DbPath) {
  $DbPath = Join-Path $Backend "wattra.db"
}

$env:PORT = "$Port"
if ($DbPath) {
  $env:WATTRA_DB = $DbPath
}

Set-Location $Backend
Write-Host "Wattra backend starting on http://127.0.0.1:$Port"
Write-Host "DB: $DbPath"
python -m uvicorn app.main:app --host 127.0.0.1 --port $Port --no-server-header

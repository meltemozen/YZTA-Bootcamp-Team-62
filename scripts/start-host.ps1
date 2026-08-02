param(
  [int]$BackendPort = 8000
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$LogDir = Join-Path $Root "logs"
$PidFile = Join-Path $Root ".wattra-backend.pid"
$LocalHealth = "http://127.0.0.1:$BackendPort/api/health"
$PublicHealth = "https://api.altspacelabs.com/api/health"

$RootEnv = Join-Path $Root ".env"
if (Test-Path $RootEnv) {
  foreach ($Line in Get-Content -LiteralPath $RootEnv) {
    $Trimmed = $Line.Trim()
    if (-not $Trimmed -or $Trimmed.StartsWith("#") -or -not $Trimmed.Contains("=")) {
      continue
    }
    $Name, $Value = $Trimmed.Split("=", 2)
    [Environment]::SetEnvironmentVariable($Name.Trim(), $Value.Trim(), "Process")
  }
}

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

$Cloudflared = Get-Service Cloudflared -ErrorAction SilentlyContinue
if (-not $Cloudflared) {
  throw "Cloudflared Windows service is not installed."
}
if ($Cloudflared.Status -ne "Running") {
  Start-Service Cloudflared
  $Cloudflared.WaitForStatus("Running", [TimeSpan]::FromSeconds(15))
}

$Listener = Get-NetTCPConnection -LocalPort $BackendPort -State Listen -ErrorAction SilentlyContinue |
  Select-Object -First 1
if (-not $Listener) {
  $Python = (Get-Command python -ErrorAction Stop).Source
  $env:PORT = "$BackendPort"
  $env:WATTRA_DB = Join-Path $Backend "wattra.db"
  $Process = Start-Process -FilePath $Python -ArgumentList @(
    "-m", "uvicorn", "app.main:app",
    "--host", "127.0.0.1",
    "--port", "$BackendPort",
    "--no-server-header"
  ) -WorkingDirectory $Backend -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $LogDir "backend.out.log") `
    -RedirectStandardError (Join-Path $LogDir "backend.err.log")
  Set-Content -Path $PidFile -Value $Process.Id
  Write-Host "Backend process started (PID $($Process.Id))."
} else {
  Write-Host "Backend is already listening on port $BackendPort."
}

$Ready = $false
for ($Attempt = 1; $Attempt -le 30; $Attempt++) {
  try {
    $Health = Invoke-RestMethod $LocalHealth -TimeoutSec 2
    if ($Health.status -eq "ok") {
      $Ready = $true
      break
    }
  } catch {
    Start-Sleep -Seconds 1
  }
}
if (-not $Ready) {
  throw "Backend did not become healthy. Check logs/backend.err.log."
}

$Public = Invoke-RestMethod $PublicHealth -TimeoutSec 15
if ($Public.status -ne "ok") {
  throw "Public API health check failed."
}

Write-Host "Wattra host is online: https://api.altspacelabs.com"

param(
  [int]$BackendPort = 8000,
  [int]$ExpoPort = 8081
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$BackendScript = Join-Path $PSScriptRoot "start-backend.ps1"
$ExpoScript = Join-Path $PSScriptRoot "start-expo.ps1"
$ApiUrl = "http://127.0.0.1:$BackendPort"

Write-Host "Opening backend and Expo in separate PowerShell windows..."
Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-ExecutionPolicy", "Bypass",
  "-File", $BackendScript,
  "-Port", "$BackendPort"
) -WorkingDirectory $Root

Start-Sleep -Seconds 4

Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-ExecutionPolicy", "Bypass",
  "-File", $ExpoScript,
  "-ApiUrl", $ApiUrl,
  "-Port", "$ExpoPort"
) -WorkingDirectory $Root

Write-Host "Backend: $ApiUrl"
Write-Host "Expo: http://localhost:$ExpoPort"

param(
  [string]$ApiUrl = "https://api.altspacelabs.com",
  [int]$Port = 8081,
  [switch]$NoClear
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Mobile = Join-Path $Root "mobile"

$env:EXPO_PUBLIC_API_URL = $ApiUrl

Set-Location $Mobile
Write-Host "Expo starting on http://localhost:$Port"
Write-Host "Mobile API URL: $ApiUrl"
if ($NoClear) {
  npx expo start --port $Port
} else {
  npx expo start --port $Port --clear
}

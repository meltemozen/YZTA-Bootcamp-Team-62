param(
  [string]$ApiUrl = "https://api.altspacelabs.com"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Mobile = Join-Path $Root "mobile"

$env:EXPO_PUBLIC_API_URL = $ApiUrl
Set-Location $Mobile

npm run doctor
npm run build:ios:production

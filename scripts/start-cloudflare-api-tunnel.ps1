param(
  [int]$BackendPort = 8000,
  [string]$TunnelName = ""
)

$ErrorActionPreference = "Stop"

$Cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue |
  Select-Object -First 1 -ExpandProperty Source
if (-not $Cloudflared) {
  $InstalledExe = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
  if (Test-Path $InstalledExe) {
    $Cloudflared = $InstalledExe
  } else {
    throw "cloudflared bulunamadı. winget install --id Cloudflare.cloudflared çalıştır."
  }
}

$Service = Get-Service cloudflared -ErrorAction SilentlyContinue
if ($Service -and $Service.Status -eq "Running" -and -not $TunnelName) {
  Write-Host "Cloudflare managed tunnel servisi zaten çalışıyor."
  Write-Host "API: https://api.altspacelabs.com"
  exit 0
}

if ($TunnelName) {
  Write-Host "Named tunnel starting: $TunnelName"
  Write-Host "Cloudflare dashboard route should point your public hostname to http://localhost:$BackendPort"
  & $Cloudflared tunnel run $TunnelName
} else {
  Write-Host "Quick tunnel starting for http://localhost:$BackendPort"
  Write-Host "Terminalde çıkan https://*.trycloudflare.com URL'ini mobil API adresi olarak kullan."
  & $Cloudflared tunnel --url "http://localhost:$BackendPort"
}

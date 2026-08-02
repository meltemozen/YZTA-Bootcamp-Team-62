param(
  [int[]]$Ports = @(8000, 8001, 8002, 8081)
)

$ErrorActionPreference = "Continue"

foreach ($Port in $Ports) {
  $pids = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique
  foreach ($ProcessId in $pids) {
    Write-Host "Stopping process $ProcessId on port $Port"
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
  }
}

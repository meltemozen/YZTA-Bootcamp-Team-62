@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\start-host.ps1"
if errorlevel 1 (
  echo.
  echo Host could not be started. See the error above.
  pause
  exit /b 1
)
echo.
echo Host is online. This window can be closed.
pause

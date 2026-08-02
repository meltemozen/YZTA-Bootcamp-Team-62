@echo off
net session >nul 2>&1
if not "%errorlevel%"=="0" (
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

sc.exe stop Cloudflared
sc.exe config Cloudflared start= disabled

echo.
echo The old Cloudflare Tunnel service is stopped and disabled.
pause

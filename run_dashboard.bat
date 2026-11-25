@echo off
title SOC Dashboard - Server & Cloudflare Launcher
color 0A
echo ========================================================
echo   SOC Outbound Late Dashboard - Cloudflare Mode
echo ========================================================
echo.
echo [1/2] Starting Flask Backend Server (http://localhost:5000)...
start "Flask Server (app.py)" cmd /k "py app.py"

timeout /t 3 /nobreak >nul

echo [2/2] Launching Cloudflare Tunnel (HTTP2 Firewall Bypass Mode)...
echo.
echo ========================================================
echo  LOOK BELOW FOR YOUR ONLINE HTTPS URL (trycloudflare.com)
echo ========================================================
echo.
cloudflared.exe tunnel --protocol http2 --url http://localhost:5000
pause

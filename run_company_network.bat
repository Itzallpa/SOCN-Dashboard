@echo off
title SOC Dashboard - Company Network Tunnel Mode (Port 443 HTTPS Bypass)
color 0B
echo ========================================================
echo   SOC Outbound Late Dashboard - Corporate Network Mode
echo ========================================================
echo.
echo [1/2] Starting Flask Backend Server (http://localhost:5000)...
start "Flask Server (app.py)" cmd /k "py app.py"

timeout /t 3 /nobreak >nul

echo [2/2] Connecting via SSH over Port 443 (HTTPS Firewall Bypass)...
echo.
echo ========================================================
echo  LOOK BELOW FOR YOUR ONLINE HTTPS URL (pinggy.link)
echo ========================================================
echo.
ssh -o StrictHostKeyChecking=no -p 443 -R 80:localhost:5000 free.pinggy.io
pause

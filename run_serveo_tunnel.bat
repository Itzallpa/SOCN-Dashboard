@echo off
title SOC Dashboard - Serveo Tunnel Auto-Reconnect
color 0a

echo ============================================================
echo   SOC Operations Portal - Serveo SSH Tunnel Auto-KeepAlive
echo ============================================================
echo.

:loop
echo [%date% %time%] Connecting to Serveo Tunnel (spx-socn-dashboard)...
ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=no -R spx-socn-dashboard:80:127.0.0.1:5000 serveo.net

echo.
echo [%date% %time%] Connection lost or closed by remote host.
echo Reconnecting in 5 seconds...
timeout /t 5 /nobreak > nul
goto loop

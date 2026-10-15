@echo off
title SOC Dashboard - Serveo Tunnel Auto-Reconnect (UAT)
color 0a

echo ============================================================
echo   SOC Operations Portal - Serveo SSH Tunnel (UAT Mode)
echo ============================================================
echo.

:loop
echo [%date% %time%] Connecting to Serveo Tunnel (uat-socn-dashboard)...
ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -i C:\Users\SPXTH71637\.ssh\id_ed25519 -R uat-socn-dashboard:80:127.0.0.1:5000 serveo.net

echo.
echo [%date% %time%] Connection lost or closed by remote host.
echo Reconnecting in 5 seconds...
timeout /t 5 /nobreak > nul
goto loop

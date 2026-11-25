@echo off
title SOC Dashboard Server Launcher
echo ====================================================
echo  Installing / Checking Required Python Packages...
echo ====================================================
py -m pip install -r requirements.txt

echo.
echo ====================================================
echo  Starting SOC Dashboard Server on http://localhost:5000
echo ====================================================
py app.py
pause

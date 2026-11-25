@echo off
title SOC Dashboard UAT Server (port 5001)
py -m pip install -r requirements.txt
echo.
echo ====================================================
echo  Starting SOC Dashboard UAT on http://localhost:5001
echo  (production uses 5000 - run_app.bat)
echo ====================================================
set PORT=5001
py app.py
pause

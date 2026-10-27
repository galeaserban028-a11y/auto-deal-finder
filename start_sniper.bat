@echo off
title AutoDealHunter Telegram Sniper
echo ===================================================
echo   PORNIRE AUTODEALHUNTER — SCANNER TELEGRAM CONTINUU
echo ===================================================
cd /d "%~dp0"
python run_sniper.py
if %errorlevel% neq 0 (
    echo.
    echo Eroare la rulare.
    pause
)

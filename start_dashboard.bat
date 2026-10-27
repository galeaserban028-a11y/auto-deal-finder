@echo off
title AutoDealHunter Dashboard
echo ===================================================
echo   PORNIRE AUTODEALHUNTER — DASHBOARD WEB INTERACTIV
echo ===================================================
cd /d "%~dp0"
python -m streamlit run web/dashboard.py
if %errorlevel% neq 0 (
    echo.
    echo Eroare la pornire. Verificati daca Python este instalat.
    pause
)

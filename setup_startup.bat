@echo off
title AutoDealHunter - Configurare Rulare Automata
echo ========================================================
echo   Configurare AutoDealHunter in Windows Startup
echo ========================================================
echo.
set SCRIPT_DIR=%~dp0
set VBS_PATH=%SCRIPT_DIR%start_silent_background.vbs
set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set SHORTCUT_PATH=%STARTUP_DIR%\AutoDealHunter.lnk

echo Se adauga comanda in Windows Startup...
powershell "$s=(New-Object -COM WScript.Shell).CreateShortcut('%SHORTCUT_PATH%');$s.TargetPath='wscript.exe';$s.Arguments='\"%VBS_PATH%\"';$s.WorkingDirectory='%SCRIPT_DIR%';$s.Save()"

echo.
echo [SUCCES] AutoDealHunter a fost adaugat la pornirea Windows!
echo De acum inainte, cand pornesti calculatorul, sniperul va rula
echo invizibil in fundal si iti va trimite alertele pe Telegram.
echo.
pause

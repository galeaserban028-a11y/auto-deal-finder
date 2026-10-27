@echo off
title AutoDealHunter - Instalare Task Silentios in Fundal
echo ================================================================
echo    INSTALARE AUTODEALHUNTER IN WINDOWS TASK SCHEDULER (24/7)
echo ================================================================
echo.
echo Task-ul verifica la fiecare 10 minute ca sniperul ruleaza si il
echo porneste invizibil daca s-a oprit (de ex. dupa o eroare sau restart).
echo Daca ruleaza deja, copia noua se inchide singura - NU se dubleaza alertele.
echo.

set SCRIPT_DIR=%~dp0
set VBS_PATH=%SCRIPT_DIR%start_silent_background.vbs

schtasks /create /f /tn "AutoDealHunter_SilentSniper" /tr "wscript.exe \"%VBS_PATH%\"" /sc minute /mo 10 /ru "%USERNAME%"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ================================================================
    echo [SUCCES!] AutoDealHunter a fost instalat in Windows Task Scheduler!
    echo.
    echo - Ruleaza complet invizibil, verificat la fiecare 10 minute.
    echo - Vei primi alertele direct pe Telegram.
    echo - Dezinstalare: schtasks /delete /tn "AutoDealHunter_SilentSniper" /f
    echo ================================================================
) else (
    echo.
    echo [EROARE] Nu s-a putut crea task-ul. Incearca sa rulezi ca Administrator.
)
echo.
pause

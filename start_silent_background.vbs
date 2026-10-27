' Ruleaza sniperul complet invizibil in fundal, fara fereastra deschisa.
' Porneste din folderul proiectului (altfel Task Scheduler/Startup nu gasesc run_sniper.py).
' Daca sniperul ruleaza deja, noua instanta se inchide singura (nu se dubleaza alertele).
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = scriptDir
WshShell.Run "python """ & scriptDir & "\run_sniper.py""", 0, False

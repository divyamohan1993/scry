' Scry - Silent Launcher
' Double-click this to start Scry without any console window
' The web control panel will open in your browser

Set WshShell = CreateObject("WScript.Shell")
ScriptPath = Replace(WScript.ScriptFullName, WScript.ScriptName, "")

' Run the batch file silently (0 = hidden, False = don't wait)
WshShell.Run """" & ScriptPath & "scripts\scry_launcher.bat""", 0, False

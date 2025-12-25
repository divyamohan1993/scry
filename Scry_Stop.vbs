' Scry - Silent Closer
' Double-click this to stop Scry without any console window

Set WshShell = CreateObject("WScript.Shell")
ScriptPath = Replace(WScript.ScriptFullName, WScript.ScriptName, "")

' Run the stop script silently (0 = hidden, False = don't wait)
WshShell.Run """" & ScriptPath & "scripts\stop.bat""", 0, False

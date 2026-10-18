' ============================================================
' MacroEngine - Inicializador Silencioso (Background)
' Executa o servidor Python sem abrir janela de prompt de comando
' ============================================================

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

strScriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strScriptDir

strPyw = ""

' 1. Verifica ambiente virtual local (.venv)
If fso.FileExists(strScriptDir & "\.venv\Scripts\pythonw.exe") Then
    strPyw = strScriptDir & "\.venv\Scripts\pythonw.exe"
' 2. Verifica instalação no LocalAppData do usuário
ElseIf fso.FileExists(WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python312\pythonw.exe") Then
    strPyw = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python312\pythonw.exe"
ElseIf fso.FileExists(WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python311\pythonw.exe") Then
    strPyw = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python311\pythonw.exe"
ElseIf fso.FileExists(WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python310\pythonw.exe") Then
    strPyw = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python310\pythonw.exe"
Else
    strPyw = "pythonw.exe"
End If

strCmd = """" & strPyw & """ """ & strScriptDir & "\server.py"""
WshShell.Run strCmd, 0, False

Set WshShell = Nothing
Set fso = Nothing

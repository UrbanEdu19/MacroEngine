@echo off
setlocal enabledelayedexpansion
title MacroEngine - Ativar Inicializacao com o Windows

echo ============================================================
echo   MACROENGINE - CONFIGURACAO DE AUTO-START
echo ============================================================
echo.
echo Configurando o servidor para iniciar automaticamente junto
echo com o Windows em segundo plano, sem janela preta.
echo.

cd /d "%~dp0"

:: 1. Registra chave no Registro do Windows (HKCU Run)
set "VBS_PATH=%~dp0run_silent.vbs"
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_FOLDER%\MacroEngineServer.lnk"

:: Remove chave legada caso exista
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "RemoteMasterProServer" /f >nul 2>&1

reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "MacroEngineServer" /t REG_SZ /d "wscript.exe \"%VBS_PATH%\"" /f >nul 2>&1

if %errorlevel% equ 0 (
    echo [OK] Chave de inicializacao adicionada com sucesso no Registro do Windows.
    :: Remove atalho duplicado da pasta Startup se existir
    if exist "%SHORTCUT_PATH%" del /f /q "%SHORTCUT_PATH%" >nul 2>&1
) else (
    echo [AVISO] Nao foi possivel gravar no Registro. Usando pasta Startup como fallback...
    powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\"%VBS_PATH%\"'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'MacroEngine Desktop Server'; $s.Save()" >nul 2>&1
    if exist "%SHORTCUT_PATH%" (
        echo [OK] Atalho criado na pasta de Inicializacao do Windows.
    )
)

echo.
echo ============================================================
echo   SUCESSO! O Servidor agora iniciara automaticamente
echo   sempre que voce ligar ou reiniciar o computador!
echo ============================================================
echo.
echo Deseja iniciar o servidor em segundo plano agora mesmo? [S/N]
set /p START_NOW="> "

if /i "%START_NOW%"=="S" (
    wscript.exe "%VBS_PATH%"
    echo.
    echo [OK] Servidor iniciado silenciosamente em segundo plano!
    timeout /t 2 >nul
)

exit /b 0

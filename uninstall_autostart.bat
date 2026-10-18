@echo off
setlocal
title MacroEngine - Desativar Inicializacao com o Windows

echo ============================================================
echo   MACROENGINE - REMOVER AUTO-START
echo ============================================================
echo.
echo Removendo o servidor da inicializacao automatica do Windows...
echo.

:: 1. Remove do Registro HKCU Run
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "MacroEngineServer" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "RemoteMasterProServer" /f >nul 2>&1
echo [OK] Chaves do Registro removidas com sucesso.

:: 2. Remove do Startup Folder
set "SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\MacroEngineServer.lnk"
set "OLD_SHORTCUT=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\RemoteMasterProServer.lnk"
if exist "%SHORTCUT_PATH%" del /f /q "%SHORTCUT_PATH%" >nul 2>&1
if exist "%OLD_SHORTCUT%" del /f /q "%OLD_SHORTCUT%" >nul 2>&1
echo [OK] Atalho da pasta Inicializar removido.

echo.
echo ============================================================
echo   O Servidor NAO ira mais iniciar automaticamente com o Windows.
echo   Voce ainda pode roda-lo manualmente via start_server.bat.
echo ============================================================
echo.
pause
exit /b 0

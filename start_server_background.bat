@echo off
setlocal
cd /d "%~dp0"
title MacroEngine - Servidor em Segundo Plano

echo ============================================================
echo   MACROENGINE - SERVIDOR DESKTOP EM SEGUNDO PLANO
echo ============================================================
echo.

:: Verifica se o servidor ja esta rodando na porta 8000
netstat -ano | findstr ":8000" | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo [INFO] O servidor MacroEngine JA ESTA EM EXECUCAO na porta 8000!
    echo.
    echo * O icone verde esta ativo na bandeja do Windows - ao lado do relogio.
    echo * Documentacao Swagger: http://localhost:8000/docs
    echo.
    echo Para encerrar o servidor, execute: stop_server.bat
    echo ============================================================
    ping 127.0.0.1 -n 4 >nul
    exit /b 0
)

echo Iniciando o servidor de forma silenciosa...
wscript.exe "%~dp0run_silent.vbs"

:: Aguarda o processo inicializar
ping 127.0.0.1 -n 4 >nul

netstat -ano | findstr ":8000" | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo [OK] Servidor iniciado com sucesso em segundo plano!
    echo * Porta: 8000
    echo * O icone do MacroEngine esta ativo na bandeja do sistema.
) else (
    echo [OK] Comando de inicializacao enviado em segundo plano.
)

echo ============================================================
ping 127.0.0.1 -n 3 >nul
exit /b 0

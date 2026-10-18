@echo off
setlocal
title MacroEngine - Configuracao do Firewall do Windows

echo ============================================================
echo   LIBERAR PORTAS NO FIREWALL DO WINDOWS
echo ============================================================
echo.
echo Este utilitario adiciona as regras de entrada necessarias no
echo Firewall do Windows para permitir a conexao do celular via Wi-Fi.
echo.
echo Requer permissoes de Administrador.
echo.

:: Verifica se esta rodando como Administrador
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [AVISO] Solicitando elevacao de Administrador...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~dp0register_firewall.bat\"\"' -Verb RunAs"
    exit /b 0
)

echo [1/2] Liberando Porta TCP 8000 (API REST e Transmissao de Tela)...
netsh advfirewall firewall delete rule name="MacroEngine (HTTP 8000)" >nul 2>&1
netsh advfirewall firewall delete rule name="Remote Master Pro (HTTP 8000)" >nul 2>&1
netsh advfirewall firewall add rule name="MacroEngine (HTTP 8000)" dir=in action=allow protocol=TCP localport=8000 profile=any >nul
if %errorlevel% equ 0 (
    echo [OK] Porta TCP 8000 liberada com sucesso!
) else (
    echo [ERRO] Falha ao configurar regra TCP 8000.
)

echo.
echo [2/2] Liberando Porta UDP 50005 (Transmissao de Audio sem Fio)...
netsh advfirewall firewall delete rule name="MacroEngine (Audio UDP 50005)" >nul 2>&1
netsh advfirewall firewall delete rule name="Remote Master Pro (Audio UDP 50005)" >nul 2>&1
netsh advfirewall firewall add rule name="MacroEngine (Audio UDP 50005)" dir=in action=allow protocol=UDP localport=50005 profile=any >nul
if %errorlevel% equ 0 (
    echo [OK] Porta UDP 50005 liberada com sucesso!
) else (
    echo [ERRO] Falha ao configurar regra UDP 50005.
)

echo.
echo ============================================================
echo   FIREWALL CONFIGURADO COM SUCESSO!
echo   Seu celular agora pode se conectar diretamente ao PC via Wi-Fi.
echo ============================================================
echo.
pause
exit /b 0

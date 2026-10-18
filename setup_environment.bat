@echo off
setlocal enabledelayedexpansion
title MacroEngine - Setup de Ambiente (GitHub)

echo ============================================================
echo   MACROENGINE - INSTALACAO DE AMBIENTE PYTHON
echo ============================================================
echo.
cd /d "%~dp0"

:: 1. Procurar interpretador Python disponível
set "PY_CMD="

py -3.12 --version >nul 2>&1
if not errorlevel 1 set "PY_CMD=py -3.12" & goto :found_python

py --version >nul 2>&1
if not errorlevel 1 set "PY_CMD=py" & goto :found_python

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :found_python
)

if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :found_python
)

python --version >nul 2>&1
if not errorlevel 1 set "PY_CMD=python" & goto :found_python

echo [ERRO] Python nao foi encontrado no sistema!
echo Instale o Python 3.10 ou superior em: https://www.python.org/downloads/
echo Lembre-se de marcar "Add python.exe to PATH" durante a instalacao.
echo.
pause
exit /b 1

:found_python
echo Interpretador localizado: %PY_CMD%
echo.

:: 2. Criar ambiente virtual se nao existir
if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Criando ambiente virtual Python (.venv)...
    %PY_CMD% -m venv .venv
    if errorlevel 1 (
        echo [AVISO] Nao foi possivel criar .venv. Instalando diretamente no Python do sistema...
        set "VENV_PY=%PY_CMD%"
    ) else (
        echo [OK] Ambiente virtual criado com sucesso!
        set "VENV_PY=.venv\Scripts\python.exe"
    )
) else (
    echo [1/3] Ambiente virtual (.venv) ja existente.
    set "VENV_PY=.venv\Scripts\python.exe"
)

:: 3. Instalar dependencias
echo.
echo [2/3] Atualizando gerenciador pip e instalando dependencias...
"%VENV_PY%" -m pip install --upgrade pip --quiet
"%VENV_PY%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias do requirements.txt.
    pause
    exit /b 1
)
echo [OK] Todas as dependencias foram instaladas com sucesso!

:: 4. Configuracoes adicionais
echo.
echo [3/3] Deseja configurar o Firewall do Windows agora? (Recomendado para Wi-Fi) [S/N]
set /p CFG_FIREWALL="> "
if /i "%CFG_FIREWALL%"=="S" (
    call "%~dp0register_firewall.bat"
)

echo.
echo Deseja ativar o inicio automatico com o Windows (Auto-Start)? [S/N]
set /p CFG_AUTO="> "
if /i "%CFG_AUTO%"=="S" (
    call "%~dp0install_autostart.bat"
)

echo.
echo ============================================================
echo   AMBIENTE PRONTO PARA USO!
echo   Para iniciar o servidor: Execute start_server.bat
echo   Ou para segundo plano:   Execute start_server_background.bat
echo ============================================================
echo.
pause
exit /b 0

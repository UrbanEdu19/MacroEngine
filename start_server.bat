@echo off
setlocal enabledelayedexpansion
title MacroEngine - Servidor Desktop

echo ============================================================
echo   Iniciando MacroEngine Server (FastAPI + UDP)
echo ============================================================
echo.

cd /d "%~dp0"

:: 1. Procurar interpretador Python disponível
set "PY_CMD="

:: Tenta o launcher oficial do Windows py -3.12
py -3.12 --version >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=py -3.12"
    goto :found_python
)

:: Tenta o launcher py geral
py --version >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=py"
    goto :found_python
)

:: Tenta caminho padrão do instalador de usuário no Windows
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :found_python
)

if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :found_python
)

if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    goto :found_python
)

:: Tenta python padrão do PATH
python --version >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=python"
    goto :found_python
)

:not_found
echo [ERRO] O Python nao foi localizado automaticamente.
echo Certifique-se de que o Python esteja instalado.
echo.
pause
exit /b 1

:found_python
echo Interpretador localizado: %PY_CMD%
echo.

echo [1/2] Verificando dependencias do Python...
%PY_CMD% -m pip install -r requirements.txt --quiet

echo.
echo [2/2] Iniciando Servidor...
echo.
%PY_CMD% server.py

pause

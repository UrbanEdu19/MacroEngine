@echo off
cd /d "%~dp0"
echo Iniciando MacroEngine em segundo plano...
wscript.exe "%~dp0run_silent.vbs"
echo [OK] Servidor iniciado silenciosamente em segundo plano (porta 8000).
timeout /t 2 >nul
exit /b 0

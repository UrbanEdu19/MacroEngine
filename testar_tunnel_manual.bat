@echo off
chcp 65001 >nul
title Teste Manual do Cloudflare Quick Tunnel - MacroEngine
color 0B
cls
echo ===============================================================================
echo            MACROENGINE - TESTE MANUAL DO CLOUDFLARE QUICK TUNNEL
echo ===============================================================================
echo.
echo NOTA: No uso normal, o MacroEngine gerencia o cloudflared automaticamente
echo em segundo plano. Voce NAO precisa abrir este executavel manualmente!
echo.
echo Este script serve para demonstrar como o cloudflared cria a URL HTTPS publica
echo conectando o seu servidor local (http://localhost:8000) a nuvem da Cloudflare.
echo.
echo Iniciando conexao com a Cloudflare...
echo.
echo -------------------------------------------------------------------------------
echo Aguarde alguns segundos. Procure pela linha que contem:
echo "https://....trycloudflare.com"
echo -------------------------------------------------------------------------------
echo.
"%~dp0cloudflared.exe" tunnel --url http://127.0.0.1:8000 --no-autoupdate
pause

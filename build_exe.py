"""
Script de Compilacao Automatizada do MacroEngineServer.exe (Windows)
Compativel com PyInstaller, System Tray (pystray), Windows Media Session e OBS WebSocket v5.
Preparado para testes locais e atualizacoes futuras.
"""

import os
import sys
import shutil
import subprocess

# Forcar encoding UTF-8 na saida padrao
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(SERVER_DIR, "assets")
ICON_PATH = os.path.join(ASSETS_DIR, "app_icon.ico")
DIST_DIR = os.path.join(SERVER_DIR, "dist")
BUILD_DIR = os.path.join(SERVER_DIR, "build")

def build():
    print("=" * 60)
    print(">> Iniciando compilacao do MacroEngineServer.exe (v1.2.6v)")
    print("=" * 60)

    # Comandos e flags do PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name", "MacroEngineServer",
        "--windowed", # Roda silencioso na bandeja (System Tray) sem tela preta do cmd
        f"--icon={ICON_PATH}",
        "--add-data", f"{ASSETS_DIR};assets",
        "--hidden-import", "winsdk",
        "--hidden-import", "winsdk.windows.media.control",
        "--hidden-import", "winsdk.windows.storage.streams",
        "--hidden-import", "obswebsocket",
        "--hidden-import", "pystray",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL.Image",
        "--hidden-import", "PIL.ImageDraw",
        "--hidden-import", "psutil",
        "--hidden-import", "win32gui",
        "--hidden-import", "win32process",
        "--hidden-import", "win32con",
        "--hidden-import", "win32api",
        "--hidden-import", "requests",
        "--hidden-import", "urllib3",
        os.path.join(SERVER_DIR, "server.py")
    ]

    print("\n[+] Executando PyInstaller...")
    res = subprocess.run(cmd, cwd=SERVER_DIR)
    if res.returncode != 0:
        print(f"[!] Falha no PyInstaller (codigo {res.returncode})")
        sys.exit(res.returncode)

    target_dist = os.path.join(DIST_DIR, "MacroEngineServer")
    print(f"\n[+] Copiando recursos auxiliares para {target_dist}...")

    # 1. Copiar cloudflared.exe se presente
    cf_exe = os.path.join(SERVER_DIR, "cloudflared.exe")
    if os.path.exists(cf_exe):
        shutil.copy2(cf_exe, os.path.join(target_dist, "cloudflared.exe"))
        print("  -> cloudflared.exe copiado com sucesso.")

    # 2. Copiar config.json
    cfg_file = os.path.join(SERVER_DIR, "config.json")
    if os.path.exists(cfg_file):
        shutil.copy2(cfg_file, os.path.join(target_dist, "config.json"))
        print("  -> config.json copiado com sucesso.")

    # 3. Criar diretorio shared_files
    sf_dir = os.path.join(target_dist, "shared_files")
    os.makedirs(sf_dir, exist_ok=True)
    print("  -> Pasta shared_files criada.")

    # 4. Copiar SEU_CODIGO_DE_PAREAMENTO.txt
    pin_file = os.path.join(SERVER_DIR, "SEU_CODIGO_DE_PAREAMENTO.txt")
    if os.path.exists(pin_file):
        shutil.copy2(pin_file, os.path.join(target_dist, "SEU_CODIGO_DE_PAREAMENTO.txt"))
        print("  -> SEU_CODIGO_DE_PAREAMENTO.txt copiado.")

    # 5. Criar script de inicializacao amigavel de teste
    test_bat_content = """@echo off
title MacroEngine Server (Executavel de Teste)
cd /d "%~dp0"
echo ========================================================
echo   Iniciando MacroEngineServer.exe em segundo plano...
echo   Verifique o icone na bandeja do sistema (proximo ao relogio).
echo ========================================================
start "" "%~dp0MacroEngineServer.exe"
"""
    with open(os.path.join(target_dist, "Iniciar_Servidor.bat"), "w", encoding="utf-8") as f:
        f.write(test_bat_content)

    print("\n" + "=" * 60)
    print("MacroEngineServer.exe compilado com sucesso!")
    print(f"Localizacao: {target_dist}")
    print("=" * 60)

if __name__ == "__main__":
    build()

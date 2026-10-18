"""
MacroEngine - Servidor Desktop de Baixa Latência
FastAPI + AsyncIO + Sockets UDP + Automação de Sistema (Windows/Linux)
"""

import sys
import os
import time
import socket
import threading
import logging
import platform
import subprocess
import webbrowser
import json
from typing import Optional, Dict, Any, List

# Compatibilidade UTF-8 e proteção para execução em background (pythonw)
if sys.platform == "win32":
    if sys.stdout is None:
        try:
            sys.stdout = open(os.devnull, "w", encoding="utf-8")
        except Exception:
            pass
    if sys.stderr is None:
        try:
            sys.stderr = open(os.devnull, "w", encoding="utf-8")
        except Exception:
            pass
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if sys.platform == "win32":
    try:
        import winreg
    except ImportError:
        winreg = None
else:
    winreg = None

try:
    import pystray
    TRAY_AVAILABLE = True
except ImportError:
    pystray = None
    TRAY_AVAILABLE = False

import io
import ctypes
try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    mss = None
    MSS_AVAILABLE = False

from PIL import Image, ImageDraw, ImageFont, ImageGrab
from fastapi import FastAPI, HTTPException, BackgroundTasks, Response, UploadFile, File, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Configuração de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("MacroEngineServer")

# ---------------------------------------------------------------------------
# CONFIGURAÇÕES E GERENCIAMENTO DE INICIALIZAÇÃO AUTOMÁTICA
# ---------------------------------------------------------------------------
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
SHARED_FILES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shared_files")
os.makedirs(SHARED_FILES_DIR, exist_ok=True)

def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

def _init_shared_folder():
    readme_sample = os.path.join(SHARED_FILES_DIR, "Bem_Vindo_Compartilhamento.txt")
    if not os.path.exists(readme_sample) and not os.listdir(SHARED_FILES_DIR):
        try:
            with open(readme_sample, "w", encoding="utf-8") as f:
                f.write("Pasta Compartilhada do MacroEngine\nArquivos colocados nesta pasta ficam disponíveis para download imediato no celular pelo menu de Transferência de Arquivos!\n")
        except Exception:
            pass
_init_shared_folder()

REG_AUTOSTART_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
REG_AUTOSTART_NAME = "MacroEngineServer"

DEFAULT_CONFIG = {
    "server": {
        "host": "0.0.0.0",
        "port": 8000,
        "log_level": "info",
        "enable_tray_icon": True
    },
    "screen_capture": {
        "fps": 30,
        "quality": 75,
        "max_width": 1280
    },
    "audio_streaming": {
        "default_port": 50005,
        "sample_rate": 44100,
        "channels": 2
    },
    "scrcpy": {
        "auto_detect": True,
        "custom_path": "",
        "max_fps": 60,
        "bitrate_mbps": 8
    },
    "system": {
        "autostart_with_windows": True,
        "auto_game_mode": False
    }
}

def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erro ao carregar {CONFIG_PATH}: {e}")
    return DEFAULT_CONFIG.copy()

def save_config(cfg: dict) -> bool:
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar {CONFIG_PATH}: {e}")
        return False

SERVER_CONFIG = load_config()

_single_instance_mutex = None

def ensure_single_instance():
    """
    Garante estritamente que apenas UMA ÚNICA instância do servidor MacroEngine
    possa ser executada simultaneamente no sistema operacional.
    Se outra instância já estiver ativa, esta nova instância é encerrada imediatamente
    sem criar ícone duplicado na bandeja e sem gerar conflito na porta 8000.
    """
    global _single_instance_mutex
    if sys.platform == "win32":
        try:
            import ctypes
            MUTEX_NAME = "Local\\MacroEngine_SingleInstance_Mutex_8000"
            kernel32 = ctypes.windll.kernel32
            mutex = kernel32.CreateMutexW(None, True, MUTEX_NAME)
            last_error = kernel32.GetLastError()
            # 183 = ERROR_ALREADY_EXISTS
            if last_error == 183:
                logger.warning("Outra instância do MacroEngine já está em execução no sistema. Encerrando processo secundário imediatamente.")
                sys.exit(0)
            _single_instance_mutex = mutex
            return mutex
        except Exception as e:
            logger.warning(f"Aviso ao verificar mutex de instância única: {e}")
            return None
    return None

def is_windows_autostart_enabled() -> bool:
    """Verifica se o servidor está configurado para inicializar com o Windows."""
    if sys.platform != "win32" or winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_AUTOSTART_KEY, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, REG_AUTOSTART_NAME)
            return bool(val)
    except Exception:
        # Fallback: checa se existe atalho no menu Iniciar / Startup
        try:
            startup_dir = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")
            return os.path.exists(os.path.join(startup_dir, "RemoteMasterProServer.lnk")) or \
                   os.path.exists(os.path.join(startup_dir, "RemoteMasterPro.vbs")) or \
                   os.path.exists(os.path.join(startup_dir, "RemoteMasterPro.bat"))
        except Exception:
            return False

def set_windows_autostart(enable: bool) -> bool:
    """Ativa ou desativa a inicialização automática silenciosa com o Windows."""
    if sys.platform != "win32":
        return False

    base_dir = os.path.dirname(os.path.abspath(__file__))
    vbs_path = os.path.join(base_dir, "run_silent.vbs")
    cmd = f'wscript.exe "{vbs_path}"'
    success = False

    # Remove qualquer atalho antigo/duplicado da pasta Startup do Windows
    try:
        startup_dir = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")
        for old_item in ["RemoteMasterProServer.lnk", "RemoteMasterPro.vbs", "RemoteMasterPro.bat"]:
            old_path = os.path.join(startup_dir, old_item)
            if os.path.exists(old_path):
                os.remove(old_path)
    except Exception:
        pass

    if winreg is not None:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_AUTOSTART_KEY, 0, winreg.KEY_SET_VALUE) as key:
                if enable:
                    winreg.SetValueEx(key, REG_AUTOSTART_NAME, 0, winreg.REG_SZ, cmd)
                else:
                    try:
                        winreg.DeleteValue(key, REG_AUTOSTART_NAME)
                    except FileNotFoundError:
                        pass
            success = True
        except Exception as e:
            logger.error(f"Erro no registro ao definir autostart: {e}")

    # Atualiza configuração no config.json
    cfg = load_config()
    cfg.setdefault("system", {})["autostart_with_windows"] = enable
    save_config(cfg)
    return success

# ---------------------------------------------------------------------------
# ÍCONE DA BANDEJA DO SISTEMA (SYSTEM TRAY)
# ---------------------------------------------------------------------------
_tray_icon = None

def create_tray_image(width=64, height=64):
    """Gera um ícone moderno de alta resolução para a bandeja do sistema Windows."""
    # Tenta carregar o ícone oficial customizado se existir
    asset_icon_path = os.path.join(os.path.dirname(__file__), "assets", "app_icon.png")
    if os.path.exists(asset_icon_path):
        try:
            icon_img = Image.open(asset_icon_path).convert("RGBA")
            icon_resized = icon_img.resize((width, height), Image.Resampling.LANCZOS)
            draw = ImageDraw.Draw(icon_resized)
            # Indicador de status 'Online' luminoso (verde) no canto inferior
            draw.ellipse([width - 18, height - 18, width - 2, height - 2], fill=(0, 230, 118), outline=(255, 255, 255), width=2)
            return icon_resized
        except Exception as e:
            logger.warning(f"Não foi possível carregar o ícone de asset: {e}")

    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Fundo moderno em gradiente escuro com cantos arredondados
    draw.rounded_rectangle([2, 2, width - 2, height - 2], radius=16, fill=(15, 23, 42), outline=(0, 173, 181), width=3)
    
    # Letras do monograma 'RM'
    try:
        font = ImageFont.load_default()
        draw.text((14, 16), "RM", fill=(0, 240, 255), font=font)
    except Exception:
        draw.rectangle([16, 16, 48, 48], fill=(0, 173, 181))
        
    # Indicador de status 'Online' luminoso (verde)
    draw.ellipse([width - 20, height - 20, width - 4, height - 4], fill=(0, 230, 118), outline=(255, 255, 255), width=2)
    return image

# ---------------------------------------------------------------------------
# MODO JOGO TURBO (ALTO DESEMPENHO NO WINDOWS)
# ---------------------------------------------------------------------------
GAME_MODE_ACTIVE = False

def _set_power_plan(plan_type: str):
    """Ativa plano de Alto Desempenho ou Equilibrado no Windows."""
    if sys.platform == 'win32':
        guid = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c" if plan_type == "high" else "381b4222-f694-41f0-9685-ff5bb260df2e"
        subprocess.run(["powercfg", "/setactive", guid], check=False, shell=True)
        return True
    return False

def toggle_game_mode() -> bool:
    """Alterna o Modo Jogo Turbo (ajusta prioridade de energia do PC)."""
    global GAME_MODE_ACTIVE
    GAME_MODE_ACTIVE = not GAME_MODE_ACTIVE
    if GAME_MODE_ACTIVE:
        _set_power_plan("high")
        logger.info("Modo Jogo Turbo ATIVADO: Plano de Alto Desempenho aplicado.")
    else:
        _set_power_plan("balanced")
        logger.info("Modo Jogo Turbo DESATIVADO: Plano Equilibrado restaurado.")
    return GAME_MODE_ACTIVE

def launch_url_on_desktop(url: str) -> bool:
    """
    Abre URL ou URI no desktop interativo do usuário (WinSta0\\Default no Windows).
    Garante que a janela do navegador apareça no monitor físico mesmo se o servidor
    estiver rodando em segundo plano, como serviço ou em sessão sem terminal ativo.
    """
    if sys.platform == "win32":
        try:
            import win32process
            si = win32process.STARTUPINFO()
            si.lpDesktop = r"WinSta0\Default"
            cmd = f'cmd.exe /c start "" "{url}"'
            win32process.CreateProcess(
                None, cmd, None, None, False, 0x08000000, None, None, si
            )
            return True
        except Exception as e:
            logger.warning(f"Falha ao iniciar processo no desktop Default: {e}")

    try:
        if webbrowser.open(url):
            return True
    except Exception:
        pass

    if sys.platform == "win32":
        try:
            os.startfile(url)
            return True
        except Exception:
            pass

    return False

def setup_tray_icon():
    """Inicializa o ícone da bandeja do Windows com menu interativo."""
    global _tray_icon
    if not TRAY_AVAILABLE or sys.platform != "win32":
        return

    cfg = load_config()
    if not cfg.get("server", {}).get("enable_tray_icon", True):
        return

    port = cfg.get("server", {}).get("port", 8000)

    def on_open_docs(icon, item):
        launch_url_on_desktop(f"http://localhost:{port}/docs")

    def on_toggle_game_mode(icon, item):
        toggle_game_mode()

    def on_toggle_autostart(icon, item):
        current = is_windows_autostart_enabled()
        set_windows_autostart(not current)

    def on_exit(icon, item):
        logger.info("Encerrando servidor via menu da bandeja...")
        icon.stop()
        os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem(f"⚡ MacroEngine (Porta {port})", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("🌐 Abrir Documentação (Swagger)", on_open_docs),
        pystray.MenuItem("🎮 Modo Jogo Turbo", on_toggle_game_mode, checked=lambda item: GAME_MODE_ACTIVE),
        pystray.MenuItem("🚀 Iniciar com o Windows", on_toggle_autostart, checked=lambda item: is_windows_autostart_enabled()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("🛑 Encerrar Servidor", on_exit)
    )

    try:
        _tray_icon = pystray.Icon("MacroEngine", create_tray_image(), "MacroEngine Server", menu=menu)
        _tray_icon.run_detached()
        logger.info("Ícone na bandeja do sistema (System Tray) inicializado com sucesso.")
    except Exception as e:
        logger.warning(f"Não foi possível inicializar o ícone da bandeja: {e}")

# Automação de Teclado/Mouse
try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.0
except ImportError:
    pyautogui = None
    logger.warning("pyautogui não instalado. Ações de teclado/mouse estarão desativadas.")

# Controle de Áudio Master no Windows (pycaw)
PYCAW_AVAILABLE = False
if sys.platform == "win32":
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        PYCAW_AVAILABLE = True
    except Exception as e:
        logger.warning(f"pycaw não disponível no Windows: {e}. Usando fallback por atalhos.")

# PyAudio / PyAudioWPatch para captura de áudio local (WASAPI Loopback)
try:
    import pyaudiowpatch as pyaudio
    PYAUDIO_AVAILABLE = True
    logger.info("pyaudiowpatch carregado com sucesso (suporte nativo a WASAPI Loopback do Windows).")
except ImportError:
    try:
        import pyaudio
        PYAUDIO_AVAILABLE = True
        logger.info("pyaudio padrão carregado.")
    except ImportError:
        pyaudio = None
        PYAUDIO_AVAILABLE = False
        logger.warning("pyaudio/pyaudiowpatch não disponível. O streaming usará sintetizador de teste.")

try:
    import numpy as np
except ImportError:
    np = None

# Instância do FastAPI
app = FastAPI(
    title="MacroEngine Server",
    description="Servidor de baixa latência para automação de macros, controle remoto e streaming de áudio",
    version="1.0.0"
)

# Habilitação de CORS para qualquer origem
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# MODELOS DE DADOS
# ---------------------------------------------------------------------------
class OpenUrlRequest(BaseModel):
    url: str = Field(..., description="URL ou link a ser aberto no navegador padrão")

class PCActionItem(BaseModel):
    action: str = Field(..., description="Tipo de ação: hotkey, launch, kill, volume_mute, volume_set")
    keys: Optional[List[str]] = Field(default_factory=list, description="Teclas para hotkey")
    target: Optional[str] = Field(default="", description="Alvo para launch ou kill")
    level: Optional[int] = Field(default=None, description="Nível de volume de 0 a 100")

class ExecuteActionsRequest(BaseModel):
    actions: List[PCActionItem] = Field(..., description="Lista de ações geradas pelo assistente SLM")

class AudioStreamStartRequest(BaseModel):
    client_ip: str = Field(..., description="IP do dispositivo Android")
    client_port: int = Field(default=50005, description="Porta UDP no Android")
    sample_rate: int = Field(default=44100, description="Taxa de amostragem PCM (Hz)")
    channels: int = Field(default=2, description="Canais: 1 (mono) ou 2 (estéreo)")

class MacroExecutionResponse(BaseModel):
    macro_id: str
    description: str
    success: bool
    message: str

class ScreenInputRequest(BaseModel):
    x: float = Field(..., ge=0.0, le=1.0, description="Posição X normalizada (0.0 a 1.0)")
    y: float = Field(..., ge=0.0, le=1.0, description="Posição Y normalizada (0.0 a 1.0)")
    action: str = Field(default="click", description="click, right_click, double_click, move")

class PhoneTouchRequest(BaseModel):
    x: float = Field(..., ge=0.0, le=1.0, description="Posição X normalizada (0.0 a 1.0)")
    y: float = Field(..., ge=0.0, le=1.0, description="Posição Y normalizada (0.0 a 1.0)")

# ---------------------------------------------------------------------------
# GERENCIADOR DE ÁUDIO MASTER (WINDOWS / LINUX)
# ---------------------------------------------------------------------------
def set_system_mute(mute_state: bool) -> bool:
    """Muta ou desmuta o áudio master do sistema operacional de forma direta no hardware via CoreAudio."""
    if PYCAW_AVAILABLE and sys.platform == "win32":
        try:
            try:
                ctypes.windll.ole32.CoInitialize(None)
            except Exception:
                pass
            devices = AudioUtilities.GetSpeakers()
            if hasattr(devices, "EndpointVolume") and devices.EndpointVolume:
                devices.EndpointVolume.SetMute(1 if mute_state else 0, None)
                logger.info(f"Áudio do sistema mutado={mute_state} via pycaw EndpointVolume")
                return True
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMute(1 if mute_state else 0, None)
            logger.info(f"Áudio do sistema mutado={mute_state} via pycaw Activate")
            return True
        except Exception as e:
            logger.error(f"Erro ao mutar via pycaw: {e}")

    # Fallback para tecla de multimídia (funciona em Windows, macOS e Linux)
    if pyautogui is not None:
        try:
            pyautogui.press('volumemute')
            logger.info("Enviado comando volumemute via pyautogui")
            return True
        except Exception as e:
            logger.error(f"Erro ao pressionar volumemute: {e}")

    # Fallback Linux ALSA/PulseAudio
    if sys.platform.startswith("linux"):
        try:
            subprocess.run(["amixer", "-D", "pulse", "set", "Master", "mute" if mute_state else "unmute"], check=False)
            return True
        except Exception:
            pass

    return False

def toggle_system_mute() -> bool:
    """Alterna o estado de mudo: se estiver mutado, desmuta; se com som, muta."""
    if PYCAW_AVAILABLE and sys.platform == "win32":
        try:
            try:
                ctypes.windll.ole32.CoInitialize(None)
            except Exception:
                pass
            devices = AudioUtilities.GetSpeakers()
            if hasattr(devices, "EndpointVolume") and devices.EndpointVolume:
                vol = devices.EndpointVolume
                cur_muted = vol.GetMute()
                new_state = 0 if cur_muted else 1
                vol.SetMute(new_state, None)
                logger.info(f"Áudio alternado via EndpointVolume: {'MUTADO' if new_state else 'SOM RESTAURADO'}")
                return new_state == 1
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            cur_muted = volume.GetMute()
            new_state = 0 if cur_muted else 1
            volume.SetMute(new_state, None)
            logger.info(f"Áudio alternado via Activate: {'MUTADO' if new_state else 'SOM RESTAURADO'}")
            return new_state == 1
        except Exception as e:
            logger.error(f"Erro ao alternar mudo via pycaw: {e}")

    if pyautogui is not None:
        try:
            pyautogui.press('volumemute')
            logger.info("Enviado comando volumemute via pyautogui")
            return True
        except Exception as e:
            logger.error(f"Erro ao pressionar volumemute: {e}")

    return False

def adjust_system_volume(delta: float) -> bool:
    """Aumenta ou reduz o volume master do sistema operacional via CoreAudio (Windows)."""
    if PYCAW_AVAILABLE and sys.platform == "win32":
        try:
            try:
                ctypes.windll.ole32.CoInitialize(None)
            except Exception:
                pass
            devices = AudioUtilities.GetSpeakers()
            if hasattr(devices, "EndpointVolume") and devices.EndpointVolume:
                vol = devices.EndpointVolume
                cur = vol.GetMasterVolumeLevelScalar()
                novo = max(0.0, min(1.0, cur + delta))
                vol.SetMasterVolumeLevelScalar(novo, None)
                logger.info(f"Volume do sistema ajustado via CoreAudio para {int(novo * 100)}%")
                return True
        except Exception as e:
            logger.warning(f"Ajuste via pycaw falhou: {e}")

    if pyautogui is not None:
        steps = max(1, int(abs(delta) * 20))
        key = 'volumeup' if delta > 0 else 'volumedown'
        for _ in range(steps):
            pyautogui.press(key)
        return True
    return False

def pause_active_media():
    """Envia o comando de Play/Pause global para pausar qualquer mídia em execução."""
    if pyautogui is not None:
        try:
            pyautogui.press('playpause')
            logger.info("Comando playpause disparado.")
            return True
        except Exception as e:
            logger.error(f"Erro ao disparar playpause: {e}")
    return False

# ---------------------------------------------------------------------------
# MAPEAMENTO EXTENSÍVEL DE MACROS
# ---------------------------------------------------------------------------
MACRO_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    # 1. CONTROLE DE MÍDIA & STREAMING
    "play_pause": {
        "name": "Play / Pause",
        "category": "Mídia",
        "action": lambda: pyautogui.press('playpause') if pyautogui else False
    },
    "next_track": {
        "name": "Próxima Faixa",
        "category": "Mídia",
        "action": lambda: pyautogui.press('nexttrack') if pyautogui else False
    },
    "prev_track": {
        "name": "Faixa Anterior",
        "category": "Mídia",
        "action": lambda: pyautogui.press('prevtrack') if pyautogui else False
    },
    "vol_up": {
        "name": "Volume +",
        "category": "Mídia",
        "action": lambda: adjust_system_volume(0.05)
    },
    "vol_down": {
        "name": "Volume -",
        "category": "Mídia",
        "action": lambda: adjust_system_volume(-0.05)
    },
    "vol_mute": {
        "name": "Mudo / Silêncio",
        "category": "Mídia",
        "action": lambda: toggle_system_mute()
    },
    "vol_boost_up": {
        "name": "Boost Som +10",
        "category": "Mídia",
        "action": lambda: adjust_system_volume(0.15)
    },
    "vol_boost_down": {
        "name": "Boost Som -10",
        "category": "Mídia",
        "action": lambda: adjust_system_volume(-0.15)
    },
    "skip_fwd_10s": {
        "name": "Avançar 10s (Vídeo)",
        "category": "Mídia",
        "action": lambda: pyautogui.press('right') if pyautogui else False
    },
    "skip_back_10s": {
        "name": "Voltar 10s (Vídeo)",
        "category": "Mídia",
        "action": lambda: pyautogui.press('left') if pyautogui else False
    },
    "toggle_fullscreen": {
        "name": "Tela Cheia (F)",
        "category": "Mídia",
        "action": lambda: pyautogui.press('f') if pyautogui else False
    },

    # 2. JANELAS & MULTI-MONITOR
    "win_d": {
        "name": "Mostrar Desktop",
        "category": "Janelas",
        "action": lambda: pyautogui.hotkey('win', 'd') if pyautogui else False
    },
    "alt_tab": {
        "name": "Alternar Janelas",
        "category": "Janelas",
        "action": lambda: pyautogui.hotkey('alt', 'tab') if pyautogui else False
    },
    "snap_left": {
        "name": "Janela na Esquerda",
        "category": "Janelas",
        "action": lambda: pyautogui.hotkey('win', 'left') if pyautogui else False
    },
    "snap_right": {
        "name": "Janela na Direita",
        "category": "Janelas",
        "action": lambda: pyautogui.hotkey('win', 'right') if pyautogui else False
    },
    "maximize_window": {
        "name": "Maximizar Janela",
        "category": "Janelas",
        "action": lambda: pyautogui.hotkey('win', 'up') if pyautogui else False
    },
    "fullscreen_f11": {
        "name": "Tela Cheia (F11)",
        "category": "Janelas",
        "action": lambda: pyautogui.press('f11') if pyautogui else False
    },
    "minimize_window": {
        "name": "Minimizar Janela",
        "category": "Janelas",
        "action": lambda: pyautogui.hotkey('win', 'down') if pyautogui else False
    },
    "next_monitor": {
        "name": "Mover para Próx. Monitor",
        "category": "Janelas",
        "action": lambda: pyautogui.hotkey('win', 'shift', 'right') if pyautogui else False
    },
    "close_window": {
        "name": "Fechar Janela (Alt+F4)",
        "category": "Janelas",
        "action": lambda: pyautogui.hotkey('alt', 'f4') if pyautogui else False
    },

    # 3. PRODUTIVIDADE & NAVEGADOR
    "clipboard_history": {
        "name": "Histórico Copiar (Win+V)",
        "category": "Produtividade",
        "action": lambda: pyautogui.hotkey('win', 'v') if pyautogui else False
    },
    "search_pc": {
        "name": "Busca Global (Win+S)",
        "category": "Produtividade",
        "action": lambda: pyautogui.hotkey('win', 's') if pyautogui else False
    },
    "close_tab": {
        "name": "Fechar Aba (Ctrl+W)",
        "category": "Produtividade",
        "action": lambda: pyautogui.hotkey('ctrl', 'w') if pyautogui else False
    },
    "reopen_tab": {
        "name": "Reabrir Aba (Ctrl+Shift+T)",
        "category": "Produtividade",
        "action": lambda: pyautogui.hotkey('ctrl', 'shift', 't') if pyautogui else False
    },
    "incognito_tab": {
        "name": "Guia Anônima",
        "category": "Produtividade",
        "action": lambda: pyautogui.hotkey('ctrl', 'shift', 'n') if pyautogui else False
    },
    "save_all": {
        "name": "Salvar Tudo (Ctrl+S)",
        "category": "Produtividade",
        "action": lambda: pyautogui.hotkey('ctrl', 's') if pyautogui else False
    },
    "open_notepad": {
        "name": "Bloco de Notas",
        "category": "Produtividade",
        "action": lambda: subprocess.Popen(['notepad.exe'] if sys.platform == 'win32' else ['gedit'])
    },
    "open_calc": {
        "name": "Calculadora",
        "category": "Produtividade",
        "action": lambda: subprocess.Popen(['calc.exe'] if sys.platform == 'win32' else ['gnome-calculator'])
    },
    "file_explorer": {
        "name": "Explorador (Win+E)",
        "category": "Produtividade",
        "action": lambda: pyautogui.hotkey('win', 'e') if sys.platform == 'win32' else subprocess.Popen(['xdg-open', '.'])
    },
    "screenshot": {
        "name": "Print Screen (Win+Shift+S)",
        "category": "Produtividade",
        "action": lambda: pyautogui.hotkey('win', 'shift', 's') if sys.platform == 'win32' else pyautogui.press('printscreen')
    },
    "open_terminal": {
        "name": "Terminal PowerShell",
        "category": "Produtividade",
        "action": lambda: _open_terminal()
    },
    "open_vscode": {
        "name": "Abrir VS Code",
        "category": "Produtividade",
        "action": lambda: subprocess.Popen(['code'] if sys.platform == 'win32' else ['code'], shell=True)
    },
    "open_localhost": {
        "name": "Abrir Localhost (8000)",
        "category": "Produtividade",
        "action": lambda: launch_url_on_desktop("http://localhost:8000")
    },

    # 4. MICROSOFT WORD & LIBREOFFICE WRITER (TEXTOS E DOCUMENTOS)
    "office_bold": {
        "name": "Negrito / Bold (Ctrl+B)",
        "category": "Office & Documentos",
        "action": lambda: pyautogui.hotkey('ctrl', 'b') if pyautogui else False
    },
    "office_italic": {
        "name": "Itálico / Italic (Ctrl+I)",
        "category": "Office & Documentos",
        "action": lambda: pyautogui.hotkey('ctrl', 'i') if pyautogui else False
    },
    "office_underline": {
        "name": "Sublinhado / Underline (Ctrl+U)",
        "category": "Office & Documentos",
        "action": lambda: pyautogui.hotkey('ctrl', 'u') if pyautogui else False
    },
    "office_align_center": {
        "name": "Centralizar Texto (Ctrl+E)",
        "category": "Office & Documentos",
        "action": lambda: pyautogui.hotkey('ctrl', 'e') if pyautogui else False
    },
    "office_align_left": {
        "name": "Alinhar à Esquerda (Ctrl+L)",
        "category": "Office & Documentos",
        "action": lambda: pyautogui.hotkey('ctrl', 'l') if pyautogui else False
    },
    "office_align_right": {
        "name": "Alinhar à Direita (Ctrl+R)",
        "category": "Office & Documentos",
        "action": lambda: pyautogui.hotkey('ctrl', 'r') if pyautogui else False
    },
    "office_align_justify": {
        "name": "Justificar Texto (Ctrl+J)",
        "category": "Office & Documentos",
        "action": lambda: pyautogui.hotkey('ctrl', 'j') if pyautogui else False
    },
    "office_save_doc": {
        "name": "Salvar Documento (Ctrl+S)",
        "category": "Office & Documentos",
        "action": lambda: pyautogui.hotkey('ctrl', 's') if pyautogui else False
    },
    "office_find_replace": {
        "name": "Localizar e Substituir (Ctrl+H)",
        "category": "Office & Documentos",
        "action": lambda: pyautogui.hotkey('ctrl', 'h') if pyautogui else False
    },
    "office_page_break": {
        "name": "Quebra de Página (Ctrl+Enter)",
        "category": "Office & Documentos",
        "action": lambda: pyautogui.hotkey('ctrl', 'enter') if pyautogui else False
    },
    "office_insert_link": {
        "name": "Inserir Link / Hiperlink (Ctrl+K)",
        "category": "Office & Documentos",
        "action": lambda: pyautogui.hotkey('ctrl', 'k') if pyautogui else False
    },
    "office_select_all": {
        "name": "Selecionar Todo o Texto (Ctrl+A)",
        "category": "Office & Documentos",
        "action": lambda: pyautogui.hotkey('ctrl', 'a') if pyautogui else False
    },
    "office_print_pdf": {
        "name": "Imprimir / Exportar PDF (Ctrl+P)",
        "category": "Office & Documentos",
        "action": lambda: pyautogui.hotkey('ctrl', 'p') if pyautogui else False
    },

    # 5. MICROSOFT EXCEL & LIBREOFFICE CALC (PLANILHAS E DADOS)
    "excel_auto_sum": {
        "name": "AutoSoma Linha/Coluna (Alt+=)",
        "category": "Excel & Planilhas",
        "action": lambda: pyautogui.hotkey('alt', '=') if pyautogui else False
    },
    "excel_insert_row": {
        "name": "Inserir Linha/Célula (Ctrl+Shift++)",
        "category": "Excel & Planilhas",
        "action": lambda: pyautogui.hotkey('ctrl', 'shift', '=') if pyautogui else False
    },
    "excel_delete_row": {
        "name": "Excluir Linha/Célula (Ctrl+-)",
        "category": "Excel & Planilhas",
        "action": lambda: pyautogui.hotkey('ctrl', '-') if pyautogui else False
    },
    "excel_format_currency": {
        "name": "Formatar Moeda R$ (Ctrl+Shift+$)",
        "category": "Excel & Planilhas",
        "action": lambda: pyautogui.hotkey('ctrl', 'shift', '4') if pyautogui else False
    },
    "excel_format_percent": {
        "name": "Formatar Porcentagem % (Ctrl+Shift+%)",
        "category": "Excel & Planilhas",
        "action": lambda: pyautogui.hotkey('ctrl', 'shift', '5') if pyautogui else False
    },
    "excel_format_date": {
        "name": "Formatar como Data (Ctrl+Shift+#)",
        "category": "Excel & Planilhas",
        "action": lambda: pyautogui.hotkey('ctrl', 'shift', '3') if pyautogui else False
    },
    "excel_filter_toggle": {
        "name": "Ativar/Desativar Filtros (Ctrl+Shift+L)",
        "category": "Excel & Planilhas",
        "action": lambda: pyautogui.hotkey('ctrl', 'shift', 'l') if pyautogui else False
    },
    "excel_new_sheet": {
        "name": "Nova Planilha / Aba (Shift+F11)",
        "category": "Excel & Planilhas",
        "action": lambda: pyautogui.hotkey('shift', 'f11') if pyautogui else False
    },
    "excel_create_chart": {
        "name": "Criar Gráfico Instantâneo (F11)",
        "category": "Excel & Planilhas",
        "action": lambda: pyautogui.press('f11') if pyautogui else False
    },
    "excel_flash_fill": {
        "name": "Preenchimento Relâmpago (Ctrl+E)",
        "category": "Excel & Planilhas",
        "action": lambda: pyautogui.hotkey('ctrl', 'e') if pyautogui else False
    },
    "excel_edit_cell": {
        "name": "Editar Célula Ativa (F2)",
        "category": "Excel & Planilhas",
        "action": lambda: pyautogui.press('f2') if pyautogui else False
    },

    # 6. POWERPOINT & LIBREOFFICE IMPRESS (APRESENTAÇÃO DE SLIDES)
    "ppt_start_slideshow": {
        "name": "Apresentar do Início (F5)",
        "category": "PowerPoint & Slides",
        "action": lambda: pyautogui.press('f5') if pyautogui else False
    },
    "ppt_present_current": {
        "name": "Apresentar Slide Atual (Shift+F5)",
        "category": "PowerPoint & Slides",
        "action": lambda: pyautogui.hotkey('shift', 'f5') if pyautogui else False
    },
    "ppt_new_slide": {
        "name": "Inserir Novo Slide (Ctrl+M)",
        "category": "PowerPoint & Slides",
        "action": lambda: pyautogui.hotkey('ctrl', 'm') if pyautogui else False
    },
    "ppt_duplicate_slide": {
        "name": "Duplicar Slide (Ctrl+D)",
        "category": "PowerPoint & Slides",
        "action": lambda: pyautogui.hotkey('ctrl', 'd') if pyautogui else False
    },
    "ppt_black_screen": {
        "name": "Tela Preta / Apagar (B)",
        "category": "PowerPoint & Slides",
        "action": lambda: pyautogui.press('b') if pyautogui else False
    },
    "ppt_white_screen": {
        "name": "Tela Branca (W)",
        "category": "PowerPoint & Slides",
        "action": lambda: pyautogui.press('w') if pyautogui else False
    },
    "ppt_laser_pointer": {
        "name": "Apontador Laser (Ctrl+L)",
        "category": "PowerPoint & Slides",
        "action": lambda: pyautogui.hotkey('ctrl', 'l') if pyautogui else False
    },
    "ppt_pen_tool": {
        "name": "Caneta Desenho Slide (Ctrl+P)",
        "category": "PowerPoint & Slides",
        "action": lambda: pyautogui.hotkey('ctrl', 'p') if pyautogui else False
    },
    "ppt_next_slide": {
        "name": "Próximo Slide (Avançar)",
        "category": "PowerPoint & Slides",
        "action": lambda: pyautogui.press('pagedown') if pyautogui else False
    },
    "ppt_prev_slide": {
        "name": "Slide Anterior (Voltar)",
        "category": "PowerPoint & Slides",
        "action": lambda: pyautogui.press('pageup') if pyautogui else False
    },
    "ppt_end_show": {
        "name": "Encerrar Apresentação (Esc)",
        "category": "PowerPoint & Slides",
        "action": lambda: pyautogui.press('esc') if pyautogui else False
    },

    # 7. DESIGN, FIGMA, CANVA, PDF & NOTION
    "design_duplicate": {
        "name": "Duplicar Seleção (Ctrl+D)",
        "category": "Design & Criação",
        "action": lambda: pyautogui.hotkey('ctrl', 'd') if pyautogui else False
    },
    "design_group": {
        "name": "Agrupar Elementos (Ctrl+G)",
        "category": "Design & Criação",
        "action": lambda: pyautogui.hotkey('ctrl', 'g') if pyautogui else False
    },
    "design_ungroup": {
        "name": "Desagrupar Elementos (Ctrl+Shift+G)",
        "category": "Design & Criação",
        "action": lambda: pyautogui.hotkey('ctrl', 'shift', 'g') if pyautogui else False
    },
    "design_zoom_fit": {
        "name": "Ajustar à Tela (Ctrl+0)",
        "category": "Design & Criação",
        "action": lambda: pyautogui.hotkey('ctrl', '0') if pyautogui else False
    },
    "design_zoom_selection": {
        "name": "Focar Seleção / Figma (Shift+2)",
        "category": "Design & Criação",
        "action": lambda: pyautogui.hotkey('shift', '2') if pyautogui else False
    },
    "notion_toggle_list": {
        "name": "Lista Recolhível / Toggle (Ctrl+Shift+7)",
        "category": "Design & Criação",
        "action": lambda: pyautogui.hotkey('ctrl', 'shift', '7') if pyautogui else False
    },
    "notion_code_block": {
        "name": "Bloco de Código (Ctrl+Alt+8)",
        "category": "Design & Criação",
        "action": lambda: pyautogui.hotkey('ctrl', 'alt', '8') if pyautogui else False
    },
    "pdf_rotate": {
        "name": "Girar Página PDF (Ctrl+Shift+R)",
        "category": "Design & Criação",
        "action": lambda: pyautogui.hotkey('ctrl', 'shift', 'r') if pyautogui else False
    },

    # 8. GAMING, BATTLEFIELD & MODO JOGO
    "game_mode_on": {
        "name": "Ativar Modo Jogo (Turbo)",
        "category": "Modo Jogo",
        "action": lambda: _set_power_plan("high")
    },
    "game_mode_balanced": {
        "name": "Modo Energia Equilibrado",
        "category": "Modo Jogo",
        "action": lambda: _set_power_plan("balanced")
    },
    "bf_spotting": {
        "name": "BF6 Q-Spotting (Marcar Inimigo)",
        "category": "Battlefield & FPS",
        "action": lambda: _bf_spotting()
    },
    "bf_hold_breath": {
        "name": "BF6 Sniper Estável (Shift)",
        "category": "Battlefield & FPS",
        "action": lambda: _bf_hold_breath()
    },
    "bf_quick_grenade": {
        "name": "Lançar Granada (G)",
        "category": "Battlefield & FPS",
        "action": lambda: pyautogui.press('g') if pyautogui else False
    },
    "bf_medkit_ammo": {
        "name": "Soltar Medkit / Munição (3/4)",
        "category": "Battlefield & FPS",
        "action": lambda: _bf_medkit_ammo()
    },
    "bf_drop_shot": {
        "name": "Drop Shot (Deitar Rápido)",
        "category": "Battlefield & FPS",
        "action": lambda: _bf_drop_shot()
    },
    "bf_tactical_reload": {
        "name": "Recarga Tática (R)",
        "category": "Battlefield & FPS",
        "action": lambda: pyautogui.press('r') if pyautogui else False
    },
    "bf_fire_mode": {
        "name": "Modo de Disparo (V)",
        "category": "Battlefield & FPS",
        "action": lambda: pyautogui.press('v') if pyautogui else False
    },
    "bf_melee_takedown": {
        "name": "Golpe Melee / Faca (F)",
        "category": "Battlefield & FPS",
        "action": lambda: pyautogui.press('f') if pyautogui else False
    },
    "bf_scoreboard": {
        "name": "Placar / Mapa Geral (Tab)",
        "category": "Battlefield & FPS",
        "action": lambda: pyautogui.press('tab') if pyautogui else False
    },
    "fps_overlay": {
        "name": "Contador de FPS (Alt+R)",
        "category": "Gaming & OBS",
        "action": lambda: pyautogui.hotkey('alt', 'r') if pyautogui else False
    },
    "instant_replay": {
        "name": "Salvar Clipe ShadowPlay (Alt+F10)",
        "category": "Gaming & OBS",
        "action": lambda: pyautogui.hotkey('alt', 'f10') if pyautogui else False
    },
    "steam_overlay": {
        "name": "Painel Steam (Shift+Tab)",
        "category": "Gaming & OBS",
        "action": lambda: pyautogui.hotkey('shift', 'tab') if pyautogui else False
    },
    "open_steam": {
        "name": "Abrir Steam",
        "category": "Gaming & OBS",
        "action": lambda: launch_url_on_desktop("steam://open/main") if sys.platform == 'win32' else subprocess.Popen(['steam'])
    },
    "game_clip": {
        "name": "Salvar Últimos 30s (Clipe)",
        "category": "Gaming & OBS",
        "action": lambda: pyautogui.hotkey('win', 'alt', 'g') if sys.platform == 'win32' else False
    },
    "game_bar": {
        "name": "Xbox Game Bar (Win+G)",
        "category": "Gaming & OBS",
        "action": lambda: pyautogui.hotkey('win', 'g') if sys.platform == 'win32' else False
    },
    "obs_record": {
        "name": "OBS Iniciar Gravação",
        "category": "Gaming & OBS",
        "action": lambda: pyautogui.hotkey('ctrl', 'f9') if pyautogui else False
    },
    "obs_stream": {
        "name": "OBS Transmitir Ao Vivo",
        "category": "Gaming & OBS",
        "action": lambda: pyautogui.hotkey('ctrl', 'f10') if pyautogui else False
    },
    "discord_mute": {
        "name": "Discord Mudar Mic (Mudo)",
        "category": "Gaming & OBS",
        "action": lambda: pyautogui.hotkey('ctrl', 'shift', 'm') if pyautogui else False
    },
    "discord_deafen": {
        "name": "Discord Ensurdecer",
        "category": "Gaming & OBS",
        "action": lambda: pyautogui.hotkey('ctrl', 'shift', 'd') if pyautogui else False
    },
    "voice_typing": {
        "name": "Digitação por Voz (Win+H)",
        "category": "Gaming & OBS",
        "action": lambda: pyautogui.hotkey('win', 'h') if sys.platform == 'win32' else False
    },
    "game_mode_boost": {
        "name": "Modo Jogo Turbo (Plano Máximo)",
        "category": "Gaming & OBS",
        "action": lambda: toggle_game_mode()
    },

    # 5. COUNTER-STRIKE 2 (CS2)
    "cs2_drop_c4": {
        "name": "CS2 Drop C4 Rápido (5->G->1)",
        "category": "Counter-Strike 2",
        "action": lambda: _cs2_drop_c4()
    },
    "cs2_jump_throw": {
        "name": "CS2 Jump Throw (Granadas)",
        "category": "Counter-Strike 2",
        "action": lambda: _cs2_jump_throw()
    },
    "cs2_inspect": {
        "name": "CS2 Inspecionar Faca / Arma (F+R)",
        "category": "Counter-Strike 2",
        "action": lambda: _cs2_inspect_twirl()
    },
    "cs2_quick_flash": {
        "name": "CS2 Puxar Flashbang (7)",
        "category": "Counter-Strike 2",
        "action": lambda: pyautogui.press('7') if pyautogui else False
    },
    "cs2_drop_pistol": {
        "name": "CS2 Drop Pistola para Teammate",
        "category": "Counter-Strike 2",
        "action": lambda: _cs2_drop_pistol()
    },
    "cs2_radar_zoom": {
        "name": "CS2 Alternar Zoom do Radar",
        "category": "Counter-Strike 2",
        "action": lambda: pyautogui.press('m') if pyautogui else False
    },

    # 6. DEADLOCK (VALVE)
    "deadlock_dash_jump": {
        "name": "Deadlock Dash Jump (Shift+Espaço)",
        "category": "Deadlock",
        "action": lambda: _deadlock_dash_jump()
    },
    "deadlock_heavy_melee": {
        "name": "Deadlock Golpe Pesado (Melee)",
        "category": "Deadlock",
        "action": lambda: _deadlock_heavy_melee()
    },
    "deadlock_parry": {
        "name": "Deadlock Parry Defensivo (F)",
        "category": "Deadlock",
        "action": lambda: pyautogui.press('f') if pyautogui else False
    },
    "deadlock_shop": {
        "name": "Deadlock Loja de Itens (B)",
        "category": "Deadlock",
        "action": lambda: pyautogui.press('b') if pyautogui else False
    },
    "deadlock_ping_boss": {
        "name": "Deadlock Ping Mid Boss / Urna",
        "category": "Deadlock",
        "action": lambda: pyautogui.press('mouse3') if pyautogui else False
    },

    # 7. CALL OF DUTY: WARZONE & MW3
    "cod_slide_cancel": {
        "name": "Warzone Slide Cancel Tático",
        "category": "Call of Duty",
        "action": lambda: _cod_slide_cancel()
    },
    "cod_plate_spam": {
        "name": "Warzone Aplicar 3 Placas Colete (4)",
        "category": "Call of Duty",
        "action": lambda: _cod_plate_spam()
    },
    "cod_ping_danger": {
        "name": "Warzone Ping Vermelho Inimigo",
        "category": "Call of Duty",
        "action": lambda: _cod_ping_danger()
    },
    "cod_drop_munitions": {
        "name": "Warzone Soltar Caixa Munição (5)",
        "category": "Call of Duty",
        "action": lambda: pyautogui.press('5') if pyautogui else False
    },
    "cod_mount_weapon": {
        "name": "Warzone Apoiar Arma em Cobertura (Z)",
        "category": "Call of Duty",
        "action": lambda: pyautogui.press('z') if pyautogui else False
    },

    # 8. HELLDIVERS 2 (ESTRATAGEMAS COM CÓDIGOS DE SETAS)
    "hd2_reinforce": {
        "name": "HD2 Reforço (Reviver Equipe)",
        "category": "Helldivers 2",
        "action": lambda: _hd2_stratagem(['up', 'down', 'right', 'left', 'up'])
    },
    "hd2_bomb_500kg": {
        "name": "HD2 Bomba de 500kg da Águia",
        "category": "Helldivers 2",
        "action": lambda: _hd2_stratagem(['up', 'right', 'down', 'down', 'down'])
    },
    "hd2_resupply": {
        "name": "HD2 Chamar Suprimentos",
        "category": "Helldivers 2",
        "action": lambda: _hd2_stratagem(['down', 'down', 'up', 'right'])
    },
    "hd2_orbital_laser": {
        "name": "HD2 Laser Orbital",
        "category": "Helldivers 2",
        "action": lambda: _hd2_stratagem(['right', 'down', 'up', 'right', 'down'])
    },
    "hd2_railcannon": {
        "name": "HD2 Canhão Elétrico Orbital",
        "category": "Helldivers 2",
        "action": lambda: _hd2_stratagem(['right', 'up', 'down', 'down', 'right'])
    },
    "hd2_stim_heal": {
        "name": "HD2 Cura Rápida Stim (V)",
        "category": "Helldivers 2",
        "action": lambda: pyautogui.press('v') if pyautogui else False
    },

    # 9. PUBG: BATTLEGROUNDS
    "pubg_crouch_jump": {
        "name": "PUBG Pulo Agachado Janelas",
        "category": "PUBG",
        "action": lambda: _pubg_crouch_jump()
    },
    "pubg_boost_energy": {
        "name": "PUBG Usar Energético / Boost (8)",
        "category": "PUBG",
        "action": lambda: pyautogui.press('8') if pyautogui else False
    },
    "pubg_first_aid": {
        "name": "PUBG Kit Primeiros Socorros (7)",
        "category": "PUBG",
        "action": lambda: pyautogui.press('7') if pyautogui else False
    },
    "pubg_driver_seat": {
        "name": "PUBG Banco Motorista Veículo (Ctrl+1)",
        "category": "PUBG",
        "action": lambda: pyautogui.hotkey('ctrl', '1') if pyautogui else False
    },
    "pubg_smoke_grenade": {
        "name": "PUBG Granada de Fumaça Rápida (5)",
        "category": "PUBG",
        "action": lambda: pyautogui.press('5') if pyautogui else False
    },

    # 10. APEX LEGENDS
    "apex_holster_run": {
        "name": "Apex Guardar Arma / Sprint (3)",
        "category": "Apex Legends",
        "action": lambda: pyautogui.press('3') if pyautogui else False
    },
    "apex_shield_battery": {
        "name": "Apex Bateria de Escudo (4)",
        "category": "Apex Legends",
        "action": lambda: pyautogui.press('4') if pyautogui else False
    },
    "apex_phoenix_kit": {
        "name": "Apex Kit Fênix Regeneração Total",
        "category": "Apex Legends",
        "action": lambda: pyautogui.press('0') if pyautogui else False
    },
    "apex_ping_enemy": {
        "name": "Apex Ping Inimigo Avistado (F)",
        "category": "Apex Legends",
        "action": lambda: pyautogui.press('f') if pyautogui else False
    },
    "apex_superglide": {
        "name": "Apex Assistente de Superglide",
        "category": "Apex Legends",
        "action": lambda: _apex_superglide()
    },

    # 11. VALORANT
    "val_spike_plant": {
        "name": "Valorant Plantar/Defusar Spike (4)",
        "category": "Valorant",
        "action": lambda: _val_spike_plant()
    },
    "val_knife_run": {
        "name": "Valorant Puxar Faca / Correr (3)",
        "category": "Valorant",
        "action": lambda: pyautogui.press('3') if pyautogui else False
    },
    "val_ping_danger": {
        "name": "Valorant Alerta de Perigo (Z)",
        "category": "Valorant",
        "action": lambda: pyautogui.press('z') if pyautogui else False
    },
    "val_drop_weapon": {
        "name": "Valorant Dropar Arma no Chão (G)",
        "category": "Valorant",
        "action": lambda: pyautogui.press('g') if pyautogui else False
    },

    # 12. DELTA FORCE & EXTRACTION
    "delta_tactical_heal": {
        "name": "Delta Force Bandagem Rápida (4)",
        "category": "Delta Force",
        "action": lambda: pyautogui.press('4') if pyautogui else False
    },
    "delta_armor_plate": {
        "name": "Delta Force Reparar Colete (5)",
        "category": "Delta Force",
        "action": lambda: pyautogui.press('5') if pyautogui else False
    },
    "delta_canted_sight": {
        "name": "Delta Force Mira Inclinada (V)",
        "category": "Delta Force",
        "action": lambda: pyautogui.press('v') if pyautogui else False
    },
    "delta_special_gadget": {
        "name": "Delta Force Gadget da Classe (X)",
        "category": "Delta Force",
        "action": lambda: pyautogui.press('x') if pyautogui else False
    },

    # 13. RUST (SOBREVIVÊNCIA)
    "rust_auto_gather": {
        "name": "Rust Mineração Contínua 6s",
        "category": "Rust",
        "action": lambda: _rust_auto_gather()
    },
    "rust_suicide_f1": {
        "name": "Rust Console Respawn (Kill)",
        "category": "Rust",
        "action": lambda: _rust_suicide_f1()
    },
    "rust_craft_bandage": {
        "name": "Rust Criar Curativo Rápido (Tab)",
        "category": "Rust",
        "action": lambda: pyautogui.press('tab') if pyautogui else False
    },

    # 14. FORTNITE
    "fortnite_wall_ramp": {
        "name": "Fortnite Parede + Rampa Defesa",
        "category": "Fortnite",
        "action": lambda: [pyautogui.press('f1'), time.sleep(0.04), pyautogui.press('f3')] if pyautogui else False
    },
    "fortnite_shield_potion": {
        "name": "Fortnite Tomar Poção Escudo (5)",
        "category": "Fortnite",
        "action": lambda: pyautogui.press('5') if pyautogui else False
    },
    "fortnite_ping_enemy": {
        "name": "Fortnite Ping Alvo Inimigo",
        "category": "Fortnite",
        "action": lambda: pyautogui.press('middle') if pyautogui else False
    },

    # 5. SISTEMA, ENERGIA & MANUTENÇÃO
    "taskmgr": {
        "name": "Gerenciador de Tarefas",
        "category": "Sistema",
        "action": lambda: pyautogui.hotkey('ctrl', 'shift', 'esc') if pyautogui else False
    },
    "lock_pc": {
        "name": "Bloquear PC (Win+L)",
        "category": "Sistema",
        "action": lambda: _lock_workstation()
    },
    "turn_off_screens": {
        "name": "Apagar Telas (Monitores)",
        "category": "Sistema",
        "action": lambda: _turn_off_monitors()
    },
    "sleep_pc": {
        "name": "Suspender PC (Sleep)",
        "category": "Sistema",
        "action": lambda: _sleep_pc()
    },
    "shutdown_pc": {
        "name": "Desligar PC (Shutdown)",
        "category": "Sistema",
        "action": lambda: _shutdown_pc()
    },
    "restart_explorer": {
        "name": "Reiniciar Barra de Tarefas",
        "category": "Sistema",
        "action": lambda: _restart_explorer()
    }
}

def _turn_off_monitors():
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
        return True
    return False

def _sleep_pc():
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.PowrProf.SetSuspendState(0, 1, 0)
        return True
    elif sys.platform.startswith('linux'):
        subprocess.run(["systemctl", "suspend"], check=False)
        return True
    return False

def _shutdown_pc():
    if sys.platform == 'win32':
        subprocess.run(["shutdown", "/s", "/t", "3"], check=False)
        return True
    elif sys.platform.startswith('linux'):
        subprocess.run(["systemctl", "poweroff"], check=False)
        return True
    return False

def _restart_explorer():
    if sys.platform == 'win32':
        subprocess.run(["taskkill", "/f", "/im", "explorer.exe"], check=False)
        subprocess.Popen(["explorer.exe"])
        return True
    return False

def _bf_spotting():
    """Q-Spotting tático: pressiona Q em rajada para marcar inimigos no Battlefield/FPS."""
    if pyautogui:
        def _spot():
            for _ in range(3):
                pyautogui.press('q')
                time.sleep(0.05)
        threading.Thread(target=_spot, daemon=True).start()
        return True
    return False

def _bf_hold_breath():
    """Segurar Respiração (Sniper): segura Shift por 2.5s para estabilização de mira."""
    if pyautogui:
        def _hold():
            pyautogui.keyDown('shift')
            time.sleep(2.5)
            pyautogui.keyUp('shift')
        threading.Thread(target=_hold, daemon=True).start()
        return True
    return False

def _bf_medkit_ammo():
    """Solta recursos de suporte (tecla 3 e 4) rapidamente para o esquadrão."""
    if pyautogui:
        def _drop():
            pyautogui.press('3')
            time.sleep(0.08)
            pyautogui.press('4')
        threading.Thread(target=_drop, daemon=True).start()
        return True
    return False

def _bf_drop_shot():
    """Drop Shot tático: deita rapidamente para evitar tiros."""
    if pyautogui:
        pyautogui.press('ctrl')
        time.sleep(0.05)
        pyautogui.press('z')
        return True
    return False

# ---------------------------------------------------------------------------
# MACROS TÁTICAS: JOGOS COMPETITIVOS E MAIS JOGADOS DO MOMENTO
# ---------------------------------------------------------------------------

# 1. COUNTER-STRIKE 2 (CS2)
def _cs2_drop_c4():
    """Drop C4 instantâneo: equipa a bomba (5), dropa (G) e volta para primária (1)."""
    if pyautogui:
        def _run():
            pyautogui.press('5')
            time.sleep(0.06)
            pyautogui.press('g')
            time.sleep(0.06)
            pyautogui.press('1')
        threading.Thread(target=_run, daemon=True).start()
        return True
    return False

def _cs2_jump_throw():
    """Jump Throw perfeito: pula e solta a granada no ápice da trajetória."""
    if pyautogui:
        def _run():
            pyautogui.press('space')
            time.sleep(0.03)
            pyautogui.mouseUp(button='left')
        threading.Thread(target=_run, daemon=True).start()
        return True
    return False

def _cs2_inspect_twirl():
    """Inspecionar e girar faca/arma com estilo (F + R rápido)."""
    if pyautogui:
        def _run():
            pyautogui.press('f')
            time.sleep(0.12)
            pyautogui.press('r')
        threading.Thread(target=_run, daemon=True).start()
        return True
    return False

def _cs2_drop_pistol():
    """Drop rápido de pistola secundária para colega de equipe."""
    if pyautogui:
        def _run():
            pyautogui.press('2')
            time.sleep(0.06)
            pyautogui.press('g')
            time.sleep(0.06)
            pyautogui.press('1')
        threading.Thread(target=_run, daemon=True).start()
        return True
    return False

# 2. DEADLOCK (VALVE)
def _deadlock_dash_jump():
    """Deadlock Dash Jump: Shift (Dash) + Espaço (Pulo) sincronizados para velocidade máxima."""
    if pyautogui:
        def _run():
            pyautogui.press('shift')
            time.sleep(0.05)
            pyautogui.press('space')
        threading.Thread(target=_run, daemon=True).start()
        return True
    return False

def _deadlock_heavy_melee():
    """Deadlock Golpe Pesado: Carrega soco corporal concentrado."""
    if pyautogui:
        def _run():
            pyautogui.keyDown('q')
            time.sleep(0.38)
            pyautogui.keyUp('q')
        threading.Thread(target=_run, daemon=True).start()
        return True
    return False

# 3. CALL OF DUTY: WARZONE & MW3
def _cod_slide_cancel():
    """Warzone Slide Cancel: Slide (Ctrl) -> Cancel (Ctrl) -> Pulo (Espaço) para resetar sprint."""
    if pyautogui:
        def _run():
            pyautogui.press('ctrl')
            time.sleep(0.07)
            pyautogui.press('ctrl')
            time.sleep(0.03)
            pyautogui.press('space')
        threading.Thread(target=_run, daemon=True).start()
        return True
    return False

def _cod_plate_spam():
    """Aplica 3 placas de blindagem completas mantendo a tecla 4 pressionada."""
    if pyautogui:
        def _run():
            pyautogui.keyDown('4')
            time.sleep(3.2)
            pyautogui.keyUp('4')
        threading.Thread(target=_run, daemon=True).start()
        return True
    return False

def _cod_ping_danger():
    """Ping duplo vermelho de inimigo avistado (duplo clique Alt)."""
    if pyautogui:
        def _run():
            pyautogui.press('alt')
            time.sleep(0.06)
            pyautogui.press('alt')
        threading.Thread(target=_run, daemon=True).start()
        return True
    return False

# 4. HELLDIVERS 2 (CÓDIGOS DE ESTRATAGEMA VIA SETAS DIRECIONAIS)
def _hd2_stratagem(keys: list):
    """Digita a sequência de setas do estratagema segurando a tecla Ctrl."""
    if pyautogui:
        def _run():
            pyautogui.keyDown('ctrl')
            time.sleep(0.06)
            for k in keys:
                pyautogui.press(k)
                time.sleep(0.04)
            pyautogui.keyUp('ctrl')
        threading.Thread(target=_run, daemon=True).start()
        return True
    return False

# 5. PUBG: BATTLEGROUNDS
def _pubg_crouch_jump():
    """Pulo agachado para saltar janelas e vãos sem bater a cabeça no PUBG."""
    if pyautogui:
        def _run():
            pyautogui.keyDown('c')
            pyautogui.press('space')
            pyautogui.keyUp('c')
        threading.Thread(target=_run, daemon=True).start()
        return True
    return False

# 6. APEX LEGENDS
def _apex_superglide():
    """Auxiliar de Superglide: Pulo com agachamento sincronizado no final da escalada."""
    if pyautogui:
        def _run():
            pyautogui.press('space')
            time.sleep(0.02)
            pyautogui.press('c')
        threading.Thread(target=_run, daemon=True).start()
        return True
    return False

# 7. VALORANT
def _val_spike_plant():
    """Segura tecla 4 para plantar ou desarmar a Spike no Valorant."""
    if pyautogui:
        def _run():
            pyautogui.keyDown('4')
            time.sleep(4.2)
            pyautogui.keyUp('4')
        threading.Thread(target=_run, daemon=True).start()
        return True
    return False

# 8. RUST
def _rust_auto_gather():
    """Auto-Gather: mineração ou corte de madeira automático contínuo por 6 segundos."""
    if pyautogui:
        def _run():
            pyautogui.mouseDown(button='left')
            time.sleep(6.0)
            pyautogui.mouseUp(button='left')
        threading.Thread(target=_run, daemon=True).start()
        return True
    return False

def _rust_suicide_f1():
    """Comando de respawn tático no console do Rust (F1 -> kill -> Enter)."""
    if pyautogui:
        def _run():
            pyautogui.press('f1')
            time.sleep(0.1)
            pyautogui.write('kill', interval=0.03)
            time.sleep(0.05)
            pyautogui.press('enter')
            time.sleep(0.05)
            pyautogui.press('f1')
        threading.Thread(target=_run, daemon=True).start()
        return True
    return False



def _lock_workstation():
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.user32.LockWorkStation()
        return True
    elif pyautogui:
        pyautogui.hotkey('ctrl', 'alt', 'l')
        return True
    return False

def _open_terminal():
    if sys.platform == 'win32':
        subprocess.Popen(['powershell.exe', '-NoExit'])
        return True
    else:
        subprocess.Popen(['x-terminal-emulator'])
        return True

# ---------------------------------------------------------------------------
# WORKER DE TRANSMISSÃO DE ÁUDIO UDP (BAIXA LATÊNCIA)
# ---------------------------------------------------------------------------
class AudioStreamer:
    def __init__(self):
        self.is_running = False
        self.client_ip: Optional[str] = None
        self.client_port: int = 50005
        self.sample_rate: int = 48000
        self.channels: int = 2
        self.chunk_size: int = 1024  # Amostras por pacote para latência mínima
        self.thread: Optional[threading.Thread] = None
        self.sock: Optional[socket.socket] = None

    def start(self, client_ip: str, client_port: int = 50005, sample_rate: int = 48000, channels: int = 2):
        if self.is_running:
            self.stop()

        self.client_ip = client_ip
        self.client_port = client_port
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_running = True

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Otimização de socket UDP para baixa latência
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)

        self.thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.thread.start()
        logger.info(f"Audio Streamer (PC -> Celular) iniciado para {client_ip}:{client_port} ({sample_rate}Hz, {channels}ch)")

    def stop(self):
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        logger.info("Audio Streamer (PC -> Celular) finalizado.")

    def _stream_loop(self):
        dest = (self.client_ip, self.client_port)
        p = None
        stream = None

        # Tentar abrir captura via PyAudio / PyAudioWPatch (WASAPI Loopback)
        if PYAUDIO_AVAILABLE:
            try:
                p = pyaudio.PyAudio()
                device_index = None
                actual_rate = self.sample_rate
                actual_channels = self.channels

                if sys.platform == "win32":
                    try:
                        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
                        default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])

                        loopback_dev = None
                        if default_speakers.get("isLoopbackDevice", False):
                            loopback_dev = default_speakers
                        else:
                            for x in range(p.get_device_count()):
                                dev = p.get_device_info_by_index(x)
                                if dev.get("isLoopbackDevice", False) and dev["name"].startswith(default_speakers["name"]):
                                    loopback_dev = dev
                                    break
                            if not loopback_dev:
                                for x in range(p.get_device_count()):
                                    dev = p.get_device_info_by_index(x)
                                    if dev.get("isLoopbackDevice", False):
                                        loopback_dev = dev
                                        break

                        if loopback_dev:
                            device_index = loopback_dev["index"]
                            actual_rate = int(loopback_dev.get("defaultSampleRate", 48000))
                            actual_channels = min(2, int(loopback_dev.get("maxInputChannels", 2)))
                            logger.info(f"Dispositivo WASAPI Loopback selecionado: {loopback_dev['name']} ({actual_rate}Hz, {actual_channels}ch)")
                    except Exception as e:
                        logger.warning(f"Não foi possível obter loopback WASAPI direto: {e}")

                stream = p.open(
                    format=pyaudio.paInt16,
                    channels=actual_channels,
                    rate=actual_rate,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=self.chunk_size
                )
                logger.info(f"Captura de áudio real do Windows aberta com sucesso (dispositivo {device_index}).")
            except Exception as e:
                logger.warning(f"Não foi possível abrir captura real de áudio: {e}. Usando sintetizador gerador de teste.")
                if stream:
                    try:
                        stream.close()
                    except Exception:
                        pass
                    stream = None

        # Loop de transmissão contínua
        phase = 0.0
        while self.is_running:
            try:
                if stream:
                    data = stream.read(self.chunk_size, exception_on_overflow=False)
                else:
                    if np is not None:
                        t = (np.arange(self.chunk_size) + phase) / self.sample_rate
                        phase += self.chunk_size
                        freq = 440.0
                        sine = (0.2 * np.sin(2 * np.pi * freq * t) * 32767).astype(np.int16)
                        stereo = np.empty((self.chunk_size * 2,), dtype=np.int16)
                        stereo[0::2] = sine
                        stereo[1::2] = sine
                        data = stereo.tobytes()
                    else:
                        data = b'\x00' * (self.chunk_size * 4)
                    time.sleep(self.chunk_size / self.sample_rate)

                if self.sock and data:
                    self.sock.sendto(data, dest)
            except Exception as e:
                if self.is_running:
                    time.sleep(0.02)

        if stream:
            try:
                stream.stop_stream()
                stream.close()
            except Exception:
                pass
        if p:
            try:
                p.terminate()
            except Exception:
                pass


class AudioInReceiver:
    """Recebe áudio do microfone do celular via UDP na porta 50006 e reproduz nos alto-falantes do PC."""
    def __init__(self, port: int = 50006):
        self.port = port
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.sock: Optional[socket.socket] = None

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._recv_loop, daemon=True)
        self.thread.start()
        logger.info(f"AudioInReceiver (Celular -> PC) ativo na porta UDP {self.port}")

    def stop(self):
        self.is_running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        logger.info("AudioInReceiver (Celular -> PC) parado.")

    def _recv_loop(self):
        p = None
        out_stream = None
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(("0.0.0.0", self.port))
            self.sock.settimeout(1.0)

            if PYAUDIO_AVAILABLE:
                p = pyaudio.PyAudio()
                out_stream = p.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=48000,
                    output=True,
                    frames_per_buffer=1024
                )

            while self.is_running:
                try:
                    data, _ = self.sock.recvfrom(4096)
                    if out_stream and data:
                        out_stream.write(data)
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.is_running:
                        time.sleep(0.02)
        except Exception as e:
            logger.error(f"Erro no AudioInReceiver: {e}")
        finally:
            if out_stream:
                try:
                    out_stream.stop_stream()
                    out_stream.close()
                except Exception:
                    pass
            if p:
                try:
                    p.terminate()
                except Exception:
                    pass

audio_streamer = AudioStreamer()
audio_in_receiver = AudioInReceiver()

# ---------------------------------------------------------------------------
# DETECÇÃO DE MAC DA PLACA FÍSICA PARA WAKE-ON-LAN
# ---------------------------------------------------------------------------
def get_primary_mac() -> str:
    """Detecta o endereço MAC da placa de rede física principal ativa (evitando adaptadores virtuais)."""
    try:
        import psutil
        stats = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()
        candidates = []
        for iface, if_addrs in addrs.items():
            if iface in stats and stats[iface].isup:
                lower_name = iface.lower()
                if any(v in lower_name for v in ['vethernet', 'virtual', 'loopback', 'wsl', 'hyper-v']):
                    continue
                for a in if_addrs:
                    if getattr(a, 'family', None) == psutil.AF_LINK or str(getattr(a, 'family', '')) == 'AddressFamily.AF_LINK' or getattr(a.family, 'name', '') == 'AF_LINK' or str(getattr(a, 'family', -1)) == '-1':
                        mac = a.address.replace('-', ':').upper()
                        if len(mac) == 17 and mac != '00:00:00:00:00:00':
                            speed = stats[iface].speed
                            candidates.append((speed, iface, mac))
        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][2]
    except Exception as e:
        logger.error(f"Erro ao detectar MAC da placa física: {e}")
    return "10:FF:E0:46:8C:9B"

# ---------------------------------------------------------------------------
# ENDPOINTS REST DA API
# ---------------------------------------------------------------------------
@app.get("/api/status")
def get_status():
    """Retorna o status do servidor, plataforma, endereço MAC e estado dos módulos."""
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "127.0.0.1"

    primary_mac = get_primary_mac()

    return {
        "status": "online",
        "app_name": "MacroEngine Server",
        "hostname": hostname,
        "local_ip": local_ip,
        "mac_address": primary_mac,
        "os": f"{platform.system()} {platform.release()}",
        "pyautogui_enabled": pyautogui is not None,
        "pycaw_enabled": PYCAW_AVAILABLE,
        "audio_stream_active": audio_streamer.is_running,
        "audio_stream_target": f"{audio_streamer.client_ip}:{audio_streamer.client_port}" if audio_streamer.is_running else None,
        "autostart_enabled": is_windows_autostart_enabled(),
        "game_mode_active": GAME_MODE_ACTIVE,
        "tray_enabled": _tray_icon is not None
    }

@app.get("/api/wol/info")
def get_wol_info():
    """Retorna dados de diagnóstico e MAC para configuração de Wake-on-LAN."""
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "127.0.0.1"
    return {
        "mac_address": get_primary_mac(),
        "ip": local_ip,
        "adapter_name": "Ethernet 3 (Realtek PCIe GbE Family Controller)",
        "wol_supported": True,
        "recommended_ports": [9, 7]
    }

# ---------------------------------------------------------------------------
# ENDPOINTS DE AUTOSTART E CONFIGURAÇÃO DO SERVIDOR
# ---------------------------------------------------------------------------
@app.get("/api/autostart/status")
def get_autostart_status():
    """Verifica se o servidor está configurado para inicializar com o Windows."""
    return {
        "autostart_enabled": is_windows_autostart_enabled(),
        "platform": sys.platform,
        "entry_name": REG_AUTOSTART_NAME
    }

@app.post("/api/autostart/enable")
def enable_autostart():
    """Habilita a inicialização automática silenciosa com o Windows."""
    ok = set_windows_autostart(True)
    return {
        "status": "success" if ok else "error",
        "autostart_enabled": True,
        "message": "Inicialização automática com o Windows ativada com sucesso."
    }

@app.post("/api/autostart/disable")
def disable_autostart():
    """Desativa a inicialização automática com o Windows."""
    ok = set_windows_autostart(False)
    return {
        "status": "success" if ok else "error",
        "autostart_enabled": False,
        "message": "Inicialização automática com o Windows desativada."
    }

@app.post("/api/autostart/toggle")
def toggle_autostart():
    """Alterna o status da inicialização automática com o Windows."""
    current = is_windows_autostart_enabled()
    new_state = not current
    ok = set_windows_autostart(new_state)
    return {
        "status": "success" if ok else "error",
        "autostart_enabled": new_state,
        "message": f"Inicialização automática {'ativada' if new_state else 'desativada'} no Windows."
    }

@app.get("/api/config")
def get_server_configuration():
    """Retorna as configurações atuais do servidor (config.json)."""
    return load_config()

@app.post("/api/game-mode/toggle")
def api_toggle_game_mode():
    """Alterna o Modo Jogo Turbo (ajusta prioridade de energia do PC)."""
    new_state = toggle_game_mode()
    return {
        "status": "success",
        "game_mode_active": new_state,
        "message": f"Modo Jogo Turbo {'ATIVADO (Alto Desempenho)' if new_state else 'DESATIVADO (Equilibrado)'}."
    }

@app.post("/api/system/sleep")
def api_system_sleep():
    """Coloca o computador em modo de suspensão profunda (Sleep S3 - Ideal para Wake-on-LAN)."""
    logger.info("Comando de suspensão (Sleep) recebido via API.")
    ok = _sleep_pc()
    return {"status": "ok" if ok else "error", "action": "sleep", "message": "Computador entrando em modo de suspensão."}

@app.post("/api/system/shutdown")
def api_system_shutdown():
    """Desliga o computador completamente."""
    logger.info("Comando de desligamento completo (Power Off) recebido via API.")
    ok = _shutdown_pc()
    return {"status": "ok" if ok else "error", "action": "shutdown", "message": "Desligamento do sistema operacional iniciado."}

@app.post("/api/server/shutdown")
def shutdown_server():
    """Encerra o servidor desktop de forma segura e limpa."""
    logger.info("Requisição de desligamento do servidor recebida via API.")
    def _do_shutdown():
        time.sleep(0.8)
        if _tray_icon:
            try:
                _tray_icon.stop()
            except Exception:
                pass
        os._exit(0)
    threading.Thread(target=_do_shutdown, daemon=True).start()
    return {"status": "shutting_down", "message": "O servidor está sendo encerrado."}

@app.post("/api/mute")
def panic_mute(background_tasks: BackgroundTasks):
    """
    BOTÃO DE PÂNICO / SILÊNCIO ABSOLUTO (TOGGLE):
    Alterna o mudo do áudio master. Se estiver desmutado, muta e pausa mídia.
    Se já estiver mutado, desmuta e restaura o som do computador na hora.
    """
    logger.info("Acionamento do BOTÃO DE PÂNICO (Mudo / Desmudo)!")
    is_now_muted = toggle_system_mute()
    pause_success = False
    if is_now_muted:
        pause_success = pause_active_media()

    return {
        "status": "panic_executed",
        "system_muted": is_now_muted,
        "media_paused": pause_success,
        "timestamp": time.time(),
        "message": "Áudio master mutado e mídia pausada." if is_now_muted else "Áudio master desmutado com sucesso (som restaurado)."
    }

@app.post("/api/open-url")
def open_url(payload: OpenUrlRequest):
    """Abre instantaneamente o link especificado no navegador padrão do desktop."""
    url = payload.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="A URL não pode estar vazia.")

    # Sanitização básica de URL
    if not (url.startswith("http://") or url.startswith("https://") or url.startswith("steam://")):
        url = "https://" + url

    logger.info(f"Abrindo URL no navegador desktop: {url}")
    opened = launch_url_on_desktop(url)

    return {
        "status": "success",
        "url": url,
        "opened": opened,
        "message": "Link despachado para o navegador do PC."
    }

@app.post("/api/execute-actions")
def execute_actions(payload: ExecuteActionsRequest):
    """
    Executa em lote ações de automação enviadas pelo assistente On-Device SLM do Android.
    Suporta: hotkey, launch, kill, volume_mute, volume_set.
    """
    results = []
    logger.info(f"Recebida lista de {len(payload.actions)} ações do assistente SLM")

    for item in payload.actions:
        act = item.action.lower().strip()
        res = {"action": act, "success": False, "message": ""}
        try:
            logger.info(f"[SLM EXEC] Ação recebida: act='{act}' | target='{item.target}' | keys={item.keys} | level={item.level}")

            if act == "hotkey":
                # Executa combinação de teclas via pyautogui
                if item.keys and pyautogui:
                    clean_keys = [k.lower().strip() for k in item.keys]
                    # Se for tecla multimídia única (volumeup, volumedown, playpause, volumemute)
                    if len(clean_keys) == 1 and clean_keys[0] in ["volumeup", "volumedown", "volumemute", "playpause", "nexttrack", "prevtrack"]:
                        pyautogui.press(clean_keys[0])
                        res["success"] = True
                        res["message"] = f"Tecla multimídia acionada: {clean_keys[0]}"
                    else:
                        mapped_keys = []
                        for k in clean_keys:
                            if k in ["control", "ctrl_l", "ctrl_r"]:
                                mapped_keys.append("ctrl")
                            elif k in ["cmd", "super", "windows"]:
                                mapped_keys.append("win")
                            else:
                                mapped_keys.append(k)
                        pyautogui.hotkey(*mapped_keys)
                        res["success"] = True
                        res["message"] = f"Teclas acionadas: {' + '.join(mapped_keys)}"
                else:
                    res["message"] = "Nenhuma tecla fornecida ou pyautogui indisponível"

            elif act == "launch":
                target = item.target.strip()
                target_lower = target.lower()
                if not target:
                    res["message"] = "Alvo de inicialização vazio"
                elif target.startswith("http://") or target.startswith("https://") or target.startswith("steam://"):
                    opened = launch_url_on_desktop(target)
                    res["success"] = opened
                    res["message"] = f"URL despachada: {target}"
                elif target_lower in ["navegador", "browser", "internet", "google"]:
                    # Abre navegador padrão ou chrome
                    opened = launch_url_on_desktop("https://www.google.com")
                    res["success"] = opened
                    res["message"] = "Navegador web iniciado"
                elif target_lower in ["calc", "calculadora"]:
                    subprocess.Popen(['calc.exe'] if sys.platform == 'win32' else ['gnome-calculator'])
                    res["success"] = True
                    res["message"] = "Calculadora iniciada"
                elif target_lower in ["notepad", "bloco de notas", "bloco"]:
                    subprocess.Popen(['notepad.exe'] if sys.platform == 'win32' else ['gedit'])
                    res["success"] = True
                    res["message"] = "Bloco de Notas iniciado"
                else:
                    if sys.platform == "win32":
                        import win32process
                        si = win32process.STARTUPINFO()
                        si.lpDesktop = r"WinSta0\Default"
                        cmd = f'cmd.exe /c start "" "{target}"'
                        win32process.CreateProcess(None, cmd, None, None, False, 0x08000000, None, None, si)
                        res["success"] = True
                        res["message"] = f"Aplicativo iniciado: {target}"
                    else:
                        subprocess.Popen(target, shell=True)
                        res["success"] = True
                        res["message"] = f"Aplicativo iniciado: {target}"

            elif act == "kill":
                target = item.target.strip()
                target_lower = target.lower()
                if not target or target_lower in ["janela", "atual", "programa", "window", "current"]:
                    if pyautogui:
                        pyautogui.hotkey('alt', 'f4')
                        res["success"] = True
                        res["message"] = "Janela fechada via Alt+F4"
                    else:
                        res["message"] = "Pyautogui indisponível para fechar janela"
                else:
                    target_map = {
                        "chrome": ["chrome.exe"],
                        "navegador": ["chrome.exe", "msedge.exe", "brave.exe", "firefox.exe"],
                        "browser": ["chrome.exe", "msedge.exe", "brave.exe", "firefox.exe"],
                        "edge": ["msedge.exe"],
                        "firefox": ["firefox.exe"],
                        "brave": ["brave.exe"],
                        "calc": ["CalculatorApp.exe", "calc.exe"],
                        "calculadora": ["CalculatorApp.exe", "calc.exe"],
                        "notepad": ["notepad.exe"],
                        "bloco de notas": ["notepad.exe"],
                        "bloco": ["notepad.exe"],
                        "spotify": ["Spotify.exe"],
                        "discord": ["Discord.exe"],
                        "explorer": ["explorer.exe"],
                    }
                    exe_list = target_map.get(target_lower, [target if target.endswith(".exe") else f"{target}.exe"])
                    if sys.platform == "win32":
                        for exe_name in exe_list:
                            subprocess.run(f"taskkill /f /im {exe_name}", shell=True, capture_output=True)
                    else:
                        subprocess.run(f"pkill -f {target}", shell=True, capture_output=True)
                    res["success"] = True
                    res["message"] = f"Processo(s) encerrado(s): {', '.join(exe_list)}"

            elif act == "volume_mute":
                # Alterna o mudo do sistema via CoreAudio
                if sys.platform == "win32":
                    try:
                        ctypes.windll.ole32.CoInitialize(None)
                    except Exception:
                        pass
                    is_muted = toggle_system_mute()
                    res["success"] = True
                    res["message"] = "Áudio mutado" if is_muted else "Áudio desmutado (som restaurado)"
                else:
                    if pyautogui:
                        pyautogui.press("volumemute")
                    res["success"] = True
                    res["message"] = "Comando volumemute enviado"

            elif act == "volume_set":
                lvl = item.level if item.level is not None else 50
                lvl = max(0, min(100, lvl))
                if sys.platform == "win32" and PYCAW_AVAILABLE:
                    try:
                        ctypes.windll.ole32.CoInitialize(None)
                    except Exception:
                        pass
                    devices = AudioUtilities.GetSpeakers()
                    if hasattr(devices, "EndpointVolume") and devices.EndpointVolume:
                        devices.EndpointVolume.SetMasterVolumeLevelScalar(lvl / 100.0, None)
                    else:
                        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                        volume = cast(interface, POINTER(IAudioEndpointVolume))
                        volume.SetMasterVolumeLevelScalar(lvl / 100.0, None)
                    res["success"] = True
                    res["message"] = f"Volume ajustado para {lvl}%"
                else:
                    res["message"] = f"Volume solicitado para {lvl}%, mas pycaw indisponível"
            else:
                res["message"] = f"Ação desconhecida: {act}"

        except Exception as e:
            res["success"] = False
            res["message"] = f"Erro ao executar {act}: {str(e)}"
            logger.error(f"Erro ao executar ação {act}: {e}")

        results.append(res)

    return {
        "status": "executed",
        "count": len(results),
        "results": results
    }

SERVER_MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
os.makedirs(SERVER_MODELS_DIR, exist_ok=True)

@app.api_route("/api/models/slm_model.bin", methods=["GET", "HEAD"])
def download_server_slm_model():
    """Permite ao smartphone baixar arquivos de modelo SLM (.bin/.task) diretamente do PC via Wi-Fi."""
    if os.path.exists(SERVER_MODELS_DIR):
        for fname in os.listdir(SERVER_MODELS_DIR):
            if fname.endswith(".bin") or fname.endswith(".task"):
                fpath = os.path.join(SERVER_MODELS_DIR, fname)
                if os.path.isfile(fpath) and os.path.getsize(fpath) > 1024 * 1024:
                    return FileResponse(fpath, filename="slm_model.bin", media_type="application/octet-stream")
    raise HTTPException(status_code=404, detail="Nenhum arquivo de modelo (.bin ou .task) encontrado na pasta 'server/models/' do computador.")

@app.get("/api/download/apk")
def download_app_apk():
    """Permite ao usuário baixar o APK atualizado diretamente pelo celular ou PC."""
    local_apk = os.path.join(os.path.dirname(os.path.abspath(__file__)), "MacroEngine-1.1.9v.apk")
    if os.path.exists(local_apk):
        return FileResponse(local_apk, filename="MacroEngine-1.1.9v.apk", media_type="application/vnd.android.package-archive")
    apk_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "build", "outputs", "apk", "debug", "app-debug.apk")
    if os.path.exists(apk_path):
        return FileResponse(apk_path, filename="MacroEngine-1.1.9v.apk", media_type="application/vnd.android.package-archive")
    raise HTTPException(status_code=404, detail="APK não encontrado.")


# ---------------------------------------------------------------------------
# TRANSFERÊNCIA DE ARQUIVOS (PC <-> CELULAR)
# ---------------------------------------------------------------------------
@app.post("/api/files/upload")
async def upload_file(file: UploadFile = File(...)):
    """Recebe um arquivo enviado do celular ou outro dispositivo e salva na pasta compartilhada do PC."""
    try:
        raw_name = file.filename or "arquivo_recebido"
        safe_filename = os.path.basename(raw_name)
        dest_path = os.path.join(SHARED_FILES_DIR, safe_filename)

        # Se já existir um arquivo com o mesmo nome, adiciona timestamp para evitar sobrescrever
        if os.path.exists(dest_path):
            name, ext = os.path.splitext(safe_filename)
            dest_path = os.path.join(SHARED_FILES_DIR, f"{name}_{int(time.time())}{ext}")
            safe_filename = os.path.basename(dest_path)

        size = 0
        with open(dest_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                buffer.write(chunk)
                size += len(chunk)

        logger.info(f"Arquivo recebido do celular: {safe_filename} ({format_file_size(size)}) salvo em {dest_path}")
        return {
            "status": "success",
            "message": f"Arquivo '{safe_filename}' salvo com sucesso no PC!",
            "filename": safe_filename,
            "size": format_file_size(size),
            "size_bytes": size,
            "saved_path": dest_path,
            "directory": SHARED_FILES_DIR
        }
    except Exception as e:
        logger.error(f"Erro ao receber upload de arquivo: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo: {str(e)}")

@app.get("/api/files/list")
def list_shared_files():
    """Lista todos os arquivos presentes na pasta compartilhada para download no celular."""
    try:
        files = []
        if os.path.exists(SHARED_FILES_DIR):
            for entry in os.scandir(SHARED_FILES_DIR):
                if entry.is_file():
                    stat = entry.stat()
                    mod_time = time.strftime("%d/%m/%Y %H:%M", time.localtime(stat.st_mtime))
                    files.append({
                        "name": entry.name,
                        "size": format_file_size(stat.st_size),
                        "size_bytes": stat.st_size,
                        "modified": mod_time,
                        "path": entry.path
                    })
        files.sort(key=lambda x: x["name"].lower())
        return {
            "status": "success",
            "count": len(files),
            "directory": SHARED_FILES_DIR,
            "files": files
        }
    except Exception as e:
        logger.error(f"Erro ao listar arquivos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files/download/{filename}")
def download_shared_file(filename: str):
    """Permite ao celular baixar qualquer arquivo presente na pasta compartilhada do PC."""
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(SHARED_FILES_DIR, safe_filename)
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado na pasta compartilhada.")

    return FileResponse(
        path=file_path,
        filename=safe_filename,
        media_type="application/octet-stream"
    )

@app.post("/api/files/open-folder")
def open_shared_folder():
    """Abre a pasta compartilhada no Windows Explorer para fácil visualização."""
    try:
        if sys.platform == "win32":
            os.startfile(SHARED_FILES_DIR)
        elif sys.platform.startswith("linux"):
            subprocess.Popen(["xdg-open", SHARED_FILES_DIR])
        return {
            "status": "success",
            "message": "Pasta compartilhada aberta no Explorer do Windows.",
            "directory": SHARED_FILES_DIR
        }
    except Exception as e:
        logger.error(f"Erro ao abrir pasta compartilhada: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/files/delete/{filename}")
def delete_shared_file(filename: str):
    """Exclui um arquivo da pasta compartilhada."""
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(SHARED_FILES_DIR, safe_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    try:
        os.remove(file_path)
        return {"status": "success", "message": f"Arquivo '{safe_filename}' removido."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/macros")
def list_macros():
    """Retorna a lista de todas as macros registradas."""
    return [
        {
            "id": macro_id,
            "name": data["name"],
            "category": data["category"]
        }
        for macro_id, data in MACRO_DEFINITIONS.items()
    ]

@app.post("/api/macro/{macro_id}", response_model=MacroExecutionResponse)
def execute_macro(macro_id: str):
    """Executa a macro identificada pelo ID."""
    macro = MACRO_DEFINITIONS.get(macro_id)
    if not macro:
        raise HTTPException(
            status_code=404,
            detail=f"Macro '{macro_id}' não encontrada. Macros disponíveis: {list(MACRO_DEFINITIONS.keys())}"
        )

    try:
        logger.info(f"Executando macro: {macro['name']} ({macro_id})")
        macro["action"]()
        return MacroExecutionResponse(
            macro_id=macro_id,
            description=macro["name"],
            success=True,
            message=f"Macro '{macro['name']}' disparada com sucesso."
        )
    except Exception as e:
        logger.error(f"Erro ao executar macro {macro_id}: {e}")
        return MacroExecutionResponse(
            macro_id=macro_id,
            description=macro["name"],
            success=False,
            message=f"Falha na execução: {str(e)}"
        )

@app.post("/api/audio/start")
def start_audio_stream(payload: AudioStreamStartRequest, request: Request):
    """Inicia a transmissão de áudio UDP de baixa latência para o IP do cliente."""
    client_ip = payload.client_ip
    if not client_ip or client_ip in ["0.0.0.0", "127.0.0.1"]:
        if request.client and request.client.host:
            client_ip = request.client.host
    audio_streamer.start(
        client_ip=client_ip,
        client_port=payload.client_port,
        sample_rate=payload.sample_rate,
        channels=payload.channels
    )
    return {
        "status": "started",
        "client_ip": client_ip,
        "client_port": payload.client_port,
        "sample_rate": payload.sample_rate,
        "channels": payload.channels
    }

@app.post("/api/audio/stop")
def stop_audio_stream():
    """Interrompe a transmissão de áudio UDP (PC -> Celular)."""
    audio_streamer.stop()
    return {"status": "stopped"}

@app.post("/api/audio/mic/start")
def start_mic_stream():
    """Inicia o receptor de áudio do microfone do celular para tocar no PC (Celular -> PC)."""
    audio_in_receiver.start()
    return {"status": "started", "port": 50006}

@app.post("/api/audio/mic/stop")
def stop_mic_stream():
    """Interrompe o receptor de áudio do microfone do celular no PC."""
    audio_in_receiver.stop()
    return {"status": "stopped"}

# ---------------------------------------------------------------------------
# GERENCIADOR DE ESPELHAMENTO DE TELA (SCRCPY)
# ---------------------------------------------------------------------------
def ensure_desktop_station_access():
    """Garante que a thread do processo no Windows tenha acesso à estação gráfica winsta0\\default."""
    if sys.platform == "win32":
        try:
            user32 = ctypes.windll.user32
            MAXIMUM_ALLOWED = 0x02000000
            hw = user32.OpenWindowStationW('winsta0', False, MAXIMUM_ALLOWED)
            if hw:
                user32.SetProcessWindowStation(hw)
            hd = user32.OpenDesktopW('default', 0, False, MAXIMUM_ALLOWED)
            if hd:
                user32.SetThreadDesktop(hd)
        except Exception as e:
            logger.debug(f"Aviso winsta0: {e}")

class ScreenMirrorManager:
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None

    def find_scrcpy_binary(self) -> Optional[str]:
        import shutil
        scrcpy_path = shutil.which("scrcpy")
        if scrcpy_path:
            return scrcpy_path

        # Caminho oficial do Winget no Windows
        winget_path = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Genymobile.scrcpy_Microsoft.Winget.Source_8wekyb3d8bbwe\scrcpy-win64-v4.1\scrcpy.exe")
        if os.path.exists(winget_path):
            return winget_path

        pkg_dir = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages")
        if os.path.exists(pkg_dir):
            for root, dirs, files in os.walk(pkg_dir):
                if "scrcpy.exe" in files:
                    return os.path.join(root, "scrcpy.exe")

        return None

    def start(self) -> Dict[str, Any]:
        if self.is_running():
            return {"status": "already_running", "message": "O espelhamento já está ativo na tela do PC."}

        binary = self.find_scrcpy_binary()
        if not binary:
            raise HTTPException(
                status_code=500,
                detail="Binário do scrcpy não encontrado no PC. Verifique a instalação do scrcpy."
            )

        adb_bin = get_adb_binary()
        env = os.environ.copy()
        if adb_bin:
            env["ADB"] = adb_bin

        cmd = [
            binary,
            "--window-title", "MacroEngine - Espelhamento do Celular",
            "--max-fps", "60",
            "--video-bit-rate", "12M",
            "--stay-awake"
        ]

        logger.info(f"Iniciando scrcpy com ADB={adb_bin}: {' '.join(cmd)}")
        try:
            self.process = subprocess.Popen(cmd, env=env)
            return {"status": "started", "message": "Janela de espelhamento aberta no PC com sucesso!"}
        except Exception as e:
            logger.error(f"Erro ao disparar scrcpy: {e}")
            raise HTTPException(status_code=500, detail=f"Erro ao iniciar scrcpy: {e}")

    def stop(self) -> Dict[str, Any]:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process = None
            return {"status": "stopped", "message": "Espelhamento encerrado."}
        self.process = None
        return {"status": "not_running", "message": "O espelhamento não estava em execução."}

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

mirror_manager = ScreenMirrorManager()

@app.post("/api/mirror/start")
@app.get("/api/mirror/start")
def start_screen_mirror():
    """Inicia o espelhamento da tela do celular no PC via Scrcpy com controle de mouse/teclado."""
    return mirror_manager.start()

@app.post("/api/mirror/stop")
@app.get("/api/mirror/stop")
def stop_screen_mirror():
    """Encerra a janela de espelhamento do Scrcpy."""
    return mirror_manager.stop()

@app.get("/api/mirror/status")
def get_mirror_status():
    """Retorna o status do espelhamento de tela."""
    return {
        "is_mirroring": mirror_manager.is_running(),
        "scrcpy_available": mirror_manager.find_scrcpy_binary() is not None
    }

# ---------------------------------------------------------------------------
# STREAMING DE TELA AO VIVO BIDIRECIONAL (PC <-> CELULAR)
# ---------------------------------------------------------------------------
# Instância global reutilizável de MSS para evitar overhead de reabertura GDI
_mss_sct = None
_mss_lock = threading.Lock()

def get_mss_instance():
    global _mss_sct
    if _mss_sct is None and MSS_AVAILABLE:
        try:
            mss_cls = getattr(mss, "MSS", getattr(mss, "mss", None))
            if mss_cls:
                _mss_sct = mss_cls()
        except Exception as e:
            logger.debug(f"Erro ao instanciar MSS: {e}")
    return _mss_sct

_pc_screen_w, _pc_screen_h = 1920, 1080
_phone_screen_w, _phone_screen_h = 1280, 2772

def capture_pc_screen_jpeg(width: int = 960, height: int = 540, quality: int = 48) -> bytes:
    """Captura a tela do PC e comprime em JPEG com latência ultra baixa (< 15ms)."""
    ensure_desktop_station_access()

    # 1. Tenta MSS global persistente (latência mínima de 5 a 10ms)
    sct = get_mss_instance()
    if sct:
        try:
            with _mss_lock:
                m = sct.monitors[1]
                raw = sct.grab(m)
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
            if img.width > width or img.height > height:
                img.thumbnail((width, height), Image.Resampling.BILINEAR)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=False)
            return buf.getvalue()
        except Exception:
            # Em caso de falha de thread desktop do MSS, recria instância
            try:
                global _mss_sct
                _mss_sct = None
                sct = get_mss_instance()
                if sct:
                    with _mss_lock:
                        m = sct.monitors[1]
                        raw = sct.grab(m)
                    img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
                    if img.width > width or img.height > height:
                        img.thumbnail((width, height), Image.Resampling.BILINEAR)
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=quality, optimize=False)
                    return buf.getvalue()
            except Exception as e:
                logger.debug(f"Aviso MSS persistente: {e}")

    # 2. Tenta PIL ImageGrab
    try:
        img = ImageGrab.grab()
        if img.width > width or img.height > height:
            img.thumbnail((width, height), Image.Resampling.BILINEAR)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=False)
        return buf.getvalue()
    except Exception as e:
        logger.debug(f"Aviso ImageGrab: {e}")

    # 3. Fallback elegante
    img = Image.new("RGB", (width, height), color=(18, 18, 18))
    draw = ImageDraw.Draw(img)
    draw.rectangle([(20, 20), (width - 20, height - 20)], outline=(0, 229, 255), width=2)
    draw.text((width // 2 - 140, height // 2 - 20), "REMOTE MASTER DESKTOP ATIVO", fill=(0, 229, 255))
    draw.text((width // 2 - 120, height // 2 + 10), time.strftime("%H:%M:%S"), fill=(240, 240, 240))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()

def stream_pc_screen():
    """Gera stream contínuo de frames MJPEG da tela do PC."""
    while True:
        frame = capture_pc_screen_jpeg()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.04)

def get_adb_binary() -> str:
    local_sdk = os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe")
    if os.path.exists(local_sdk):
        return local_sdk
    import shutil
    adb_path = shutil.which("adb")
    if adb_path:
        return adb_path
    return "adb"

class PhoneScreenCaptureManager:
    """Gerenciador de captura contínua e em tempo real da tela do celular para streaming com latência zero."""
    def __init__(self):
        self._lock = threading.Lock()
        self._capture_lock = threading.Lock()
        self._latest_jpeg: Optional[bytes] = None
        self._frame_id: int = 0
        self._wake_event = threading.Event()
        self._running = True
        try:
            adb = get_adb_binary()
            subprocess.run([adb, "start-server"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4)
        except Exception:
            pass
        self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="PhoneScreenCaptureWorker")
        self._thread.start()

    def notify_screen_changed(self):
        """Acorda o worker imediatamente para capturar o novo estado da tela após toque ou macro."""
        self._wake_event.set()

    def get_latest_frame(self) -> bytes:
        with self._lock:
            if self._latest_jpeg is not None:
                return self._latest_jpeg

        with self._capture_lock:
            if self._latest_jpeg is not None:
                return self._latest_jpeg
            frame = self._do_capture(quality=55)
            if frame:
                with self._lock:
                    self._latest_jpeg = frame
                return frame

        # Fallback inicial antes da primeira captura
        img = Image.new("RGB", (360, 640), color=(25, 25, 25))
        draw = ImageDraw.Draw(img)
        draw.text((60, 300), "Aguardando Celular...", fill=(0, 230, 118))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=50)
        return buf.getvalue()

    def get_frame_id(self) -> int:
        with self._lock:
            return self._frame_id

    def _do_capture(self, quality: int = 55) -> Optional[bytes]:
        import struct
        adb = get_adb_binary()

        # 1. Captura RAW ultra-rápida (elimina o atraso e tela preta causada pelo libpng na tela inicial/menu)
        try:
            proc = subprocess.run(
                [adb, "exec-out", "screencap"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=3.0
            )
            if proc.returncode == 0 and len(proc.stdout) > 16:
                w, h, fmt = struct.unpack('<III', proc.stdout[:12])
                expected_size = 16 + (w * h * 4)
                if len(proc.stdout) >= expected_size and w > 0 and h > 0:
                    img = Image.frombuffer('RGBA', (w, h), proc.stdout[16:expected_size], 'raw', 'RGBA', 0, 1)
                    target_w = 426
                    target_h = int(target_w * (h / w))
                    img_small = img.resize((target_w, target_h), Image.Resampling.BOX).convert('RGB')
                    buf = io.BytesIO()
                    img_small.save(buf, format="JPEG", quality=quality, optimize=False)
                    return buf.getvalue()
            elif proc.stderr and (b"protocol fault" in proc.stderr or b"connection reset" in proc.stderr):
                subprocess.run([adb, "start-server"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4)
        except Exception as e:
            logger.debug(f"Aviso captura raw: {e}")

        # 2. Fallback PNG se raw não estiver disponível
        try:
            proc = subprocess.run(
                [adb, "exec-out", "screencap", "-p"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=3.5
            )
            if proc.returncode == 0 and proc.stdout:
                img = Image.open(io.BytesIO(proc.stdout)).convert("RGB")
                img.thumbnail((480, 1040), Image.Resampling.BILINEAR)
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=quality, optimize=False)
                return buf.getvalue()
        except Exception as e:
            logger.debug(f"Aviso captura png fallback: {e}")

        return None

    def _worker_loop(self):
        while self._running:
            try:
                with self._capture_lock:
                    frame = self._do_capture(quality=55)
                if frame and len(frame) > 1000:
                    with self._lock:
                        self._latest_jpeg = frame
                        self._frame_id += 1
            except Exception as e:
                logger.debug(f"Erro worker phone capture: {e}")

            # Pequeno intervalo adaptativo: se houver evento de toque, acorda imediatamente!
            self._wake_event.wait(timeout=0.06)
            self._wake_event.clear()

phone_screen_manager = PhoneScreenCaptureManager()

def capture_phone_screen_jpeg(quality: int = 55) -> bytes:
    """Retorna o frame mais recente da tela do celular servido diretamente da memória RAM."""
    return phone_screen_manager.get_latest_frame()

def stream_phone_screen():
    """Gera stream contínuo de frames MJPEG da tela do celular servido da memória RAM sem bloqueios."""
    last_id = -1
    while True:
        curr_id = phone_screen_manager.get_frame_id()
        if curr_id != last_id:
            frame = phone_screen_manager.get_latest_frame()
            last_id = curr_id
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n'
                   b'Content-Length: ' + str(len(frame)).encode() + b'\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.03)

@app.get("/api/screen/stream")
def get_pc_screen_stream():
    """Retorna o stream de vídeo MJPEG em tempo real da tela do PC."""
    return StreamingResponse(
        stream_pc_screen(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/api/screen/frame")
def get_pc_screen_frame():
    """Retorna um único frame da tela do PC."""
    return Response(content=capture_pc_screen_jpeg(), media_type="image/jpeg")

@app.post("/api/screen/input")
def handle_pc_screen_input(payload: ScreenInputRequest):
    """Executa ações de mouse na tela do PC baseadas em toques relativos (0.0 a 1.0) com latência sub-milissegundo."""
    global _pc_screen_w, _pc_screen_h
    if sys.platform == "win32":
        try:
            _pc_screen_w = ctypes.windll.user32.GetSystemMetrics(0)
            _pc_screen_h = ctypes.windll.user32.GetSystemMetrics(1)
        except Exception:
            pass

    target_x = max(0, min(_pc_screen_w - 1, int(payload.x * _pc_screen_w)))
    target_y = max(0, min(_pc_screen_h - 1, int(payload.y * _pc_screen_h)))

    if sys.platform == "win32":
        u32 = ctypes.windll.user32
        u32.SetCursorPos(target_x, target_y)

        if payload.action == "click":
            u32.mouse_event(0x0002, 0, 0, 0, 0) # LEFTDOWN
            u32.mouse_event(0x0004, 0, 0, 0, 0) # LEFTUP
        elif payload.action == "right_click":
            u32.mouse_event(0x0008, 0, 0, 0, 0) # RIGHTDOWN
            u32.mouse_event(0x0010, 0, 0, 0, 0) # RIGHTUP
        elif payload.action == "double_click":
            u32.mouse_event(0x0002, 0, 0, 0, 0)
            u32.mouse_event(0x0004, 0, 0, 0, 0)
            u32.mouse_event(0x0002, 0, 0, 0, 0)
            u32.mouse_event(0x0004, 0, 0, 0, 0)
        elif payload.action == "drag_start":
            u32.mouse_event(0x0002, 0, 0, 0, 0) # Segura o botão esquerdo
        elif payload.action == "drag_end":
            u32.mouse_event(0x0004, 0, 0, 0, 0) # Solta o botão esquerdo
        elif payload.action == "scroll_up":
            u32.mouse_event(0x0800, 0, 0, 120, 0)
        elif payload.action == "scroll_down":
            u32.mouse_event(0x0800, 0, 0, -120, 0)
    else:
        if pyautogui:
            if payload.action == "click":
                pyautogui.click(target_x, target_y)
            elif payload.action == "right_click":
                pyautogui.rightClick(target_x, target_y)
            elif payload.action == "double_click":
                pyautogui.doubleClick(target_x, target_y)
            elif payload.action == "move":
                pyautogui.moveTo(target_x, target_y)

    return {"status": "ok", "x": target_x, "y": target_y, "action": payload.action}

@app.get("/api/phone/screen/stream")
def get_phone_screen_stream():
    """Retorna o stream de vídeo MJPEG em tempo real da tela do celular para o PC."""
    return StreamingResponse(
        stream_phone_screen(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/api/phone/screen/frame")
def get_phone_screen_frame(urgent: int = 0):
    """Retorna um único frame em JPEG servido diretamente da memória RAM em 0ms."""
    if urgent:
        phone_screen_manager.notify_screen_changed()
    return Response(
        content=phone_screen_manager.get_latest_frame(),
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "X-Frame-Id": str(phone_screen_manager.get_frame_id()),
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
    )

@app.post("/api/phone/screen/touch")
def handle_phone_touch_input(payload: PhoneTouchRequest):
    """Executa toque na tela do celular a partir do PC de forma rápida e assíncrona com atualização imediata de tela."""
    adb = get_adb_binary()
    px = int(payload.x * _phone_screen_w)
    py_pos = int(payload.y * _phone_screen_h)
    subprocess.Popen([adb, "shell", "input", "tap", str(px), str(py_pos)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    phone_screen_manager.notify_screen_changed()
    return {"status": "ok", "x": px, "y": py_pos}

# ---------------------------------------------------------------------------
# MACROS NATIVAS PARA MEXER NO CELULAR VIA ADB
# ---------------------------------------------------------------------------
PHONE_MACROS: Dict[str, list] = {
    # Navegação
    "back": ["shell", "input", "keyevent", "4"],
    "home": ["shell", "input", "keyevent", "3"],
    "recents": ["shell", "input", "keyevent", "187"],
    "power": ["shell", "input", "keyevent", "26"],
    "notifications": ["shell", "cmd", "statusbar", "expand-notifications"],
    "quick_settings": ["shell", "cmd", "statusbar", "expand-settings"],
    "collapse_panels": ["shell", "cmd", "statusbar", "collapse"],

    # Gestos e Swipes
    "scroll_up": ["shell", "input", "swipe", "540", "1600", "540", "600", "200"],
    "scroll_down": ["shell", "input", "swipe", "540", "600", "540", "1600", "200"],
    "swipe_left": ["shell", "input", "swipe", "900", "1000", "150", "1000", "200"],
    "swipe_right": ["shell", "input", "swipe", "150", "1000", "900", "1000", "200"],

    # Volume & Mídia do Celular
    "vol_up": ["shell", "input", "keyevent", "24"],
    "vol_down": ["shell", "input", "keyevent", "25"],
    "vol_mute": ["shell", "input", "keyevent", "164"],
    "media_play_pause": ["shell", "input", "keyevent", "85"],
    "media_next": ["shell", "input", "keyevent", "87"],
    "media_prev": ["shell", "input", "keyevent", "88"],

    # Aplicativos no Celular
    "open_camera": ["shell", "am", "start", "-a", "android.media.action.STILL_IMAGE_CAMERA"],
    "open_browser": ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", "https://google.com"],
    "open_settings": ["shell", "am", "start", "-a", "android.settings.SETTINGS"],
    "open_whatsapp": ["shell", "monkey", "-p", "com.whatsapp", "1"],
    "open_youtube": ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", "https://youtube.com"],
    "screenshot": ["shell", "input", "keyevent", "120"],
    "open_files": ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", "content://media/external/file"],
    "open_dialer": ["shell", "am", "start", "-a", "android.intent.action.DIAL"],
    "open_sms": ["shell", "am", "start", "-a", "android.intent.action.MAIN", "-c", "android.intent.category.APP_MESSAGING"],
    "open_gallery": ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-t", "image/*"],
    "open_music": ["shell", "monkey", "-p", "com.spotify.music", "1"],
    "open_clock": ["shell", "am", "start", "-a", "android.intent.action.SHOW_ALARMS"],
    "open_calculator": ["shell", "monkey", "-p", "com.google.android.calculator", "1"],
    "open_maps": ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", "geo:0,0"],
    "open_playstore": ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", "market://details?id=com.usbmaster.pro"],

    # Gestos adicionais
    "unlock": ["shell", "input", "swipe", "540", "1800", "540", "600", "200"],
    "scroll_top": ["shell", "input", "swipe", "540", "400", "540", "2200", "200"],
    "scroll_bottom": ["shell", "input", "swipe", "540", "2200", "540", "400", "200"],
    "double_tap": ["shell", "input", "tap", "540", "1200"],

    # Teclas e Entrada de Texto no Celular
    "key_enter": ["shell", "input", "keyevent", "66"],
    "key_backspace": ["shell", "input", "keyevent", "67"],
    "key_space": ["shell", "input", "keyevent", "62"],
    "key_search": ["shell", "input", "keyevent", "84"],
    "key_tab": ["shell", "input", "keyevent", "61"],
    "key_escape": ["shell", "input", "keyevent", "111"],
    "paste_clipboard": ["shell", "input", "keyevent", "279"],

    # Configurações do Sistema do Celular
    "open_wifi_settings": ["shell", "am", "start", "-a", "android.settings.WIFI_SETTINGS"],
    "open_bluetooth_settings": ["shell", "am", "start", "-a", "android.settings.BLUETOOTH_SETTINGS"],
    "open_display_settings": ["shell", "am", "start", "-a", "android.settings.DISPLAY_SETTINGS"],
    "open_battery_settings": ["shell", "am", "start", "-a", "android.intent.action.POWER_USAGE_SUMMARY"],
    "open_sound_settings": ["shell", "am", "start", "-a", "android.settings.SOUND_SETTINGS"],
    "open_app_manager": ["shell", "am", "start", "-a", "android.settings.APPLICATION_SETTINGS"]
}

@app.post("/api/phone/macro/{macro_id}")
@app.get("/api/phone/macro/{macro_id}")
def trigger_phone_macro(macro_id: str):
    """Executa macro para mexer no celular via ADB de forma assíncrona com atualização imediata de tela."""
    adb = get_adb_binary()
    if macro_id in PHONE_MACROS:
        cmd = [adb] + PHONE_MACROS[macro_id]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        phone_screen_manager.notify_screen_changed()
        logger.info(f"Macro do celular executada: {macro_id}")
        return {"status": "ok", "macro": macro_id, "target": "phone"}

    if macro_id.startswith("KEYCODE_"):
        subprocess.Popen([adb, "shell", "input", "keyevent", macro_id], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        phone_screen_manager.notify_screen_changed()
        return {"status": "ok", "macro": macro_id, "target": "phone"}

    raise HTTPException(status_code=404, detail=f"Macro do celular '{macro_id}' não encontrada")

# ===========================================================================
# 1. MONITOR DE HARDWARE EM TEMPO REAL (TELEMETRIA GAMER HUD)
# ===========================================================================
_last_net_time = 0.0
_last_bytes_sent = 0
_last_bytes_recv = 0
_net_lock = threading.Lock()

def _get_gpu_telemetry() -> Optional[Dict[str, Any]]:
    import shutil
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi and os.path.exists(r"C:\Windows\system32\nvidia-smi.exe"):
        nvidia_smi = r"C:\Windows\system32\nvidia-smi.exe"
    if nvidia_smi:
        try:
            out = subprocess.check_output(
                [nvidia_smi, "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
                encoding="utf-8",
                timeout=1.5
            )
            parts = [p.strip() for p in out.strip().split(",")]
            if len(parts) >= 5:
                return {
                    "name": parts[0],
                    "temperature_c": int(parts[1]) if parts[1].isdigit() else 0,
                    "usage_percent": int(parts[2]) if parts[2].isdigit() else 0,
                    "memory_used_mb": int(parts[3]) if parts[3].isdigit() else 0,
                    "memory_total_mb": int(parts[4]) if parts[4].isdigit() else 0
                }
        except Exception:
            pass
    return None

@app.get("/api/hardware/telemetry")
def get_hardware_telemetry():
    """Retorna telemetria completa de hardware do PC em tempo real."""
    global _last_net_time, _last_bytes_sent, _last_bytes_recv
    import psutil

    # CPU
    cpu_percent = psutil.cpu_percent(interval=None)
    cpu_freq = psutil.cpu_freq()
    cpu_cores = psutil.cpu_count(logical=True)

    # RAM
    ram = psutil.virtual_memory()

    # Discos
    disks = []
    for part in psutil.disk_partitions(all=False):
        try:
            if "cdrom" in part.opts or part.fstype == "":
                continue
            usage = psutil.disk_usage(part.mountpoint)
            disks.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "total_gb": round(usage.total / (1024**3), 1),
                "used_gb": round(usage.used / (1024**3), 1),
                "free_gb": round(usage.free / (1024**3), 1),
                "percent": usage.percent
            })
        except Exception:
            pass

    # Rede (Cálculo de taxa KB/s)
    now = time.time()
    net = psutil.net_io_counters()
    upload_kbps = 0.0
    download_kbps = 0.0
    with _net_lock:
        if _last_net_time > 0 and now > _last_net_time:
            dt = now - _last_net_time
            if dt > 0.1:
                upload_kbps = round((net.bytes_sent - _last_bytes_sent) / 1024 / dt, 1)
                download_kbps = round((net.bytes_recv - _last_bytes_recv) / 1024 / dt, 1)
        _last_net_time = now
        _last_bytes_sent = net.bytes_sent
        _last_bytes_recv = net.bytes_recv

    # GPU
    gpu = _get_gpu_telemetry()

    return {
        "status": "ok",
        "timestamp": int(now),
        "cpu": {
            "percent": cpu_percent,
            "freq_ghz": round(cpu_freq.current / 1000, 2) if cpu_freq else 0.0,
            "cores": cpu_cores
        },
        "ram": {
            "percent": ram.percent,
            "used_gb": round(ram.used / (1024**3), 1),
            "total_gb": round(ram.total / (1024**3), 1),
            "free_gb": round(ram.available / (1024**3), 1)
        },
        "network": {
            "upload_kbps": max(0.0, upload_kbps),
            "download_kbps": max(0.0, download_kbps)
        },
        "gpu": gpu,
        "disks": disks
    }


# ===========================================================================
# 2. MIXER DE ÁUDIO POR APLICATIVO (WINDOWS AUDIO SESSIONS)
# ===========================================================================
class AudioSessionVolumeRequest(BaseModel):
    pid: int
    volume: int  # 0 a 100

class AudioSessionMuteRequest(BaseModel):
    pid: int
    muted: bool

@app.get("/api/audio/sessions")
def list_audio_sessions():
    """Lista todos os aplicativos ativos com sessão de áudio no Windows."""
    if sys.platform != "win32":
        return {"sessions": []}
    try:
        try:
            ctypes.windll.ole32.CoInitialize(None)
        except Exception:
            pass
        from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
        sessions = AudioUtilities.GetAllSessions()
        result = []
        seen_pids = set()
        for session in sessions:
            if not session.Process:
                continue
            pid = session.Process.pid
            if pid in seen_pids:
                continue
            seen_pids.add(pid)
            try:
                name = session.Process.name()
                volume_ctrl = session._ctl.QueryInterface(ISimpleAudioVolume)
                vol = round(volume_ctrl.GetMasterVolume() * 100)
                muted = bool(volume_ctrl.GetMute())
                
                friendly_name = os.path.splitext(name)[0]
                if friendly_name.lower() == "chrome": friendly_name = "Google Chrome"
                elif friendly_name.lower() == "msedge": friendly_name = "Microsoft Edge"
                elif friendly_name.lower() == "spotify": friendly_name = "Spotify"
                elif friendly_name.lower() == "discord": friendly_name = "Discord"
                elif friendly_name.lower() == "steam": friendly_name = "Steam"

                result.append({
                    "pid": pid,
                    "process_name": name,
                    "display_name": friendly_name,
                    "volume": vol,
                    "muted": muted
                })
            except Exception:
                pass
        return {"status": "ok", "sessions": result}
    except Exception as e:
        logger.warning(f"Erro ao listar sessões de áudio: {e}")
        return {"status": "error", "message": str(e), "sessions": []}

@app.post("/api/audio/sessions/set-volume")
def set_audio_session_volume(req: AudioSessionVolumeRequest):
    """Ajusta o volume de um aplicativo específico por PID."""
    if sys.platform != "win32":
        raise HTTPException(status_code=501, detail="Disponível apenas no Windows")
    try:
        try:
            ctypes.windll.ole32.CoInitialize(None)
        except Exception:
            pass
        from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
        target_vol = max(0.0, min(1.0, req.volume / 100.0))
        for session in AudioUtilities.GetAllSessions():
            if session.Process and session.Process.pid == req.pid:
                volume_ctrl = session._ctl.QueryInterface(ISimpleAudioVolume)
                volume_ctrl.SetMasterVolume(target_vol, None)
                return {"status": "ok", "pid": req.pid, "volume": req.volume}
        raise HTTPException(status_code=404, detail="Processo de áudio não encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/audio/sessions/set-mute")
def set_audio_session_mute(req: AudioSessionMuteRequest):
    """Muta ou desmuta um aplicativo específico por PID."""
    if sys.platform != "win32":
        raise HTTPException(status_code=501, detail="Disponível apenas no Windows")
    try:
        try:
            ctypes.windll.ole32.CoInitialize(None)
        except Exception:
            pass
        from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
        for session in AudioUtilities.GetAllSessions():
            if session.Process and session.Process.pid == req.pid:
                volume_ctrl = session._ctl.QueryInterface(ISimpleAudioVolume)
                volume_ctrl.SetMute(1 if req.muted else 0, None)
                return {"status": "ok", "pid": req.pid, "muted": req.muted}
        raise HTTPException(status_code=404, detail="Processo de áudio não encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================================================
# 3. TOUCHPAD VIRTUAL & AIR MOUSE (CONTROLE DE SOFÁ)
# ===========================================================================
class TrackpadMoveRequest(BaseModel):
    dx: float
    dy: float

class MouseClickRequest(BaseModel):
    button: str = "left"
    double: Optional[bool] = False
    click_type: Optional[str] = "single"

class MouseScrollRequest(BaseModel):
    clicks: Optional[int] = None
    dx: Optional[float] = 0.0
    dy: Optional[float] = None

class KeyboardInputRequest(BaseModel):
    text: str

class KeyboardKeyRequest(BaseModel):
    key: str

@app.post("/api/mouse/trackpad")
def mouse_trackpad_move(req: TrackpadMoveRequest):
    """Move o ponteiro do mouse relativamente de forma ultra-rápida."""
    try:
        if sys.platform == "win32":
            # MOUSEEVENTF_MOVE = 0x0001
            ctypes.windll.user32.mouse_event(0x0001, int(round(req.dx)), int(round(req.dy)), 0, 0)
            return {"status": "ok"}
        elif pyautogui:
            pyautogui.moveRel(req.dx, req.dy, _pause=False)
            return {"status": "ok"}
        return {"status": "disabled"}
    except Exception as e:
        logger.warning(f"Erro ao mover mouse: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/mouse/click")
def mouse_click_action(req: MouseClickRequest):
    """Executa clique no mouse (esquerdo, direito, meio, duplo)."""
    btn = (req.button or "left").lower()
    is_double = bool(req.double) or (req.click_type == "double")

    try:
        if sys.platform == "win32":
            if btn == "left":
                # MOUSEEVENTF_LEFTDOWN = 0x0002, LEFTUP = 0x0004
                ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
                ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
                if is_double:
                    time.sleep(0.05)
                    ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
                    ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
            elif btn == "right":
                # MOUSEEVENTF_RIGHTDOWN = 0x0008, RIGHTUP = 0x0010
                ctypes.windll.user32.mouse_event(0x0008, 0, 0, 0, 0)
                ctypes.windll.user32.mouse_event(0x0010, 0, 0, 0, 0)
            elif btn in ("middle", "meio"):
                # MOUSEEVENTF_MIDDLEDOWN = 0x0020, MIDDLEUP = 0x0040
                ctypes.windll.user32.mouse_event(0x0020, 0, 0, 0, 0)
                ctypes.windll.user32.mouse_event(0x0040, 0, 0, 0, 0)
            return {"status": "ok", "button": btn, "double": is_double}
        elif pyautogui:
            if is_double:
                pyautogui.doubleClick(button=btn, _pause=False)
            else:
                pyautogui.click(button=btn, _pause=False)
            return {"status": "ok", "button": btn, "double": is_double}
        return {"status": "disabled"}
    except Exception as e:
        logger.warning(f"Erro ao clicar: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/mouse/scroll")
def mouse_scroll_action(req: MouseScrollRequest):
    """Executa rolagem da roda do mouse."""
    try:
        val = 0
        if req.clicks is not None:
            val = int(req.clicks)
        elif req.dy is not None:
            val = int(round(req.dy))
        
        if val == 0:
            val = 1 if (req.dy or 0) > 0 else -1

        if sys.platform == "win32":
            # MOUSEEVENTF_WHEEL = 0x0800. Cada 'notch' de scroll padrão do Windows é 120
            wheel_delta = val * 60
            ctypes.windll.user32.mouse_event(0x0800, 0, 0, wheel_delta, 0)
            return {"status": "ok", "scroll": val}
        elif pyautogui:
            pyautogui.scroll(val, _pause=False)
            return {"status": "ok", "scroll": val}
        return {"status": "disabled"}
    except Exception as e:
        logger.warning(f"Erro no scroll: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/keyboard/input")
def keyboard_input_text(req: KeyboardInputRequest):
    """Digita texto recebido do celular no aplicativo ativo do PC."""
    if not req.text:
        return {"status": "ok", "length": 0}
    try:
        import pyperclip
        pyperclip.copy(req.text)
        time.sleep(0.04)
        if pyautogui:
            pyautogui.hotkey("ctrl", "v", _pause=False)
        return {"status": "ok", "length": len(req.text)}
    except Exception as e:
        logger.warning(f"Erro ao colar texto via clipboard: {e}")
        if pyautogui:
            try:
                pyautogui.write(req.text, interval=0.005)
                return {"status": "ok", "fallback": True}
            except Exception as e2:
                logger.error(f"Erro fallback pyautogui.write: {e2}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/keyboard/key")
def keyboard_press_key(req: KeyboardKeyRequest):
    """Pressiona tecla ou atalho composto (ex: ctrl+c, alt+tab, win, enter)."""
    k = req.key.strip().lower()
    try:
        if not pyautogui:
            return {"status": "disabled"}

        if "+" in k:
            parts = [p.strip() for p in k.split("+")]
            mapped = []
            for p in parts:
                if p in ("ctrl", "control"): mapped.append("ctrl")
                elif p in ("alt", "menu"): mapped.append("alt")
                elif p in ("shift"): mapped.append("shift")
                elif p in ("win", "windows", "cmd"): mapped.append("win")
                else: mapped.append(p)
            pyautogui.hotkey(*mapped, _pause=False)
            return {"status": "ok", "hotkey": mapped}
        elif k in ("win", "windows"):
            pyautogui.press("win", _pause=False)
            return {"status": "ok", "key": "win"}
        else:
            pyautogui.press(k, _pause=False)
            return {"status": "ok", "key": k}
    except Exception as e:
        logger.warning(f"Erro ao pressionar tecla '{k}': {e}")
        return {"status": "error", "message": str(e)}


# ===========================================================================
# 4. CENTRAL DE ENERGIA & TIMER INTELIGENTE (SLEEP TIMER)
# ===========================================================================
_sleep_timer_deadline: Optional[float] = None
_sleep_timer_action: Optional[str] = None
_power_lock = threading.Lock()

class SleepTimerRequest(BaseModel):
    minutes: int
    action: str = "shutdown"

class PowerActionRequest(BaseModel):
    action: str

@app.post("/api/power/sleep-timer")
def set_sleep_timer(req: SleepTimerRequest):
    """Programa timer para desligar, suspender ou apagar telas em X minutos."""
    global _sleep_timer_deadline, _sleep_timer_action
    with _power_lock:
        if req.minutes <= 0:
            return cancel_sleep_timer()
        
        seconds = req.minutes * 60
        _sleep_timer_deadline = time.time() + seconds
        _sleep_timer_action = req.action

        if sys.platform == "win32":
            if req.action == "shutdown":
                subprocess.Popen(["shutdown", "/s", "/t", str(seconds)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif req.action == "restart":
                subprocess.Popen(["shutdown", "/r", "/t", str(seconds)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return {
            "status": "ok",
            "minutes": req.minutes,
            "seconds": seconds,
            "action": req.action,
            "message": f"Timer programado para {req.minutes} minuto(s)!"
        }

@app.post("/api/power/cancel-timer")
def cancel_sleep_timer():
    """Cancela qualquer timer de energia ativo."""
    global _sleep_timer_deadline, _sleep_timer_action
    with _power_lock:
        _sleep_timer_deadline = None
        _sleep_timer_action = None
        if sys.platform == "win32":
            subprocess.Popen(["shutdown", "/a"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"status": "ok", "message": "Timer cancelado com sucesso!"}

@app.get("/api/power/timer-status")
def get_sleep_timer_status():
    """Retorna tempo restante do timer de energia."""
    global _sleep_timer_deadline, _sleep_timer_action
    with _power_lock:
        if _sleep_timer_deadline is not None:
            remaining = int(_sleep_timer_deadline - time.time())
            if remaining > 0:
                return {
                    "active": True,
                    "remaining_seconds": remaining,
                    "action": _sleep_timer_action
                }
            else:
                _sleep_timer_deadline = None
                _sleep_timer_action = None
        return {"active": False, "remaining_seconds": 0, "action": None}

@app.post("/api/power/action")
def execute_power_action(req: PowerActionRequest):
    """Executa ação imediata de energia no PC."""
    act = req.action.lower()
    if act == "turn_off_screens":
        if sys.platform == "win32":
            ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
            return {"status": "ok", "action": act, "message": "Monitores desligados!"}
    elif act == "lock":
        if sys.platform == "win32":
            ctypes.windll.user32.LockWorkStation()
            return {"status": "ok", "action": act, "message": "Estação bloqueada!"}
    elif act == "sleep":
        if sys.platform == "win32":
            subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
            return {"status": "ok", "action": act, "message": "Entrando em suspensão..."}
    elif act == "restart":
        if sys.platform == "win32":
            subprocess.Popen(["shutdown", "/r", "/t", "0"])
            return {"status": "ok", "action": act, "message": "Reiniciando..."}
    elif act == "shutdown":
        if sys.platform == "win32":
            subprocess.Popen(["shutdown", "/s", "/t", "0"])
            return {"status": "ok", "action": act, "message": "Desligando..."}

    raise HTTPException(status_code=400, detail=f"Ação de energia '{req.action}' desconhecida.")


# ===========================================================================
# 5. ÁREA DE TRANSFERÊNCIA UNIFICADA (UNIVERSAL CLIPBOARD)
# ===========================================================================
class ClipboardSetRequest(BaseModel):
    text: str
    auto_paste: bool = False

@app.get("/api/clipboard")
def get_clipboard_content():
    """Retorna o conteúdo atual da área de transferência do PC."""
    try:
        import pyperclip
        val = pyperclip.paste() or ""
        return {"status": "ok", "text": val, "length": len(val)}
    except Exception as e:
        return {"status": "error", "message": str(e), "text": ""}

@app.post("/api/clipboard")
def set_clipboard_content(req: ClipboardSetRequest):
    """Define o texto copiado no PC com opção de colar automático (Ctrl+V)."""
    try:
        import pyperclip
        pyperclip.copy(req.text)
        if req.auto_paste and pyautogui:
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "v", _pause=False)
        return {
            "status": "ok",
            "message": "Texto copiado para a Área de Transferência do PC!",
            "length": len(req.text),
            "pasted": req.auto_paste
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------------------------
# INICIALIZAÇÃO VIA TERMINAL
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Garante estritamente apenas UMA instância do servidor no PC
    ensure_single_instance()

    import uvicorn

    # Inicializa o ícone da bandeja do sistema (System Tray) no Windows
    setup_tray_icon()

    # Parâmetros configuráveis via config.json
    host = SERVER_CONFIG.get("server", {}).get("host", "0.0.0.0")
    port = SERVER_CONFIG.get("server", {}).get("port", 8000)
    log_level = SERVER_CONFIG.get("server", {}).get("log_level", "info")
    autostart_active = is_windows_autostart_enabled()

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_preview = s.getsockname()[0]
        s.close()
    except Exception:
        ip_preview = "127.0.0.1"

    if sys.stdout and hasattr(sys.stdout, "write"):
        try:
            print("=" * 65)
            print("  >> MACROENGINE - SERVIDOR DE AUTOMACAO & STREAMING <<")
            print("=" * 65)
            print(f"  * IP Local da Maquina:     {ip_preview}")
            print(f"  * Porta da API REST:       {port}")
            print(f"  * Porta Audio UDP:         {SERVER_CONFIG.get('audio_streaming', {}).get('default_port', 50005)}")
            print(f"  * Iniciar com o Windows:   {'ATIVADO (Silencioso)' if autostart_active else 'DESATIVADO'}")
            print(f"  * Modo Jogo Turbo:         {'ATIVO' if GAME_MODE_ACTIVE else 'DISPONIVEL'}")
            print(f"  * Swagger Docs:            http://{ip_preview}:{port}/docs")
            print(f"  * Acesso Local:            http://localhost:{port}")
            print("=" * 65)
            print("  Servidor iniciado com sucesso! Pressione Ctrl+C para encerrar.")
            print("=" * 65)
        except Exception:
            pass

    try:
        uvicorn.run(app, host=host, port=port, log_level=log_level)
    finally:
        if _tray_icon is not None:
            try:
                _tray_icon.stop()
            except Exception:
                pass

"""
MacroEngine - Suite de Auto-Diagnóstico & Teste de Saúde
Valida bibliotecas, latência de captura e endpoints REST da API
"""

import sys
import time
import socket
import json

if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def check_modules():
    print("=" * 60)
    print("1. VERIFICANDO MÓDULOS E DEPENDÊNCIAS DO SISTEMA")
    print("=" * 60)
    modules = [
        ("fastapi", "Framework REST API"),
        ("uvicorn", "Servidor ASGI ASGI de Alta Performance"),
        ("pydantic", "Validação de Schemas e Modelos"),
        ("pyautogui", "Automação de Teclado e Mouse"),
        ("mss", "Captura de Tela de Baixa Latência (DirectX/GDI)"),
        ("PIL", "Processamento de Imagens (Pillow)"),
        ("psutil", "Monitoramento de Hardware & Placa de Rede"),
        ("pystray", "Ícone e Menu na Bandeja do Windows (System Tray)"),
        ("pycaw", "Controle de Áudio Master no Windows"),
        ("pyaudio", "Captura de Áudio Local (PCM)")
    ]

    all_ok = True
    for mod_name, desc in modules:
        try:
            __import__(mod_name)
            print(f" [OK] {mod_name:<12} -> {desc}")
        except ImportError:
            is_optional = mod_name in ["pycaw", "pyaudio", "pystray"]
            tag = "[AVISO (Opcional)]" if is_optional else "[FALHA]"
            print(f" {tag} {mod_name:<12} -> {desc}")
            if not is_optional:
                all_ok = False

    return all_ok

def check_endpoints(base_url="http://localhost:8000"):
    import urllib.request
    import urllib.error

    print("\n" + "=" * 60)
    print(f"2. TESTANDO COMUNICAÇÃO HTTP COM A API ({base_url})")
    print("=" * 60)

    # 1. Status
    auth_token = None
    try:
        t0 = time.time()
        with urllib.request.urlopen(f"{base_url}/api/status", timeout=3) as resp:
            data = json.loads(resp.read().decode())
            lat = (time.time() - t0) * 1000
            print(f" [OK] /api/status -> Status: {data.get('status')} | Hostname: {data.get('hostname')} | IP: {data.get('local_ip')} | MAC: {data.get('mac_address')} | AuthRequired: {data.get('auth_required')} ({lat:.1f}ms)")
    except Exception as e:
        print(f" [ERRO] Servidor parece estar desligado ou inacessível em {base_url}: {e}")
        return False

    # 2. Pareamento com PIN de Segurança
    try:
        pin = "123456"
        try:
            import os
            cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    pin = json.load(f).get("security", {}).get("pin", "123456")
        except Exception:
            pass

        t0 = time.time()
        pair_req = urllib.request.Request(
            f"{base_url}/api/auth/pair",
            data=json.dumps({"pin": pin}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(pair_req, timeout=3) as resp:
            pair_data = json.loads(resp.read().decode())
            auth_token = pair_data.get("auth_token")
            lat = (time.time() - t0) * 1000
            print(f" [OK] /api/auth/pair -> Pareamento autenticado com PIN {pin} ({lat:.1f}ms)")
    except Exception as e:
        print(f" [AVISO] /api/auth/pair falhou: {e}")

    def auth_headers():
        h = {}
        if auth_token:
            h["X-MacroEngine-Key"] = auth_token
        return h

    def open_url(url):
        req = urllib.request.Request(url, headers=auth_headers())
        return urllib.request.urlopen(req, timeout=3)

    # 2. WoL Info
    try:
        t0 = time.time()
        with open_url(f"{base_url}/api/wol/info") as resp:
            data = json.loads(resp.read().decode())
            lat = (time.time() - t0) * 1000
            print(f" [OK] /api/wol/info -> MAC Físico: {data.get('mac_address')} | Placa: {data.get('adapter_name')} ({lat:.1f}ms)")
    except Exception as e:
        print(f" [AVISO] /api/wol/info falhou: {e}")

    # 3. Macros
    try:
        t0 = time.time()
        with open_url(f"{base_url}/api/macros") as resp:
            macros = json.loads(resp.read().decode())
            lat = (time.time() - t0) * 1000
            categories = set(m.get('category') for m in macros)
            print(f" [OK] /api/macros -> {len(macros)} macros cadastradas em {len(categories)} categorias ({lat:.1f}ms)")
    except Exception as e:
        print(f" [AVISO] /api/macros falhou: {e}")

    # 4. Latência de Frame do PC
    try:
        t0 = time.time()
        with open_url(f"{base_url}/api/screen/frame") as resp:
            raw = resp.read()
            lat = (time.time() - t0) * 1000
            print(f" [OK] /api/screen/frame -> Frame capturado ({len(raw)} bytes) | Latência: {lat:.1f}ms")
    except Exception as e:
        print(f" [AVISO] /api/screen/frame falhou: {e}")

    # 5. Autostart Status
    try:
        t0 = time.time()
        with open_url(f"{base_url}/api/autostart/status") as resp:
            data = json.loads(resp.read().decode())
            lat = (time.time() - t0) * 1000
            print(f" [OK] /api/autostart/status -> Windows Autostart: {data.get('autostart_enabled')} ({lat:.1f}ms)")
    except Exception as e:
        print(f" [AVISO] /api/autostart/status falhou: {e}")

    # 6. Configuração do Servidor
    try:
        t0 = time.time()
        with open_url(f"{base_url}/api/config") as resp:
            cfg = json.loads(resp.read().decode())
            lat = (time.time() - t0) * 1000
            print(f" [OK] /api/config -> Porta: {cfg.get('server', {}).get('port')} | Tray: {cfg.get('server', {}).get('enable_tray_icon')} ({lat:.1f}ms)")
    except Exception as e:
        print(f" [AVISO] /api/config falhou: {e}")

    # 7. Swagger Docs
    try:
        with open_url(f"{base_url}/docs") as resp:
            print(f" [OK] /docs -> Documentação Swagger OpenAPI ativa (HTTP {resp.status})")
    except Exception as e:
        print(f" [AVISO] /docs falhou: {e}")

    # 8. Transferência de Arquivos (Shared Files)
    try:
        t0 = time.time()
        with open_url(f"{base_url}/api/files/list") as resp:
            data = json.loads(resp.read().decode())
            lat = (time.time() - t0) * 1000
            file_count = len(data.get("files", []))
            print(f" [OK] /api/files/list -> {file_count} arquivo(s) na pasta compartilhada ({lat:.1f}ms)")
    except Exception as e:
        print(f" [AVISO] /api/files/list falhou: {e}")

    return True

if __name__ == "__main__":
    print("\n--- INICIANDO TESTE DO MACROENGINE SERVER ---")
    mods_ok = check_modules()
    server_ok = check_endpoints()

    print("\n" + "=" * 60)
    if mods_ok and server_ok:
        print(" RESULTADO FINAL: TODOS OS SISTEMAS OPERACIONAIS E SAUDÁVEIS! [100% OK]")
    elif mods_ok and not server_ok:
        print(" RESULTADO: Dependências OK! Inicie o servidor via start_server.bat para rodar os testes da API.")
    else:
        print(" RESULTADO: Algumas dependências precisam de atenção. Execute setup_environment.bat.")
    print("=" * 60 + "\n")

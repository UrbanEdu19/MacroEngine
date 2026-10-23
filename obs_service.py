"""
Módulo de Integração com OBS Studio (WebSocket v5)
Permite alternar cenas, controlar lives/gravações e mutar microfone diretamente do MacroEngine.
"""

import json
import logging
import threading
import time
from typing import Dict, Any, List, Optional
import websocket

logger = logging.getLogger("MacroEngine.OBS")

class ObsStudioManager:
    def __init__(self, host: str = "localhost", port: int = 4455, password: str = ""):
        self.host = host
        self.port = port
        self.password = password
        self.is_connected = False
        self.is_streaming = False
        self.is_recording = False
        self.current_scene = ""
        self.scenes: List[str] = []
        self.mic_muted = False
        self._ws: Optional[websocket.WebSocket] = None
        self._lock = threading.Lock()

    def connect(self) -> bool:
        """Tenta conectar ao servidor WebSocket v5 do OBS Studio."""
        with self._lock:
            try:
                if self._ws:
                    try:
                        self._ws.close()
                    except Exception:
                        pass
                ws_url = f"ws://{self.host}:{self.port}"
                self._ws = websocket.create_connection(ws_url, timeout=3.0)
                
                # Handshake OBS WebSocket v5 (OpCode 0 Hello -> OpCode 1 Identify)
                hello_raw = self._ws.recv()
                hello_data = json.loads(hello_raw)
                if hello_data.get("op") == 0:
                    identify_payload = {
                        "op": 1,
                        "d": {
                            "rpcVersion": 1,
                            "eventSubscriptions": 33
                        }
                    }
                    self._ws.send(json.dumps(identify_payload))
                    resp = json.loads(self._ws.recv())
                    if resp.get("op") == 2: # Identified
                        self.is_connected = True
                        logger.info("Conectado com sucesso ao OBS Studio WebSocket v5!")
                        self._refresh_status()
                        return True
                self.is_connected = False
                return False
            except Exception as e:
                self.is_connected = False
                logger.debug(f"OBS Studio não está aberto ou WebSocket desativado: {e}")
                return False

    def _send_request(self, request_type: str, request_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Envia uma requisição OpCode 6 para o OBS WebSocket v5."""
        if not self.is_connected or not self._ws:
            if not self.connect():
                return None

        req_id = f"req_{int(time.time()*1000)}"
        msg = {
            "op": 6,
            "d": {
                "requestType": request_type,
                "requestId": req_id,
                "requestData": request_data or {}
            }
        }
        with self._lock:
            try:
                self._ws.send(json.dumps(msg))
                raw = self._ws.recv()
                data = json.loads(raw)
                if data.get("op") == 7 and data.get("d", {}).get("requestStatus", {}).get("result"):
                    return data.get("d", {}).get("responseData", {})
                return None
            except Exception as e:
                logger.debug(f"Falha na comunicação com OBS: {e}")
                self.is_connected = False
                return None

    def _refresh_status(self):
        """Atualiza a lista de cenas e status de transmissão/gravação."""
        # 1. Cenas
        scenes_data = self._send_request("GetSceneList")
        if scenes_data:
            self.current_scene = scenes_data.get("currentProgramSceneName", "")
            raw_scenes = scenes_data.get("scenes", [])
            self.scenes = [s.get("sceneName") for s in raw_scenes if "sceneName" in s]

        # 2. Status de Stream
        stream_data = self._send_request("GetStreamStatus")
        if stream_data:
            self.is_streaming = stream_data.get("outputActive", False)

        # 3. Status de Gravação
        record_data = self._send_request("GetRecordStatus")
        if record_data:
            self.is_recording = record_data.get("outputActive", False)

    def get_status(self) -> Dict[str, Any]:
        """Retorna o estado consolidado da integração com o OBS Studio."""
        if not self.is_connected:
            self.connect()
        else:
            self._refresh_status()

        return {
            "connected": self.is_connected,
            "host": f"{self.host}:{self.port}",
            "current_scene": self.current_scene,
            "scenes": self.scenes,
            "is_streaming": self.is_streaming,
            "is_recording": self.is_recording,
            "mic_muted": self.mic_muted
        }

    def set_current_scene(self, scene_name: str) -> bool:
        """Altera a cena atual de transmissão no OBS."""
        res = self._send_request("SetCurrentProgramScene", {"sceneName": scene_name})
        if res is not None:
            self.current_scene = scene_name
            return True
        return False

    def toggle_stream(self) -> bool:
        """Inicia ou para a transmissão ao vivo."""
        res = self._send_request("ToggleStream")
        if res is not None:
            self.is_streaming = res.get("outputActive", not self.is_streaming)
            return True
        return False

    def toggle_record(self) -> bool:
        """Inicia ou para a gravação local."""
        res = self._send_request("ToggleRecord")
        if res is not None:
            self.is_recording = res.get("outputActive", not self.is_recording)
            return True
        return False

    def toggle_input_mute(self, input_name: str = "Mic/Aux") -> bool:
        """Alterna o mute de uma entrada de áudio (ex: microfone)."""
        res = self._send_request("ToggleInputMute", {"inputName": input_name})
        if res is not None:
            self.mic_muted = res.get("inputMuted", not self.mic_muted)
            return True
        return False

# Instância Global do OBS Manager
obs_manager = ObsStudioManager()

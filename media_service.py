"""
Módulo de Integração com o Windows Media Session (Universal Media Controller)
Captura título, artista, álbum, duração, posição e capa do álbum de qualquer reprodutor
(Spotify, YouTube no Chrome/Edge, VLC, Apple Music, Deezer, etc.)
"""

import sys
import logging
import base64
from typing import Optional, Dict, Any

logger = logging.getLogger("MacroEngine.Media")

_last_media_info: Dict[str, Any] = {
    "has_media": False,
    "title": "",
    "artist": "",
    "album": "",
    "status": "stopped",
    "position_seconds": 0,
    "duration_seconds": 0,
    "thumbnail_base64": "",
    "app_id": ""
}
_raw_thumbnail_bytes: Optional[bytes] = None

async def get_system_media_info() -> Dict[str, Any]:
    """Obtém as informações da faixa atual tocando no Windows em tempo real."""
    global _last_media_info, _raw_thumbnail_bytes
    if sys.platform != "win32":
        return {"has_media": False, "message": "Apenas suportado no Windows"}

    try:
        from winsdk.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionManager as MediaManager,
            GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus
        )
        from winsdk.windows.storage.streams import DataReader

        manager = await MediaManager.request_async()
        session = manager.get_current_session()
        if not session:
            _last_media_info["has_media"] = False
            _last_media_info["status"] = "stopped"
            return _last_media_info

        info = await session.try_get_media_properties_async()
        timeline = session.get_timeline_properties()
        playback = session.get_playback_info()

        status_str = "unknown"
        if playback:
            s = playback.playback_status
            if s == PlaybackStatus.PLAYING:
                status_str = "playing"
            elif s == PlaybackStatus.PAUSED:
                status_str = "paused"
            elif s == PlaybackStatus.STOPPED:
                status_str = "stopped"

        # Thumbnail da capa
        thumb_b64 = _last_media_info.get("thumbnail_base64", "")
        if info.thumbnail:
            try:
                stream = await info.thumbnail.open_read_async()
                size = stream.size
                if size > 0:
                    reader = DataReader(stream.get_input_stream_at(0))
                    await reader.load_async(size)
                    bytes_arr = bytearray(size)
                    reader.read_bytes(bytes_arr)
                    _raw_thumbnail_bytes = bytes(bytes_arr)
                    thumb_b64 = base64.b64encode(_raw_thumbnail_bytes).decode("ascii")
            except Exception as te:
                logger.debug(f"Falha ao ler thumbnail da mídia: {te}")

        pos_sec = timeline.position.total_seconds() if timeline and timeline.position else 0.0
        end_sec = timeline.end_time.total_seconds() if timeline and timeline.end_time else 0.0

        title = info.title.strip() if info.title else ""
        artist = info.artist.strip() if info.artist else ""
        album = info.album_title.strip() if info.album_title else ""
        app_id = session.source_app_user_model_id or ""

        _last_media_info = {
            "has_media": bool(title or artist),
            "title": title or "Sem Título",
            "artist": artist or "Artista Desconhecido",
            "album": album,
            "status": status_str,
            "position_seconds": int(pos_sec),
            "duration_seconds": int(end_sec),
            "thumbnail_base64": thumb_b64,
            "app_id": app_id
        }
        return _last_media_info
    except Exception as e:
        logger.debug(f"Erro ao obter informações de mídia: {e}")
        return _last_media_info

async def control_system_media(action: str, position_seconds: Optional[int] = None) -> bool:
    """Envia comandos de controle de reprodução para o player ativo do Windows."""
    if sys.platform != "win32":
        return False
    try:
        from winsdk.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionManager as MediaManager
        )
        manager = await MediaManager.request_async()
        session = manager.get_current_session()
        if not session:
            return False

        action_clean = action.lower().strip()
        if action_clean == "play":
            return await session.try_play_async()
        elif action_clean == "pause":
            return await session.try_pause_async()
        elif action_clean in ("toggle", "play_pause"):
            return await session.try_toggle_play_pause_async()
        elif action_clean in ("next", "skip_next"):
            return await session.try_skip_next_async()
        elif action_clean in ("previous", "prev", "skip_previous"):
            return await session.try_skip_previous_async()
        elif action_clean == "stop":
            return await session.try_stop_async()
        elif action_clean == "seek" and position_seconds is not None:
            # TimeSpan no Windows Runtime é em centenas de nanosegundos (1s = 10_000_000 ticks)
            import datetime
            time_span = datetime.timedelta(seconds=position_seconds)
            return await session.try_change_playback_position_async(time_span.total_seconds() * 10_000_000)
        return False
    except Exception as e:
        logger.error(f"Erro ao controlar mídia do Windows: {e}")
        return False

def get_current_thumbnail_bytes() -> Optional[bytes]:
    """Retorna os bytes brutos da imagem de capa para servir via HTTP."""
    global _raw_thumbnail_bytes
    return _raw_thumbnail_bytes

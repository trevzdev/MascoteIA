"""
Motor de Voz Avançado com 6 Opções Distintas (3 Masculinas e 3 Femininas)
Utiliza síntese neural realista via edge-tts com reprodução assíncrona PyQt6 (QMediaPlayer),
com fallback automático para SAPI do Windows.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from desktop_ui.settings_manager import SettingsManager

# 6 Opções de Vozes (Exatamente 3 Masculinas e 3 Femininas)
VOICE_PROFILES: Dict[str, Dict[str, Any]] = {
    "male_1": {
        "id": "male_1",
        "gender": "male",
        "name": "Antonio (Natural)",
        "voice_tag": "pt-BR-AntonioNeural",
        "rate": "+0%",
        "pitch": "+0Hz",
        "desc": "Homem maduro, tom firme, confiável e natural.",
        "description": "Voz masculina madura, firme, confiável e natural."
    },
    "male_2": {
        "id": "male_2",
        "gender": "male",
        "name": "Fabio (Grave & Enérgico)",
        "voice_tag": "pt-BR-FabioNeural",
        "rate": "+8%",
        "pitch": "+5Hz",
        "desc": "Tom jovem, ágil, entusiasta e dinâmico.",
        "description": "Tom jovem, ágil, entusiasta e vibrante."
    },
    "male_3": {
        "id": "male_3",
        "gender": "male",
        "name": "Cyborg (Sintético Robótico)",
        "voice_tag": "pt-BR-AntonioNeural",
        "rate": "-4%",
        "pitch": "-22Hz",
        "desc": "Grave mecânico, cadência robótica futurista.",
        "description": "Grave mecânico, cadência robótica futurista."
    },
    "female_1": {
        "id": "female_1",
        "gender": "female",
        "name": "Francisca (Acolhedora)",
        "voice_tag": "pt-BR-FranciscaNeural",
        "rate": "+0%",
        "pitch": "+0Hz",
        "desc": "Tom sereno, calmo, claro e aveludado.",
        "description": "Tom calmo, maternal, claro e aveludado."
    },
    "female_2": {
        "id": "female_2",
        "gender": "female",
        "name": "Thalita (Jovem Expressiva)",
        "voice_tag": "pt-BR-ThalitaNeural",
        "rate": "+7%",
        "pitch": "+6Hz",
        "desc": "Voz jovem descontraída, moderna e comunicativa.",
        "description": "Voz jovem descontraída, moderna e comunicativa."
    },
    "female_3": {
        "id": "female_3",
        "gender": "female",
        "name": "A.I. 9000 (Cibernética Futurista)",
        "voice_tag": "pt-BR-BrendaNeural",
        "rate": "+10%",
        "pitch": "-12Hz",
        "desc": "Cadência computacional ultraprecisa com timbre digital.",
        "description": "Cadência computacional ultraprecisa com timbre digital."
    }
}

VOICES = VOICE_PROFILES


class VoiceSynthesizerWorker(QObject):
    """Gera o arquivo de áudio neural em background thread."""
    audio_generated = pyqtSignal(str)
    failed = pyqtSignal(str)

    @pyqtSlot(str, str)
    def synthesize(self, text: str, voice_id: str):
        if not text:
            self.failed.emit("Texto vazio")
            return

        # Busca pelo ID chave ou pelo voice_tag
        profile = VOICE_PROFILES.get(voice_id)
        if not profile:
            for p in VOICE_PROFILES.values():
                if p["voice_tag"] == voice_id:
                    profile = p
                    break
        if not profile:
            profile = VOICE_PROFILES["male_1"]

        voice_tag = profile["voice_tag"]
        rate = profile["rate"]
        pitch = profile["pitch"]

        # Cache local por SHA256 do texto + parâmetros da voz
        import hashlib
        cache_key = hashlib.sha256(f"{text.strip()}_{voice_tag}_{rate}_{pitch}".encode("utf-8")).hexdigest()[:24]
        cache_dir = Path(tempfile.gettempdir()) / "mascote_tts_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        output_file = str(cache_dir / f"tts_{cache_key}.mp3")

        # Se já existe no cache, emite imediatamente (< 1ms)
        if os.path.exists(output_file) and os.path.getsize(output_file) > 100:
            self.audio_generated.emit(output_file)
            return

        try:
            import edge_tts

            async def _run():
                communicate = edge_tts.Communicate(text, voice_tag, rate=rate, pitch=pitch)
                await communicate.save(output_file)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_run())
            loop.close()

            if os.path.exists(output_file) and os.path.getsize(output_file) > 100:
                self.audio_generated.emit(output_file)
            else:
                self.failed.emit("Arquivo de áudio não gerado")
        except Exception as e:
            self.failed.emit(str(e))


class TTSEngine(QObject):
    """Controlador principal de Text-to-Speech com QMediaPlayer."""

    VOICES = VOICE_PROFILES
    VOICE_PROFILES = VOICE_PROFILES

    speech_started = pyqtSignal(str)
    speech_finished = pyqtSignal()
    synthesize_requested = pyqtSignal(str, str)

    def __init__(self, parent=None, voice_id: Optional[str] = None):
        super().__init__(parent)
        self.is_muted = False
        self.current_voice_id = voice_id or SettingsManager.get_voice_id()

        # Configura Player de Áudio do PyQt6
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)

        # Worker de Síntese
        self.worker_thread = QThread()
        self.worker = VoiceSynthesizerWorker()
        self.worker.moveToThread(self.worker_thread)

        self.synthesize_requested.connect(self.worker.synthesize)
        self.worker.audio_generated.connect(self._play_audio)
        self.worker.failed.connect(self._on_synthesis_failed)

        self.worker_thread.start()
        self._current_text = ""

    def set_voice(self, voice_id: str):
        """Define o ID da voz ativa."""
        self.current_voice_id = voice_id

    @classmethod
    def get_voice_profiles(cls) -> List[Dict[str, Any]]:
        return list(VOICE_PROFILES.values())

    @classmethod
    def get_profile(cls, voice_id: str) -> Dict[str, Any]:
        return VOICE_PROFILES.get(voice_id, VOICE_PROFILES["male_1"])

    def prewarm(self, text: str, voice_id: Optional[str] = None):
        """Pré-sintetiza em background para deixar o áudio pronto no cache local sem tocar."""
        if not text or not text.strip():
            return
        v_id = voice_id or self.current_voice_id or SettingsManager.get_voice_id()

        import threading
        def _bg():
            profile = VOICE_PROFILES.get(v_id)
            if not profile:
                for p in VOICE_PROFILES.values():
                    if p["voice_tag"] == v_id:
                        profile = p
                        break
            if not profile:
                profile = VOICE_PROFILES["male_1"]

            import hashlib, edge_tts
            cache_key = hashlib.sha256(f"{text.strip()}_{profile['voice_tag']}_{profile['rate']}_{profile['pitch']}".encode("utf-8")).hexdigest()[:24]
            cache_dir = Path(tempfile.gettempdir()) / "mascote_tts_cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            cached_file = cache_dir / f"tts_{cache_key}.mp3"
            if not cached_file.exists() or cached_file.stat().st_size <= 100:
                try:
                    async def _run():
                        comm = edge_tts.Communicate(text, profile['voice_tag'], rate=profile['rate'], pitch=profile['pitch'])
                        await comm.save(str(cached_file))
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(_run())
                    loop.close()
                except Exception:
                    pass

        threading.Thread(target=_bg, daemon=True).start()

    def speak(self, text: str, voice_id: Optional[str] = None):
        """Dispara a síntese de fala e reprodução."""
        if self.is_muted or not text:
            self.speech_finished.emit()
            return

        self._current_text = text
        v_id = voice_id or self.current_voice_id or SettingsManager.get_voice_id()
        self.synthesize_requested.emit(text, v_id)

    @pyqtSlot(str)
    def _play_audio(self, audio_path: str):
        self.speech_started.emit(self._current_text)
        self.player.setSource(QUrl.fromLocalFile(audio_path))
        self.player.play()

    @pyqtSlot(str)
    def _on_synthesis_failed(self, error: str):
        # Fallback para Windows SAPI se edge-tts falhar
        try:
            import win32com.client
            sp = win32com.client.Dispatch("SAPI.SpVoice")
            self.speech_started.emit(self._current_text)
            sp.Speak(self._current_text, 1)  # 1 = Async
        except Exception:
            pass
        self.speech_finished.emit()

    def _on_playback_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.StoppedState:
            self.speech_finished.emit()

    def toggle_mute(self) -> bool:
        self.is_muted = not self.is_muted
        if self.is_muted and self.player.isPlaying():
            self.player.stop()
        return self.is_muted

    def shutdown(self):
        if self.player.isPlaying():
            self.player.stop()
        if self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait(1000)

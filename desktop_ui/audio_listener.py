"""
Módulo de Captura e Reconhecimento de Voz via Microfone
Inclui:
1. Gravação de comandos de voz sob demanda com monitoramento de amplitude RMS.
2. Escuta contínua em segundo plano de Wake Word (ex: "Ei Laranja", "Eai Laranja").
Sem dependência do PyAudio (utiliza sounddevice + speech_recognition).
"""

import io
import re
import time
import wave
import numpy as np
import sounddevice as sd
import speech_recognition as sr
from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot


class AudioRecorderWorker(QObject):
    """Worker que grava e transcreve o áudio de comando do microfone em segundo plano."""
    listening_started = pyqtSignal()
    listening_stopped = pyqtSignal()
    amplitude_updated = pyqtSignal(float)
    transcription_success = pyqtSignal(str)
    transcription_error = pyqtSignal(str)

    def __init__(self, sample_rate: int = 16000, duration: float = 5.0):
        super().__init__()
        self.sample_rate = sample_rate
        self.duration = duration
        self.is_recording = False
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True

    @pyqtSlot()
    def start_listening(self):
        """Inicia a gravação com monitoramento de amplitude e transcrição."""
        if self.is_recording:
            return

        self.is_recording = True
        self.listening_started.emit()

        frames = []
        block_size = int(self.sample_rate * 0.1)  # 100ms
        total_blocks = int(self.duration / 0.1)

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                blocksize=block_size,
            ) as stream:
                for _ in range(total_blocks):
                    if not self.is_recording:
                        break
                    data, _ = stream.read(block_size)
                    frames.append(data)

                    # Calcula amplitude RMS para animar o mascote
                    data_float = data.astype(np.float32)
                    rms = np.sqrt(np.mean(data_float ** 2))
                    normalized = min(1.0, float(rms / 4000.0))
                    self.amplitude_updated.emit(normalized)

            self.is_recording = False
            self.listening_stopped.emit()

            if not frames:
                self.transcription_error.emit("Nenhum áudio gravado.")
                return

            audio_data = np.concatenate(frames, axis=0)
            wav_io = io.BytesIO()
            with wave.open(wav_io, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_data.tobytes())
            wav_io.seek(0)

            with sr.AudioFile(wav_io) as source:
                audio = self.recognizer.record(source)

            try:
                text = self.recognizer.recognize_google(audio, language="pt-BR")
                self.transcription_success.emit(text)
            except sr.UnknownValueError:
                self.transcription_error.emit("Não entendi o que você disse. Pode repetir?")
            except sr.RequestError as e:
                self.transcription_error.emit(f"Erro de conexão no reconhecimento de voz: {e}")

        except Exception as e:
            self.is_recording = False
            self.listening_stopped.emit()
            self.transcription_error.emit(f"Falha ao acessar o microfone: {str(e)}")

    @pyqtSlot()
    def stop_listening(self):
        """Interrompe a gravação antecipadamente."""
        self.is_recording = False


class WakeWordWorker(QObject):
    """Worker que monitora áudio em segundo plano aguardando frase de ativação."""
    wake_word_detected = pyqtSignal(str)

    def __init__(self, robot_name: str = "Laranja", sample_rate: int = 16000):
        super().__init__()
        self.robot_name = robot_name
        self.sample_rate = sample_rate
        self.is_running = False
        self.is_paused = False  # Pausa enquanto o usuário está falando um comando
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 400

    def set_robot_name(self, name: str):
        self.robot_name = name.strip() or "Laranja"

    def pause_wake_word(self):
        self.is_paused = True

    def resume_wake_word(self):
        self.is_paused = False

    @pyqtSlot()
    def run_loop(self):
        """Loop contínuo de escuta em baixa latência."""
        self.is_running = True
        chunk_seconds = 2.5
        block_size = int(self.sample_rate * 0.2)
        blocks_per_chunk = int(chunk_seconds / 0.2)

        while self.is_running:
            if self.is_paused:
                time.sleep(0.3)
                continue

            try:
                frames = []
                has_sound = False

                with sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype="int16",
                    blocksize=block_size,
                ) as stream:
                    for _ in range(blocks_per_chunk):
                        if not self.is_running or self.is_paused:
                            break
                        data, _ = stream.read(block_size)
                        frames.append(data)

                        # Detecção de voz (VAD simples por RMS)
                        data_float = data.astype(np.float32)
                        rms = np.sqrt(np.mean(data_float ** 2))
                        if rms > 500:  # Nível de corte para fala
                            has_sound = True

                if not self.is_running:
                    break

                # Só gasta requisição de transcrição se houver sinal sonoro significativo
                if has_sound and frames and not self.is_paused:
                    audio_data = np.concatenate(frames, axis=0)
                    wav_io = io.BytesIO()
                    with wave.open(wav_io, "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(self.sample_rate)
                        wf.writeframes(audio_data.tobytes())
                    wav_io.seek(0)

                    with sr.AudioFile(wav_io) as source:
                        audio = self.recognizer.record(source)

                    try:
                        detected_text = self.recognizer.recognize_google(audio, language="pt-BR").lower()
                        # Verifica se disse a palavra de ativação
                        target_name = self.robot_name.lower()
                        wake_patterns = [
                            rf"\b(ei|eai|e aí|opa|hey|oi|olá|ola|diga)\s+{re.escape(target_name)}\b",
                            rf"^{re.escape(target_name)}$",
                            rf"\b{re.escape(target_name)}\b"
                        ]
                        for pat in wake_patterns:
                            if re.search(pat, detected_text):
                                self.wake_word_detected.emit(detected_text)
                                break
                    except (sr.UnknownValueError, sr.RequestError):
                        pass

            except Exception:
                time.sleep(1.0)

    @pyqtSlot()
    def stop(self):
        self.is_running = False


class AudioListener(QObject):
    """Fachada unificada para gravação de comandos e escuta contínua de wake word."""
    start_signal = pyqtSignal()
    stop_signal = pyqtSignal()
    start_wake_signal = pyqtSignal()
    stop_wake_signal = pyqtSignal()

    listening_started = pyqtSignal()
    listening_stopped = pyqtSignal()
    amplitude_updated = pyqtSignal(float)
    transcription_success = pyqtSignal(str)
    transcription_error = pyqtSignal(str)
    wake_word_detected = pyqtSignal(str)

    def __init__(self, parent=None, duration: float = 5.0, robot_name: str = "Laranja", wake_enabled: bool = True):
        super().__init__(parent)
        self.is_listening = False
        self.wake_enabled = wake_enabled

        # Thread de gravação de comando
        self.record_thread = QThread()
        self.record_worker = AudioRecorderWorker(duration=duration)
        self.record_worker.moveToThread(self.record_thread)

        self.start_signal.connect(self.record_worker.start_listening)
        self.stop_signal.connect(self.record_worker.stop_listening)
        self.record_worker.listening_started.connect(self._on_command_started)
        self.record_worker.listening_stopped.connect(self._on_command_stopped)
        self.record_worker.amplitude_updated.connect(self.amplitude_updated)
        self.record_worker.transcription_success.connect(self.transcription_success)
        self.record_worker.transcription_error.connect(self.transcription_error)
        self.record_thread.start()

        # Thread de Wake Word contínua
        self.wake_thread = QThread()
        self.wake_worker = WakeWordWorker(robot_name=robot_name)
        self.wake_worker.moveToThread(self.wake_thread)
        self.start_wake_signal.connect(self.wake_worker.run_loop)
        self.stop_wake_signal.connect(self.wake_worker.stop)
        self.wake_worker.wake_word_detected.connect(self.wake_word_detected)
        self.wake_thread.start()

        if self.wake_enabled:
            self.start_wake_signal.emit()

    def update_robot_name(self, name: str):
        self.wake_worker.set_robot_name(name)

    def set_wake_word_enabled(self, enabled: bool):
        self.wake_enabled = enabled
        if enabled:
            self.wake_worker.resume_wake_word()
        else:
            self.wake_worker.pause_wake_word()

    def _on_command_started(self):
        self.is_listening = True
        self.wake_worker.pause_wake_word()
        self.listening_started.emit()

    def _on_command_stopped(self):
        self.is_listening = False
        self.wake_worker.resume_wake_word()
        self.listening_stopped.emit()

    def toggle_listening(self):
        """Alterna entre gravar comando ou parar."""
        if not self.is_listening:
            self.start_signal.emit()
        else:
            self.stop_signal.emit()

    def shutdown(self):
        """Encerra threads secundárias."""
        self.record_worker.stop_listening()
        self.wake_worker.stop()
        self.record_thread.quit()
        self.wake_thread.quit()
        self.record_thread.wait(1000)
        self.wake_thread.wait(1000)

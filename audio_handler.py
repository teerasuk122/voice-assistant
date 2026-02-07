"""
audio_handler.py — Speech-to-Text and Text-to-Speech

STT: Google Web Speech API via SpeechRecognition (Thai th-TH).
TTS: Microsoft Edge TTS (th-TH-PremwadeeNeural) → play via macOS afplay.
"""

import asyncio
import logging
import os
import subprocess
import tempfile

import edge_tts
import speech_recognition as sr
from PyQt6.QtCore import QThread, pyqtSignal

from config import CFG

log = logging.getLogger(__name__)


class STTWorker(QThread):
    """Listen via microphone → emit recognised Thai text."""

    result = pyqtSignal(str)       # recognised text
    error = pyqtSignal(str)
    listening_started = pyqtSignal()

    def run(self):
        recogniser = sr.Recognizer()
        recogniser.energy_threshold = CFG["stt_energy_threshold"]
        recogniser.dynamic_energy_threshold = True
        recogniser.pause_threshold = CFG["stt_pause_threshold"]

        try:
            with sr.Microphone() as source:
                recogniser.adjust_for_ambient_noise(source, duration=0.5)
                self.listening_started.emit()
                log.info("Listening started")
                audio = recogniser.listen(
                    source,
                    phrase_time_limit=CFG["stt_phrase_time_limit"],
                )
        except OSError as exc:
            msg = f"ไม่พบไมโครโฟน: {exc}"
            log.error(msg)
            self.error.emit(msg)
            return

        try:
            text = recogniser.recognize_google(audio, language=CFG["stt_language"])
            log.info("STT result: %s", text)
            self.result.emit(text)
        except sr.UnknownValueError:
            msg = "ไม่สามารถเข้าใจเสียงได้ — ลองพูดใหม่อีกครั้ง"
            log.warning(msg)
            self.error.emit(msg)
        except sr.RequestError as exc:
            msg = f"Google STT Error: {exc}"
            log.error(msg)
            self.error.emit(msg)


class TTSWorker(QThread):
    """Convert text → speech file → play via afplay."""

    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, text: str):
        super().__init__()
        self.text = text

    def run(self):
        try:
            asyncio.run(self._synthesize_and_play())
            self.finished.emit()
        except Exception as exc:
            log.exception("TTS error")
            self.error.emit(f"TTS Error: {exc}")

    async def _synthesize_and_play(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp_path = tmp.name
        tmp.close()

        try:
            communicate = edge_tts.Communicate(self.text, CFG["tts_voice"])
            await communicate.save(tmp_path)
            log.info("TTS audio saved, playing via afplay")

            subprocess.run(
                ["afplay", tmp_path],
                check=True,
                capture_output=True,
            )
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

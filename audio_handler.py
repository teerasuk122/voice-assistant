"""
audio_handler.py — Speech-to-Text and Text-to-Speech

STT: Google Web Speech API via SpeechRecognition (Thai th-TH).
TTS: Microsoft Edge TTS (th-TH-PremwadeeNeural) → play via macOS afplay.
"""

import asyncio
import os
import subprocess
import tempfile

import edge_tts
import speech_recognition as sr
from PyQt6.QtCore import QThread, pyqtSignal


TTS_VOICE = "th-TH-PremwadeeNeural"
STT_LANGUAGE = "th-TH"

# Silence-based energy / pause thresholds
ENERGY_THRESHOLD = 300
PAUSE_THRESHOLD = 1.5        # seconds of silence to consider phrase complete
PHRASE_TIME_LIMIT = 30        # max seconds for a single utterance


class STTWorker(QThread):
    """Listen via microphone → emit recognised Thai text."""

    result = pyqtSignal(str)       # recognised text
    error = pyqtSignal(str)
    listening_started = pyqtSignal()

    def run(self):
        recogniser = sr.Recognizer()
        recogniser.energy_threshold = ENERGY_THRESHOLD
        recogniser.dynamic_energy_threshold = True
        recogniser.pause_threshold = PAUSE_THRESHOLD

        try:
            with sr.Microphone() as source:
                recogniser.adjust_for_ambient_noise(source, duration=0.5)
                self.listening_started.emit()
                audio = recogniser.listen(
                    source,
                    phrase_time_limit=PHRASE_TIME_LIMIT,
                )
        except OSError as exc:
            self.error.emit(f"ไม่พบไมโครโฟน: {exc}")
            return

        try:
            text = recogniser.recognize_google(audio, language=STT_LANGUAGE)
            self.result.emit(text)
        except sr.UnknownValueError:
            self.error.emit("ไม่สามารถเข้าใจเสียงได้ — ลองพูดใหม่อีกครั้ง")
        except sr.RequestError as exc:
            self.error.emit(f"Google STT Error: {exc}")


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
            self.error.emit(f"TTS Error: {exc}")

    async def _synthesize_and_play(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp_path = tmp.name
        tmp.close()

        try:
            communicate = edge_tts.Communicate(self.text, TTS_VOICE)
            await communicate.save(tmp_path)

            # afplay is built-in on macOS — lightweight, no extra deps
            proc = subprocess.run(
                ["afplay", tmp_path],
                check=True,
                capture_output=True,
            )
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

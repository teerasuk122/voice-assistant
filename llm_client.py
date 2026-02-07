"""
llm_client.py — OpenClaw API Client (OpenAI-compatible)

Handles all communication with the OpenClaw inference endpoint.
Runs requests in a QThread to avoid blocking the GUI.
"""

import requests
from PyQt6.QtCore import QThread, pyqtSignal


OPENCLAW_URL = "http://localhost:4000/v1/chat/completions"
MODEL_NAME = "openclaw"
TIMEOUT_SECONDS = 60


class LLMWorker(QThread):
    """Background thread for LLM API calls."""

    finished = pyqtSignal(str)     # emitted with the assistant reply
    error = pyqtSignal(str)        # emitted on failure

    def __init__(self, user_text: str, conversation: list | None = None):
        super().__init__()
        self.user_text = user_text
        self.conversation = conversation or []

    def run(self):
        messages = list(self.conversation)
        messages.append({"role": "user", "content": self.user_text})

        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1024,
        }

        try:
            resp = requests.post(
                OPENCLAW_URL,
                json=payload,
                timeout=TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            data = resp.json()
            reply = data["choices"][0]["message"]["content"]
            self.finished.emit(reply.strip())
        except requests.ConnectionError:
            self.error.emit("ไม่สามารถเชื่อมต่อ OpenClaw ได้ — ตรวจสอบว่าเซิร์ฟเวอร์ทำงานอยู่")
        except requests.Timeout:
            self.error.emit("OpenClaw ไม่ตอบสนองภายในเวลาที่กำหนด")
        except Exception as exc:
            self.error.emit(f"LLM Error: {exc}")

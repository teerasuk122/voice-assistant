"""
llm_client.py — OpenClaw API Client (OpenAI-compatible)

Handles all communication with the OpenClaw inference endpoint.
Runs requests in a QThread to avoid blocking the GUI.
"""

import logging
import requests
from PyQt6.QtCore import QThread, pyqtSignal

from config import CFG

log = logging.getLogger(__name__)


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
            "model": CFG["llm_model"],
            "messages": messages,
            "temperature": CFG["llm_temperature"],
            "max_tokens": CFG["llm_max_tokens"],
        }

        log.info("Sending to LLM: %s", self.user_text[:80])

        try:
            resp = requests.post(
                CFG["llm_url"],
                json=payload,
                timeout=CFG["llm_timeout"],
            )
            resp.raise_for_status()
            data = resp.json()
            reply = data["choices"][0]["message"]["content"]
            log.info("LLM reply received (%d chars)", len(reply))
            self.finished.emit(reply.strip())
        except requests.ConnectionError:
            msg = "ไม่สามารถเชื่อมต่อ OpenClaw ได้ — ตรวจสอบว่าเซิร์ฟเวอร์ทำงานอยู่"
            log.error(msg)
            self.error.emit(msg)
        except requests.Timeout:
            msg = "OpenClaw ไม่ตอบสนองภายในเวลาที่กำหนด"
            log.error(msg)
            self.error.emit(msg)
        except Exception as exc:
            log.exception("LLM error")
            self.error.emit(f"LLM Error: {exc}")

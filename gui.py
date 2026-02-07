"""
gui.py — Floating HUD search-bar interface (PyQt6)

Frameless, transparent, always-on-top, centred overlay.
Dark-mode aesthetic with pulsing animation while listening.
"""

from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QTimer, pyqtSlot, QSize,
)
from PyQt6.QtGui import QColor, QPainter, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGraphicsDropShadowEffect,
    QApplication, QSizePolicy,
)

import logging

from audio_handler import STTWorker, TTSWorker
from llm_client import LLMWorker
from config import CFG

log = logging.getLogger(__name__)

# ── Colour palette ──────────────────────────────────────────────
BG_COLOR      = QColor(30, 30, 30, 230)       # near-black translucent
ACCENT_COLOR  = QColor(80, 160, 255)           # blue accent
TEXT_COLOR     = QColor(230, 230, 230)
ERROR_COLOR   = QColor(255, 90, 90)
SUBTLE_COLOR  = QColor(140, 140, 140)

BAR_WIDTH  = CFG["bar_width"]
BAR_HEIGHT = 64
EXPANDED_MIN_HEIGHT = 180
CORNER_RADIUS = 20


class PulseIndicator(QWidget):
    """Animated pulsing circle shown while listening."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self._radius = 6.0
        self._opacity = 1.0

        self._anim = QPropertyAnimation(self, b"minimumSize")
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(60)
        self._pulse_state = 0.0
        self._pulse_direction = 1
        self._pulse_timer.timeout.connect(self._tick)

    def start(self):
        self._pulse_timer.start()
        self.show()

    def stop(self):
        self._pulse_timer.stop()
        self.hide()

    def _tick(self):
        self._pulse_state += 0.05 * self._pulse_direction
        if self._pulse_state >= 1.0:
            self._pulse_direction = -1
        elif self._pulse_state <= 0.0:
            self._pulse_direction = 1
        self._radius = 4.0 + 6.0 * self._pulse_state
        self._opacity = 0.4 + 0.6 * (1.0 - self._pulse_state)
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(ACCENT_COLOR)
        color.setAlphaF(self._opacity)
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        cx, cy = self.width() / 2, self.height() / 2
        painter.drawEllipse(int(cx - self._radius), int(cy - self._radius),
                            int(self._radius * 2), int(self._radius * 2))
        painter.end()


class AssistantHUD(QWidget):
    """The main floating overlay window."""

    def __init__(self):
        super().__init__()
        self._conversation: list[dict] = []
        self._setup_window()
        self._build_ui()
        self._workers_init()

    # ── Window setup ────────────────────────────────────────────
    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool              # hide from dock / taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(BAR_WIDTH)
        self.setMinimumHeight(BAR_HEIGHT)

    def _center_on_screen(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = int(screen.height() * 0.28)       # slightly above centre
        self.move(x, y)

    # ── UI construction ─────────────────────────────────────────
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(10)

        # Top row: pulse indicator + status label
        self.pulse = PulseIndicator(self)
        self.pulse.hide()

        self.status_label = QLabel("กดปุ่มพูดเพื่อเริ่มต้น")
        self.status_label.setFont(QFont(".AppleSystemUIFont", 15))
        self.status_label.setStyleSheet(f"color: {SUBTLE_COLOR.name()};")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        from PyQt6.QtWidgets import QHBoxLayout
        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        top_row.addWidget(self.pulse)
        top_row.addWidget(self.status_label, 1)
        layout.addLayout(top_row)

        # Response area (hidden when collapsed)
        self.response_label = QLabel("")
        self.response_label.setFont(QFont(".AppleSystemUIFont", 14))
        self.response_label.setStyleSheet(f"color: {TEXT_COLOR.name()};")
        self.response_label.setWordWrap(True)
        self.response_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.response_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.response_label.hide()
        layout.addWidget(self.response_label)

        # Shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

    # ── Paint rounded dark background ───────────────────────────
    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(BG_COLOR)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), CORNER_RADIUS, CORNER_RADIUS)
        painter.end()

    # ── Worker references ───────────────────────────────────────
    def _workers_init(self):
        self._stt_worker: STTWorker | None = None
        self._llm_worker: LLMWorker | None = None
        self._tts_worker: TTSWorker | None = None

    # ── Public API ──────────────────────────────────────────────
    def activate(self):
        """Show the HUD and start listening."""
        self._set_collapsed()
        self.show()
        self.raise_()
        self.activateWindow()
        self._center_on_screen()
        self._start_listening()

    def deactivate(self):
        """Hide the HUD and stop any workers."""
        self._stop_all_workers()
        self.hide()

    def toggle(self):
        if self.isVisible():
            self.deactivate()
        else:
            self.activate()

    # ── Internal state helpers ──────────────────────────────────
    def _set_collapsed(self):
        self.response_label.hide()
        self.response_label.setText("")
        self.setFixedHeight(BAR_HEIGHT)
        self._center_on_screen()

    def _set_expanded(self, text: str):
        self.response_label.setText(text)
        self.response_label.show()
        self.adjustSize()
        height = max(EXPANDED_MIN_HEIGHT, self.sizeHint().height())
        self.setFixedHeight(min(height, 500))
        self._center_on_screen()

    def _set_status(self, msg: str, color: QColor = SUBTLE_COLOR):
        self.status_label.setText(msg)
        self.status_label.setStyleSheet(f"color: {color.name()};")

    # ── Listening pipeline ──────────────────────────────────────
    def _start_listening(self):
        self._set_status("กำลังฟัง…", ACCENT_COLOR)
        self.pulse.start()

        self._stt_worker = STTWorker()
        self._stt_worker.listening_started.connect(self._on_listening_started)
        self._stt_worker.result.connect(self._on_stt_result)
        self._stt_worker.error.connect(self._on_stt_error)
        self._stt_worker.start()

    @pyqtSlot()
    def _on_listening_started(self):
        self._set_status("กำลังฟัง… พูดได้เลย", ACCENT_COLOR)

    @pyqtSlot(str)
    def _on_stt_result(self, text: str):
        self.pulse.stop()
        self._set_status(f"🗣 \"{text}\"", TEXT_COLOR)
        self._send_to_llm(text)

    @pyqtSlot(str)
    def _on_stt_error(self, msg: str):
        self.pulse.stop()
        self._set_status(msg, ERROR_COLOR)
        # Auto-retry listening after showing error briefly
        QTimer.singleShot(2000, self._resume_listening)

    # ── LLM pipeline ───────────────────────────────────────────
    def _send_to_llm(self, user_text: str):
        self._set_status("กำลังคิด…", ACCENT_COLOR)

        self._llm_worker = LLMWorker(user_text, self._conversation)
        self._llm_worker.finished.connect(lambda reply: self._on_llm_reply(user_text, reply))
        self._llm_worker.error.connect(self._on_llm_error)
        self._llm_worker.start()

    @pyqtSlot(str)
    def _on_llm_reply(self, user_text: str, reply: str):
        # Keep conversation history (capped at 20 turns)
        self._conversation.append({"role": "user", "content": user_text})
        self._conversation.append({"role": "assistant", "content": reply})
        if len(self._conversation) > 40:
            self._conversation = self._conversation[-40:]

        self._set_status("คำตอบ:", TEXT_COLOR)
        self._set_expanded(reply)
        self._speak(reply)

    @pyqtSlot(str)
    def _on_llm_error(self, msg: str):
        self._set_status(msg, ERROR_COLOR)
        QTimer.singleShot(3000, self._resume_listening)

    # ── TTS pipeline ────────────────────────────────────────────
    def _speak(self, text: str):
        self._tts_worker = TTSWorker(text)
        self._tts_worker.finished.connect(self._on_tts_done)
        self._tts_worker.error.connect(self._on_tts_error)
        self._tts_worker.start()

    @pyqtSlot()
    def _on_tts_done(self):
        # After speaking, automatically start listening again
        QTimer.singleShot(500, self._resume_listening)

    @pyqtSlot(str)
    def _on_tts_error(self, msg: str):
        # Non-fatal: response is still visible, resume listening
        log.warning("TTS: %s", msg)
        QTimer.singleShot(500, self._resume_listening)

    # ── Resume listening (continuous mode) ─────────────────────
    def _resume_listening(self):
        """Collapse the response and start listening again."""
        if not self.isVisible():
            return
        self._set_collapsed()
        self._center_on_screen()
        self._start_listening()

    # ── Cleanup ─────────────────────────────────────────────────
    def _stop_all_workers(self):
        for w in (self._stt_worker, self._llm_worker, self._tts_worker):
            if w is not None and w.isRunning():
                w.quit()
                w.wait(2000)

    def keyPressEvent(self, event):
        """Escape dismisses the overlay."""
        if event.key() == Qt.Key.Key_Escape:
            self.deactivate()
        super().keyPressEvent(event)

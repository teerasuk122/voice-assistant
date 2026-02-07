#!/usr/bin/env python3
"""
main.py — Voice Assistant entry point

Registers a global Alt+Space hotkey via pynput,
launches the PyQt6 HUD, and bridges the two event loops.
"""

import sys
import signal

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PyQt6.QtCore import QTimer
from pynput import keyboard

from gui import AssistantHUD


def make_tray_icon() -> QIcon:
    """Generate a simple coloured circle as the tray icon."""
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(80, 160, 255))
    painter.setPen(QColor(80, 160, 255))
    painter.drawEllipse(8, 8, size - 16, size - 16)
    painter.end()
    return QIcon(pixmap)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # keep running in tray

    hud = AssistantHUD()

    # ── System tray ─────────────────────────────────────────────
    tray = QSystemTrayIcon(make_tray_icon(), parent=app)
    tray_menu = QMenu()

    activate_action = QAction("เปิดผู้ช่วย (Alt+Space)")
    activate_action.triggered.connect(hud.activate)
    tray_menu.addAction(activate_action)

    quit_action = QAction("ออก")
    quit_action.triggered.connect(app.quit)
    tray_menu.addAction(quit_action)

    tray.setContextMenu(tray_menu)
    tray.setToolTip("Voice Assistant — Alt+Space")
    tray.show()

    # ── Global hotkey (pynput runs its own thread) ──────────────
    hotkey_combo = {keyboard.Key.alt_l, keyboard.Key.space}
    pressed_keys: set = set()

    def on_press(key):
        pressed_keys.add(key)
        if hotkey_combo.issubset(pressed_keys):
            # Schedule on the Qt main thread via a single-shot timer
            QTimer.singleShot(0, hud.toggle)

    def on_release(key):
        pressed_keys.discard(key)

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.daemon = True
    listener.start()

    # Allow Ctrl+C to quit from terminal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    print("Voice Assistant running — Alt+Space to activate, tray icon to quit.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

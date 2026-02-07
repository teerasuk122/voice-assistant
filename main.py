#!/usr/bin/env python3
"""
main.py — Voice Assistant entry point

Registers a global Ctrl+Space hotkey using macOS Quartz Event Tap,
launches the PyQt6 HUD, and bridges the two event loops.
"""

import sys
import signal
import logging
import threading

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PyQt6.QtCore import QTimer

import Quartz
from Foundation import NSObject

from config import setup_logging, create_default_config, CFG
from gui import AssistantHUD

log = logging.getLogger(__name__)

# Modifier flags
kCGEventFlagMaskControl = 0x00040000
SPACE_KEYCODE = 49


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


def start_hotkey_listener(callback):
    """Use Quartz Event Tap to listen for Ctrl+Space globally."""

    def event_tap_callback(proxy, event_type, event, refcon):
        if event_type == Quartz.kCGEventKeyDown:
            keycode = Quartz.CGEventGetIntegerValueField(
                event, Quartz.kCGKeyboardEventKeycode
            )
            flags = Quartz.CGEventGetFlags(event)
            ctrl_held = bool(flags & kCGEventFlagMaskControl)

            if keycode == SPACE_KEYCODE and ctrl_held:
                log.info("Hotkey triggered (Ctrl+Space)")
                QTimer.singleShot(0, callback)
                # Return None to suppress the event (prevent space from typing)
                return None

        return event

    event_mask = Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown)

    tap = Quartz.CGEventTapCreate(
        Quartz.kCGSessionEventTap,
        Quartz.kCGHeadInsertEventTap,
        Quartz.kCGEventTapOptionDefault,
        event_mask,
        event_tap_callback,
        None,
    )

    if tap is None:
        log.error(
            "Failed to create event tap! "
            "Grant Accessibility permission: "
            "System Settings → Privacy & Security → Accessibility"
        )
        return

    run_loop_source = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
    Quartz.CFRunLoopAddSource(
        Quartz.CFRunLoopGetCurrent(),
        run_loop_source,
        Quartz.kCFRunLoopCommonModes,
    )
    Quartz.CGEventTapEnable(tap, True)
    log.info("Quartz event tap registered (Ctrl+Space)")
    Quartz.CFRunLoopRun()


def main():
    setup_logging()
    create_default_config()

    log.info("Starting Voice Assistant")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    hud = AssistantHUD()

    # ── System tray ─────────────────────────────────────────────
    tray = QSystemTrayIcon(make_tray_icon(), parent=app)
    tray_menu = QMenu()

    activate_action = QAction("เปิดผู้ช่วย (Ctrl+Space)")
    activate_action.triggered.connect(hud.activate)
    tray_menu.addAction(activate_action)

    quit_action = QAction("ออก")
    quit_action.triggered.connect(app.quit)
    tray_menu.addAction(quit_action)

    tray.setContextMenu(tray_menu)
    tray.setToolTip("Voice Assistant — Ctrl+Space / click tray")
    # Click on tray icon = activate HUD (fallback for hotkey)
    tray.activated.connect(
        lambda reason: hud.toggle()
        if reason == QSystemTrayIcon.ActivationReason.Trigger
        else None
    )
    tray.show()

    # ── Global hotkey via Quartz (runs in daemon thread) ────────
    hotkey_thread = threading.Thread(
        target=start_hotkey_listener,
        args=(hud.toggle,),
        daemon=True,
    )
    hotkey_thread.start()

    # Allow Ctrl+C to quit from terminal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    log.info("Voice Assistant running — Ctrl+Space or click tray icon")
    print("Voice Assistant running — Ctrl+Space or click tray icon to activate.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

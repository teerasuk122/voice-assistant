#!/usr/bin/env python3
"""
autostart.py — Install/remove macOS LaunchAgent for auto-start on login.

Usage:
    python autostart.py install    # Enable auto-start
    python autostart.py remove     # Disable auto-start
    python autostart.py status     # Check status
"""

import os
import sys
import subprocess
from pathlib import Path

PLIST_NAME = "com.voiceassistant.app"
LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
PLIST_PATH = LAUNCH_AGENTS_DIR / f"{PLIST_NAME}.plist"
PROJECT_DIR = Path(__file__).parent.resolve()
VENV_PYTHON = PROJECT_DIR / "venv" / "bin" / "python"
MAIN_SCRIPT = PROJECT_DIR / "main.py"


def generate_plist() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{PLIST_NAME}</string>

    <key>ProgramArguments</key>
    <array>
        <string>{VENV_PYTHON}</string>
        <string>{MAIN_SCRIPT}</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <false/>

    <key>WorkingDirectory</key>
    <string>{PROJECT_DIR}</string>

    <key>StandardOutPath</key>
    <string>{PROJECT_DIR / "logs" / "launchd_stdout.log"}</string>

    <key>StandardErrorPath</key>
    <string>{PROJECT_DIR / "logs" / "launchd_stderr.log"}</string>
</dict>
</plist>
"""


def install():
    LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    (PROJECT_DIR / "logs").mkdir(exist_ok=True)

    if not VENV_PYTHON.exists():
        print(f"ERROR: venv not found at {VENV_PYTHON}")
        print("Run: python3.12 -m venv venv && source venv/bin/activate && pip install -r requirements.txt")
        sys.exit(1)

    PLIST_PATH.write_text(generate_plist(), encoding="utf-8")
    subprocess.run(["launchctl", "load", str(PLIST_PATH)], check=True)
    print(f"Installed: {PLIST_PATH}")
    print("Voice Assistant will start automatically on login.")


def remove():
    if not PLIST_PATH.exists():
        print("Not installed.")
        return
    subprocess.run(["launchctl", "unload", str(PLIST_PATH)], check=False)
    PLIST_PATH.unlink()
    print(f"Removed: {PLIST_PATH}")


def status():
    if PLIST_PATH.exists():
        result = subprocess.run(
            ["launchctl", "list", PLIST_NAME],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print(f"INSTALLED and loaded: {PLIST_PATH}")
        else:
            print(f"INSTALLED but not loaded: {PLIST_PATH}")
    else:
        print("NOT INSTALLED")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("install", "remove", "status"):
        print(__doc__)
        sys.exit(1)

    action = sys.argv[1]
    {"install": install, "remove": remove, "status": status}[action]()

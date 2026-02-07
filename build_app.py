#!/usr/bin/env python3
"""
build_app.py — Build macOS .app bundle with PyInstaller

Usage:
    source venv/bin/activate
    python build_app.py
"""

import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.resolve()


def build():
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "VoiceAssistant",
        "--windowed",                          # .app bundle (no terminal)
        "--onedir",                            # faster startup than --onefile
        "--noconfirm",
        "--clean",

        # macOS specific
        "--osx-bundle-identifier", "com.voiceassistant.app",

        # Hidden imports that PyInstaller may miss
        "--hidden-import", "pynput.keyboard._darwin",
        "--hidden-import", "pynput.mouse._darwin",
        "--hidden-import", "speech_recognition",
        "--hidden-import", "edge_tts",

        # Include config.yaml if it exists
        *(["--add-data", "config.yaml:."] if (PROJECT_DIR / "config.yaml").exists() else []),

        # Entry point
        str(PROJECT_DIR / "main.py"),
    ]

    print("Building .app bundle...")
    print(f"Command: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(PROJECT_DIR))

    if result.returncode == 0:
        app_path = PROJECT_DIR / "dist" / "VoiceAssistant.app"
        if app_path.exists():
            print(f"\nBuild successful!")
            print(f"App location: {app_path}")
            print(f"\nTo run: open {app_path}")
            print(f"To install: cp -r {app_path} /Applications/")
        else:
            # onedir mode puts it in a folder
            dist_dir = PROJECT_DIR / "dist" / "VoiceAssistant"
            print(f"\nBuild successful!")
            print(f"Distribution: {dist_dir}")
            app_in_dist = dist_dir / "VoiceAssistant.app"
            if app_in_dist.exists():
                print(f"App: {app_in_dist}")
    else:
        print(f"\nBuild FAILED (exit code {result.returncode})")
        sys.exit(1)


if __name__ == "__main__":
    build()

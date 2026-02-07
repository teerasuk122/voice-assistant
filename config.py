"""
config.py — Centralised configuration

Loads settings from config.yaml if present, otherwise uses defaults.
"""

import os
import logging
from pathlib import Path

APP_NAME = "VoiceAssistant"
APP_DIR = Path(__file__).parent
LOG_DIR = APP_DIR / "logs"
CONFIG_PATH = APP_DIR / "config.yaml"

# ── Defaults ────────────────────────────────────────────────────
DEFAULTS = {
    # OpenClaw / LLM
    "llm_url": "http://localhost:4000/v1/chat/completions",
    "llm_model": "openclaw",
    "llm_timeout": 60,
    "llm_temperature": 0.7,
    "llm_max_tokens": 1024,

    # STT
    "stt_language": "th-TH",
    "stt_energy_threshold": 300,
    "stt_pause_threshold": 1.5,
    "stt_phrase_time_limit": 30,

    # TTS
    "tts_voice": "th-TH-PremwadeeNeural",

    # Hotkey
    "hotkey": "alt+space",

    # UI
    "bar_width": 680,
    "auto_hide_delay": 5000,  # ms after TTS finishes
}


def _load_yaml() -> dict:
    """Load config.yaml if it exists; return empty dict otherwise."""
    if not CONFIG_PATH.exists():
        return {}
    try:
        import yaml  # optional dependency
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        logging.warning("PyYAML not installed — using default config")
        return {}
    except Exception as exc:
        logging.warning("Failed to load config.yaml: %s", exc)
        return {}


def _merge(defaults: dict, overrides: dict) -> dict:
    merged = dict(defaults)
    for k, v in overrides.items():
        if k in merged:
            merged[k] = type(merged[k])(v)  # cast to expected type
    return merged


# ── Public config object ────────────────────────────────────────
_overrides = _load_yaml()
CFG = _merge(DEFAULTS, _overrides)


# ── Logging setup ───────────────────────────────────────────────
def setup_logging():
    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / "assistant.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    logging.info("Config loaded: overrides=%s", list(_overrides.keys()) or "none")


def create_default_config():
    """Write a sample config.yaml for user reference."""
    if CONFIG_PATH.exists():
        return
    sample = """# Voice Assistant Configuration
# Uncomment and modify any value to override the default.

# llm_url: http://localhost:4000/v1/chat/completions
# llm_model: openclaw
# llm_timeout: 60
# llm_temperature: 0.7
# llm_max_tokens: 1024

# stt_language: th-TH
# stt_energy_threshold: 300
# stt_pause_threshold: 1.5
# stt_phrase_time_limit: 30

# tts_voice: th-TH-PremwadeeNeural

# hotkey: alt+space

# bar_width: 680
# auto_hide_delay: 5000
"""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(sample)
    logging.info("Created sample config.yaml")

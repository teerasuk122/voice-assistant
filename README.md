# Voice Assistant for macOS

A local, Siri-like desktop voice assistant that runs entirely on your Mac. Speak Thai commands through a floating HUD overlay, get answers from a local LLM (Ollama), and hear responses read aloud.

![Python](https://img.shields.io/badge/Python-3.12+-blue)
![macOS](https://img.shields.io/badge/macOS-Sequoia-black)
![LLM](https://img.shields.io/badge/LLM-Ollama-orange)

## How It Works

```
Ctrl+Space ──> HUD appears ──> Listen (Thai STT) ──> LLM thinks ──> Speak (Thai TTS) ──> Auto-hide
```

| Stage | Technology | Detail |
|-------|-----------|--------|
| GUI | PyQt6 | Frameless, transparent, always-on-top dark overlay |
| STT | Google Web Speech API | Thai (`th-TH`), silence-based auto-stop |
| LLM | Ollama + LiteLLM Proxy | Local inference, OpenAI-compatible API |
| TTS | Microsoft Edge TTS | `th-TH-PremwadeeNeural` voice, played via `afplay` |
| Hotkey | Quartz Event Tap | `Ctrl+Space` global hotkey (+ tray icon fallback) |

## Prerequisites

- **macOS** (Apple Silicon recommended)
- **Python 3.12+**
- **Homebrew** (`/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`)
- **External microphone** (Mac Mini has no built-in mic — use USB/Bluetooth)
- **Internet connection** (required for Google STT and Edge TTS)

## Installation

### 1. Clone and setup

```bash
git clone https://github.com/teerasuk122/voice-assistant.git
cd voice-assistant
```

### 2. Install system dependencies

```bash
brew install python@3.12 portaudio ollama
```

### 3. Create virtual environment

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Start Ollama and pull a model

```bash
brew services start ollama
ollama pull llama3.1:8b
```

### 5. Install and start LiteLLM Proxy (OpenAI-compatible API on port 4000)

```bash
pip install 'litellm[proxy]'
litellm --config litellm_config.yaml --port 4000
```

### 6. Grant macOS permissions

The app requires these permissions in **System Settings > Privacy & Security**:

| Permission | Why |
|-----------|-----|
| **Accessibility** | Global hotkey (Ctrl+Space) |
| **Microphone** | Speech recognition |

Add your **Terminal.app** (or the app you run from) to both.

## Usage

### Run from terminal

```bash
source venv/bin/activate
python main.py
```

### Activate the assistant

| Method | Action |
|--------|--------|
| **Hotkey** | Press `Ctrl+Space` |
| **Tray icon** | Click the blue circle in the menu bar |
| **Tray menu** | Right-click tray > "เปิดผู้ช่วย" |

### Voice interaction

1. HUD appears with pulsing blue indicator
2. Speak in Thai — recording stops automatically on silence
3. LLM processes your query (status: "กำลังคิด…")
4. Response is displayed and read aloud
5. HUD auto-hides after 5 seconds (or press `Esc`)

### Quit

Right-click the tray icon > "ออก"

## Configuration

A `config.yaml` is auto-generated on first run. Edit it to customize:

```yaml
# LLM
llm_url: http://localhost:4000/v1/chat/completions
llm_model: openclaw
llm_timeout: 60
llm_temperature: 0.7
llm_max_tokens: 1024

# Speech-to-Text
stt_language: th-TH
stt_energy_threshold: 300
stt_pause_threshold: 1.5        # seconds of silence to stop recording
stt_phrase_time_limit: 30       # max recording duration

# Text-to-Speech
tts_voice: th-TH-PremwadeeNeural

# UI
bar_width: 680
auto_hide_delay: 5000           # ms after TTS finishes
```

Install PyYAML to enable config overrides:

```bash
pip install pyyaml
```

## Project Structure

```
voice-assistant/
├── main.py               # Entry point, hotkey, system tray
├── gui.py                # PyQt6 floating HUD with animations
├── audio_handler.py      # STT (Google) + TTS (Edge) workers
├── llm_client.py         # OpenClaw/LiteLLM API client
├── config.py             # Centralized config + logging
├── autostart.py          # macOS LaunchAgent manager
├── build_app.py          # PyInstaller .app bundle builder
├── litellm_config.yaml   # LiteLLM proxy model routing
├── requirements.txt      # Python dependencies
└── logs/                 # Runtime logs (auto-created)
```

## Architecture

All blocking operations run in **QThread** workers to keep the UI responsive:

```
┌─────────────────────────────────────────────────┐
│  main.py                                        │
│  ┌──────────┐  ┌──────────────────────────────┐ │
│  │  Quartz  │  │  PyQt6 Main Thread           │ │
│  │  Hotkey  │──│  ┌────────────────────────┐  │ │
│  │  Thread  │  │  │   AssistantHUD (gui)   │  │ │
│  └──────────┘  │  │                        │  │ │
│                │  │  STTWorker ──────────┐  │  │ │
│  ┌──────────┐  │  │  LLMWorker ────────┐│  │  │ │
│  │  System  │  │  │  TTSWorker ──────┐││  │  │ │
│  │  Tray    │──│  │                  │││  │  │ │
│  └──────────┘  │  └──────────────────│││──┘  │ │
│                └─────────────────────│││─────┘ │
│                                      │││       │
│  ┌───────────────────────────────────│││─────┐ │
│  │  External Services                │││     │ │
│  │  ┌─────────────┐  ┌─────────────┐│││     │ │
│  │  │ Google STT  │◄─┘             ││││     │ │
│  │  │ (Internet)  │   │ LiteLLM    │◄┘│     │ │
│  │  └─────────────┘   │ :4000      │  │     │ │
│  │  ┌─────────────┐   │  ┌───────┐ │  │     │ │
│  │  │ Edge TTS    │◄──│  │Ollama │ │  │     │ │
│  │  │ (Internet)  │   │  │:11434 │◄┘  │     │ │
│  │  └─────────────┘   │  └───────┘ │  │     │ │
│  │                    └─────────────┘  │     │ │
│  └─────────────────────────────────────┘     │ │
└──────────────────────────────────────────────┘
```

## Extra Features

### Auto-start on login

```bash
python autostart.py install    # Enable
python autostart.py remove     # Disable
python autostart.py status     # Check
```

### Build .app bundle

```bash
pip install pyinstaller
python build_app.py
# Output: dist/VoiceAssistant.app

# Install to Applications:
cp -r dist/VoiceAssistant.app /Applications/
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Hotkey doesn't work | Grant Accessibility permission to Terminal.app / your terminal |
| "ไม่พบไมโครโฟน" | Connect external mic, check System Settings > Sound > Input |
| "ไม่สามารถเชื่อมต่อ OpenClaw" | Start Ollama (`brew services start ollama`) and LiteLLM proxy |
| "ไม่สามารถเข้าใจเสียงได้" | Speak louder/closer to mic, check internet connection |
| TTS no sound | Check System Settings > Sound > Output, verify internet |

## Tech Stack

- **Python 3.12** — Runtime
- **PyQt6** — GUI framework
- **SpeechRecognition** — Google Web Speech API wrapper
- **edge-tts** — Microsoft Edge Text-to-Speech
- **Ollama** — Local LLM inference engine
- **LiteLLM** — OpenAI-compatible API proxy
- **Quartz (PyObjC)** — macOS native global hotkey

## License

MIT

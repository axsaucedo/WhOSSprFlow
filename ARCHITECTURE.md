# WhOSSpr Flow Architecture

This document describes the architecture of WhOSSpr Flow, an open-source speech-to-text application for macOS.

## Overview

WhOSSpr Flow captures audio from the microphone, transcribes it using OpenAI Whisper, optionally enhances the text with an LLM, and inserts the result into the active application.

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Workflow                             │
├─────────────────────────────────────────────────────────────────┤
│  1. User presses keyboard shortcut (hold or toggle)              │
│  2. Audio is recorded from microphone                            │
│  3. Audio is transcribed to text using Whisper                   │
│  4. (Optional) Text is enhanced using LLM                        │
│  5. Text is inserted at cursor position via clipboard paste      │
└─────────────────────────────────────────────────────────────────┘
```

## Module Structure

```
whosspr/
├── __init__.py      # Package version
├── cli.py           # Command-line interface (Typer)
├── config.py        # Configuration schema and loading
├── controller.py    # Main orchestration logic
├── recorder.py      # Audio recording (sounddevice)
├── transcriber.py   # Speech-to-text (Whisper)
├── keyboard.py      # Global keyboard shortcuts (pynput)
├── inserter.py      # Text insertion via clipboard
├── enhancer.py      # LLM text enhancement (OpenAI API)
└── permissions.py   # macOS permission checks
```

## Module Responsibilities

### cli.py (284 lines)
Command-line interface built with Typer. Handles:
- Argument parsing and config loading
- Permission checks before starting
- Service lifecycle management
- User feedback via Rich console

### config.py (180 lines)
Configuration management using Pydantic:
- Type-safe configuration schema
- JSON file loading/saving
- Default value handling
- Config file discovery

### controller.py (255 lines)
Main orchestration - coordinates all components:
- State management (IDLE → RECORDING → PROCESSING)
- Connects keyboard shortcuts to recording
- Manages the transcription pipeline
- Handles callbacks for UI feedback

### recorder.py (115 lines)
Audio recording using sounddevice:
- Callback-based recording (non-blocking)
- Float32 audio at 16kHz (Whisper's preferred format)
- Start/stop/cancel operations
- Duration tracking

### transcriber.py (116 lines)
Whisper transcription:
- Lazy model loading (load on first use)
- Device auto-detection (CUDA/MPS/CPU)
- Multiple model size support
- Memory management (unload)

### keyboard.py (173 lines)
Global keyboard shortcuts using pynput:
- Shortcut parsing ("ctrl+cmd+1")
- Hold and toggle modes
- Modifier key normalization
- Callback invocation

### inserter.py (53 lines)
Text insertion via clipboard:
- Copy text to clipboard
- Paste with Cmd+V
- Works with any application

### enhancer.py (206 lines)
Optional LLM text enhancement:
- OpenAI-compatible API
- API key resolution (direct, helper command, env var)
- Custom system prompts
- Grammar/punctuation improvement

### permissions.py (58 lines)
macOS permission checks:
- Microphone access
- Accessibility access
- Simple pass/fail status

## Data Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Keyboard   │────▶│  Controller  │────▶│   Recorder   │
│   Shortcuts  │     │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
                            │                    │
                            │                    ▼
                            │              ┌──────────────┐
                            │              │    Audio     │
                            │              │   (numpy)    │
                            │              └──────────────┘
                            │                    │
                            ▼                    ▼
                     ┌──────────────┐     ┌──────────────┐
                     │   Enhancer   │◀────│  Transcriber │
                     │  (optional)  │     │   (Whisper)  │
                     └──────────────┘     └──────────────┘
                            │                    │
                            │                    │
                            ▼                    ▼
                     ┌──────────────┐     ┌──────────────┐
                     │   Inserter   │◀────│    Text      │
                     │              │     │              │
                     └──────────────┘     └──────────────┘
```

## Design Principles

### 1. Simple Modules
Each module has a single, focused responsibility. No module exceeds ~300 lines.

### 2. Sequential Processing
Audio processing is sequential (record → transcribe → enhance → insert). The user is waiting anyway, so threading complexity is avoided.

### 3. Minimal Dependencies Between Modules
Modules are loosely coupled. The controller imports others, but other modules don't import each other (except config).

### 4. Direct Initialization
Components are created directly when needed, not via lazy patterns or factories.

### 5. Callbacks for UI
The controller uses callbacks (on_state, on_text, on_error) to communicate with the CLI, keeping UI concerns separate from logic.

## Threading Model

Threading is minimal:
- **sounddevice** handles audio callback internally
- **pynput** runs keyboard listener in a thread
- **Processing is sequential** - no background threads for transcription

This simplifies debugging and reduces race conditions.

## Configuration

Configuration uses Pydantic models for type safety:

```python
Config
├── whisper: WhisperConfig
│   ├── model_size: ModelSize (tiny/base/small/medium/large/turbo)
│   ├── language: str
│   └── device: DeviceType (auto/cpu/cuda/mps)
├── shortcuts: ShortcutsConfig
│   ├── hold_to_dictate: str
│   └── toggle_dictation: str
├── enhancement: EnhancementConfig
│   ├── enabled: bool
│   ├── api_key: str
│   └── model: str
└── audio: AudioConfig
    ├── sample_rate: int
    └── channels: int
```

## Testing Strategy

```
tests/
├── test_config.py       # Config loading/saving
├── test_recorder.py     # Audio recording
├── test_transcriber.py  # Whisper wrapper
├── test_keyboard.py     # Shortcut parsing/handling
├── test_controller.py   # Orchestration logic
├── test_enhancer.py     # LLM enhancement
├── test_cli.py          # CLI commands
└── test_e2e_manual.py   # Interactive tests (require user)
```

- **Unit tests**: Mock external dependencies (sounddevice, whisper, pynput)
- **Manual E2E tests**: Real audio recording and transcription with user interaction

## File Counts

| File | Lines | Description |
|------|-------|-------------|
| cli.py | 284 | CLI interface |
| controller.py | 255 | Orchestration |
| enhancer.py | 206 | LLM enhancement |
| config.py | 180 | Configuration |
| keyboard.py | 173 | Shortcuts |
| transcriber.py | 116 | Whisper |
| recorder.py | 115 | Audio |
| permissions.py | 58 | Permissions |
| inserter.py | 53 | Text insertion |
| **Total** | **1444** | |

## Dependencies

- **sounddevice**: Audio recording (no portaudio headers needed)
- **openai-whisper**: Local speech-to-text
- **pynput**: Global keyboard shortcuts
- **pyperclip**: Clipboard operations
- **typer + rich**: CLI framework
- **pydantic**: Configuration validation
- **openai**: LLM API client

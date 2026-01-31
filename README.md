# WhOSSpr Flow

Open Source Speech-to-Text for macOS - A clone of Whispr Flow.

## Installation

```bash
pip install whosspr
```

## Quick Start

```bash
# 1. Create default configuration
whosspr config --init

# 2. Check permissions (grant when prompted)
whosspr check

# 3. Start dictation service
whosspr start
```

## Default Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Cmd+1` (hold) | Hold to record, release to transcribe |
| `Ctrl+Cmd+2` | Toggle dictation on/off |

## Features

| Feature | Description |
|---------|-------------|
| Local Whisper transcription | Uses OpenAI Whisper models locally for privacy |
| Configurable model sizes | Choose from tiny, base, small, medium, or large models |
| Keyboard shortcuts | Hold-to-dictate or toggle dictation modes |
| Universal text injection | Works with any application (browsers, terminals, editors) |
| Optional LLM enhancement | Improve transcribed text with OpenAI-compatible APIs |
| JSON configuration | Easy setup via config files or command-line parameters |

## Configuration

Copy `config.example.json` to `whosspr.json` and customize:

```json
{
  "whisper": {
    "model_size": "base",
    "language": "en",
    "device": "auto"
  },
  "shortcuts": {
    "hold_to_dictate": "ctrl+cmd+1",
    "toggle_dictation": "ctrl+cmd+2"
  },
  "enhancement": {
    "enabled": false,
    "api_base_url": "https://api.openai.com/v1",
    "api_key": "",
    "model": "gpt-4o-mini"
  }
}
```

## Whisper Model Sizes

| Model | Size | Speed | Accuracy | VRAM |
|-------|------|-------|----------|------|
| tiny | 39M | Fastest | Basic | ~1GB |
| base | 74M | Fast | Good | ~1GB |
| small | 244M | Medium | Better | ~2GB |
| medium | 769M | Slow | Great | ~5GB |
| large | 1.5B | Slowest | Best | ~10GB |
| turbo | 809M | Fast | High | ~6GB |

**Recommendation:** Start with `base` for a balance of speed and accuracy.

## Requirements

| Requirement | Details |
|-------------|---------|
| OS | macOS 10.14+ (optimized for Apple Silicon) |
| Python | 3.12+ |
| Permissions | Microphone access, Accessibility access |
| RAM | 2GB+ (more for larger models) |

## Permissions Setup

WhOSSpr requires two macOS permissions:

| Permission | Purpose | How to Grant |
|------------|---------|--------------|
| Microphone | Record audio | System Preferences → Privacy → Microphone → Enable Terminal |
| Accessibility | Insert text | System Preferences → Privacy → Accessibility → Add Terminal |

Verify with:
```bash
whosspr check
```

## Usage

### Starting the Service

```bash
whosspr start
```

### Command-line Options

| Option | Description |
|--------|-------------|
| `--model` | Whisper model size (tiny/base/small/medium/large/turbo) |
| `--language` | Language code (e.g., en, es, fr) |
| `--device` | Device for inference (auto/cpu/mps/cuda) |
| `--enhancement` | Enable LLM text enhancement |
| `--api-key` | API key for enhancement |

### Examples

```bash
# Use small model with Spanish
whosspr start --model small --language es

# Use MPS (Apple Silicon GPU)
whosspr start --device mps

# Enable enhancement
whosspr start --enhancement --api-key sk-xxx
```

## Text Enhancement

WhOSSpr can improve transcribed text using an OpenAI-compatible API:

```bash
# Using OpenAI
export OPENAI_API_KEY=sk-your-api-key
whosspr start --enhancement

# Using local LLM (Ollama)
whosspr start --enhancement \
  --api-key ollama \
  --api-base-url http://localhost:11434/v1
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Permission denied | Run `whosspr check`, grant permissions, restart terminal |
| No audio input | Check microphone connection and permissions |
| Text not appearing | Verify Accessibility permission, try different app |
| Model download fails | Check internet, try `--model tiny` |
| High CPU/memory | Use smaller model, try `--device mps` on Apple Silicon |

## Development

### Install from Source

```bash
git clone https://github.com/axsaucedo/WhOSSprFlow.git
cd WhOSSprFlow
pip install -e ".[dev]"
```

### Running Tests

```bash
# All automated tests
pytest

# With coverage
pytest --cov=whosspr

# Manual E2E tests (interactive)
WHOSSPR_MANUAL_TESTS=1 pytest tests/test_e2e_manual.py -v -s
```

### Project Structure

| Directory/File | Purpose |
|----------------|---------|
| `whosspr/` | Main package |
| `whosspr/cli.py` | CLI interface |
| `whosspr/controller.py` | Main orchestration |
| `whosspr/recorder.py` | Audio recording |
| `whosspr/transcriber.py` | Whisper integration |
| `whosspr/keyboard.py` | Shortcut handling |
| `whosspr/inserter.py` | Text insertion |
| `whosspr/enhancer.py` | LLM enhancement |
| `whosspr/config.py` | Configuration |
| `whosspr/permissions.py` | Permission checks |
| `tests/` | Test suite |
| `prompts/` | Enhancement prompts |

### Key Dependencies

| Package | Purpose |
|---------|---------|
| sounddevice | Audio recording |
| openai-whisper | Speech-to-text |
| pynput | Keyboard shortcuts |
| pyperclip | Clipboard operations |
| typer | CLI framework |

## License

Apache 2.0

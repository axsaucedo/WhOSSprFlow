# WhOSSper Flow

Open Source Speech-to-Text for macOS - A clone of Whispr Flow.

## Features

- **Local Whisper transcription** - Uses OpenAI Whisper models locally for privacy
- **Configurable model sizes** - Choose from tiny, base, small, medium, or large models
- **Keyboard shortcuts** - Hold-to-dictate or toggle dictation modes
- **Universal text injection** - Works with any application (browsers, terminals, editors)
- **Optional LLM enhancement** - Improve transcribed text with OpenAI-compatible APIs
- **JSON configuration** - Easy setup via config files or command-line parameters

## Installation

```bash
# Install dependencies
brew install portaudio  # Required for audio recording
uv sync

# Or with pip
pip install -e .
```

## Quick Start

```bash
# Start with default settings
whossper start

# Check permissions
whossper check

# Use custom config
whossper start --config myconfig.json
```

## Configuration

Copy `config.example.json` to `whossper.json` and customize:

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

| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| tiny | 39M | Fastest | Basic |
| base | 74M | Fast | Good |
| small | 244M | Medium | Better |
| medium | 769M | Slow | Great |
| large | 1.5G | Slowest | Best |

## Requirements

- macOS (optimized for Apple Silicon)
- Python 3.12+
- Microphone access permission
- Accessibility permission (for text injection)

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=whossper
```

## License

MIT

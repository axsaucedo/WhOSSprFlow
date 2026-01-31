# WhOSSpr Flow

Open Source Speech-to-Text for macOS - A clone of Whispr Flow.

## Features

- **Local Whisper transcription** - Uses OpenAI Whisper models locally for privacy
- **Configurable model sizes** - Choose from tiny, base, small, medium, or large models
- **Keyboard shortcuts** - Hold-to-dictate or toggle dictation modes
- **Universal text injection** - Works with any application (browsers, terminals, editors)
- **Optional LLM enhancement** - Improve transcribed text with OpenAI-compatible APIs
- **JSON configuration** - Easy setup via config files or command-line parameters

## Quick Start

```bash
# 1. Install WhOSSpr (no system dependencies needed)
uv sync

# 2. Create default configuration
uv run whosspr config --init

# 3. Check permissions (grant when prompted)
uv run whosspr check

# 4. Start dictation service
uv run whosspr start
```

**Default shortcuts:**
- Hold `Ctrl+Cmd+1` to record, release to transcribe
- Press `Ctrl+Cmd+2` to toggle recording on/off

For detailed setup instructions, see [Detailed Instructions](#detailed-instructions) below.

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
uv run pytest --cov=whosspr
```

## License

Apache 2.0

---

# Detailed Instructions

This section covers the complete setup of WhOSSpr Flow on macOS, including permissions, dependencies, and first run.

## System Requirements

- **macOS** 10.14 (Mojave) or later
- **Python** 3.10 or later
- **Homebrew** (for installing dependencies)
- At least **2GB RAM** (more for larger Whisper models)
- **Microphone access**

## Step-by-Step Installation

### 1. Install Python Dependencies

WhOSSpr uses `sounddevice` for audio recording, which has no system dependencies.

If using `uv` (recommended):

```bash
uv sync
```

Or with pip:

```bash
pip install -e .
```

### 2. Grant macOS Permissions

WhOSSpr requires two macOS permissions to function:

#### Microphone Access

Required for recording your voice.

1. Run `whosspr check` - macOS will prompt for microphone access
2. Click **"Allow"** when prompted
3. Or manually:
   - Go to **System Preferences** → **Security & Privacy** → **Privacy**
   - Select **Microphone** from the left sidebar
   - Check the box next to **Terminal** (or your terminal app)

#### Accessibility Access

Required for injecting text into applications.

1. Go to **System Preferences** → **Security & Privacy** → **Privacy**
2. Select **Accessibility** from the left sidebar
3. Click the **lock icon** and enter your password
4. Click **+** and add your **Terminal** app (or iTerm2, VS Code, etc.)
5. Make sure the checkbox is enabled

> **Note:** You need to grant Accessibility access to the application that runs WhOSSpr (e.g., Terminal.app, iTerm2, VS Code terminal).

### 3. Verify Permissions

Run the permission check command:

```bash
uv run whosspr check
```

You should see:
```
✅ Granted  Microphone
✅ Granted  Accessibility
```

If any permissions are denied, follow the instructions shown.

## Configuration

### Create a Configuration File

```bash
uv run whosspr config --init
```

This creates `whosspr.json` in the current directory with default settings.

### Configuration Options

Edit `whosspr.json`:

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
    "model": "gpt-4o-mini",
    "system_prompt_file": "prompts/default_enhancement.txt"
  },
  "audio": {
    "sample_rate": 16000,
    "channels": 1
  },
  "tmp_dir": "./tmp"
}
```

### Whisper Model Sizes

| Model | Size | Speed | Accuracy | VRAM |
|-------|------|-------|----------|------|
| tiny | 39M | Fastest | Lower | ~1GB |
| base | 74M | Fast | Good | ~1GB |
| small | 244M | Medium | Better | ~2GB |
| medium | 769M | Slow | High | ~5GB |
| large | 1.5B | Slowest | Highest | ~10GB |
| turbo | 809M | Fast | High | ~6GB |

**Recommendation:** Start with `base` for a balance of speed and accuracy.

## Usage

### Starting the Dictation Service

```bash
uv run whosspr start
```

With options:

```bash
# Use a specific model
uv run whosspr start --model small

# Specify language
uv run whosspr start --language es

# Use MPS (Apple Silicon GPU)
uv run whosspr start --device mps

# Enable text enhancement with OpenAI API
uv run whosspr start --enhancement --api-key sk-xxx
```

### Keyboard Shortcuts

Default shortcuts (configurable):

| Shortcut | Action |
|----------|--------|
| `Ctrl+Cmd+1` (hold) | Hold to record, release to transcribe |
| `Ctrl+Cmd+2` | Toggle dictation on/off |

### Using Dictation

1. **Hold-to-Dictate Mode:**
   - Press and hold `Ctrl+Cmd+1`
   - Speak into your microphone
   - Release the keys to transcribe and insert text

2. **Toggle Mode:**
   - Press `Ctrl+Cmd+2` to start recording
   - Speak into your microphone
   - Press `Ctrl+Cmd+2` again to stop and insert text

### Stopping the Service

Press `Ctrl+C` in the terminal to stop WhOSSpr.

## Text Enhancement (Optional)

WhOSSpr can improve transcribed text using an OpenAI-compatible API:

```bash
# Using OpenAI
export OPENAI_API_KEY=sk-your-api-key
uv run whosspr start --enhancement

# Using a local LLM (e.g., Ollama)
uv run whosspr start --enhancement \
  --api-key ollama \
  --api-base-url http://localhost:11434/v1
```

### Custom System Prompt

Edit `prompts/default_enhancement.txt` to customize how the LLM improves your text.

## Troubleshooting

### "Permission denied" errors

1. Run `uv run whosspr check` to see which permissions are missing
2. Grant the required permissions in System Preferences
3. **Important:** Restart your terminal after granting Accessibility access

### "No audio input" or silent recordings

1. Check that your microphone is connected and working
2. Verify microphone permission is granted
3. Test your microphone in System Preferences → Sound → Input

### Text not appearing in applications

1. Verify Accessibility permission is granted
2. Make sure the application you're typing in is active (foreground)
3. Some applications may block automated input - try a different app

### Model download issues

The first time you use a model, Whisper downloads it automatically. If this fails:

1. Check your internet connection
2. Try a smaller model: `--model tiny`
3. Manually download: `uv run python -c "import whisper; whisper.load_model('base')"`

### High CPU/memory usage

- Use a smaller model: `tiny` or `base`
- For Apple Silicon Macs, use `--device mps` to use the GPU

## Running Tests

```bash
# Run all automated tests
uv run pytest

# Run with coverage
uv run pytest --cov=whosspr

# Run manual E2E tests (interactive, requires user input)
WHOSSPER_MANUAL_TESTS=1 uv run pytest tests/test_e2e_manual.py -v -s

# Or run manual tests directly
python tests/test_e2e_manual.py
```

## Development

### Project Structure

The codebase follows a simplified architecture with only 4 core files:

```
whosspr/
├── __init__.py     # Version and exports
├── cli.py          # Typer-based CLI interface
├── config.py       # Configuration (schema + management)
├── core.py         # Main controller (audio, keyboard, transcription, text insertion)
└── enhancer.py     # Optional LLM text enhancement

tests/
├── conftest.py        # Pytest fixtures
├── test_cli.py        # CLI tests
├── test_config.py     # Configuration tests
├── test_core.py       # Core functionality tests
├── test_enhancer.py   # Enhancement tests
└── test_e2e_manual.py # Interactive manual tests
```

### Key Dependencies

- **sounddevice** - Audio recording (no system dependencies)
- **openai-whisper** - Local speech-to-text
- **pynput** - Keyboard shortcuts
- **pyperclip** - Clipboard operations
- **typer** - CLI framework

### Adding Features

1. Modify the appropriate module in `whosspr/`
2. Add tests in `tests/`
3. Run tests: `uv run pytest`
4. Run manual E2E tests before submitting changes

## Support

For issues and feature requests, please open an issue on GitHub.

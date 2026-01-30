# WhOSSper Flow

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
# 1. Install system dependencies
brew install portaudio

# 2. Install WhOSSper
uv sync

# 3. Create default configuration
uv run whossper config --init

# 4. Check permissions (grant when prompted)
uv run whossper check

# 5. Start dictation service
uv run whossper start
```

**Default shortcuts:**
- Hold `Ctrl+Cmd+1` to record, release to transcribe
- Press `Ctrl+Cmd+2` to toggle recording on/off

For detailed setup instructions, see [Detailed Instructions](#detailed-instructions) below.

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

Apache 2.0

---

# Detailed Instructions

This section covers the complete setup of WhOSSper Flow on macOS, including permissions, dependencies, and first run.

## System Requirements

- **macOS** 10.14 (Mojave) or later
- **Python** 3.10 or later
- **Homebrew** (for installing dependencies)
- At least **2GB RAM** (more for larger Whisper models)
- **Microphone access**

## Step-by-Step Installation

### 1. Install System Dependencies

WhOSSper requires PortAudio for audio recording:

```bash
brew install portaudio
```

### 2. Install Python Dependencies

If using `uv` (recommended):

```bash
uv sync
```

Or with pip:

```bash
pip install -e .
```

### 3. Grant macOS Permissions

WhOSSper requires two macOS permissions to function:

#### Microphone Access

Required for recording your voice.

1. Run `whossper check` - macOS will prompt for microphone access
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

> **Note:** You need to grant Accessibility access to the application that runs WhOSSper (e.g., Terminal.app, iTerm2, VS Code terminal).

### 4. Verify Permissions

Run the permission check command:

```bash
uv run whossper check
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
uv run whossper config --init
```

This creates `whossper.json` in the current directory with default settings.

### Configuration Options

Edit `whossper.json`:

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
uv run whossper start
```

With options:

```bash
# Use a specific model
uv run whossper start --model small

# Specify language
uv run whossper start --language es

# Use MPS (Apple Silicon GPU)
uv run whossper start --device mps

# Enable text enhancement with OpenAI API
uv run whossper start --enhancement --api-key sk-xxx
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

Press `Ctrl+C` in the terminal to stop WhOSSper.

## Text Enhancement (Optional)

WhOSSper can improve transcribed text using an OpenAI-compatible API:

```bash
# Using OpenAI
export OPENAI_API_KEY=sk-your-api-key
uv run whossper start --enhancement

# Using a local LLM (e.g., Ollama)
uv run whossper start --enhancement \
  --api-key ollama \
  --api-base-url http://localhost:11434/v1
```

### Custom System Prompt

Edit `prompts/default_enhancement.txt` to customize how the LLM improves your text.

## Troubleshooting

### "Permission denied" errors

1. Run `uv run whossper check` to see which permissions are missing
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
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=whossper

# Run specific test file
uv run pytest tests/test_integration.py
```

## Development

### Project Structure

```
whossper/
├── audio/          # Audio recording
├── transcription/  # Whisper integration
├── input/          # Text injection & keyboard
├── enhancement/    # OpenAI text enhancement
├── config/         # Configuration management
├── permissions/    # macOS permissions
├── core/           # Main controller
└── cli.py          # CLI interface
```

### Adding Features

1. Create a new module in the appropriate package
2. Add tests in `tests/`
3. Run tests: `uv run pytest`
4. Update documentation as needed

## Support

For issues and feature requests, please open an issue on GitHub.

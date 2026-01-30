"""Configuration schema using Pydantic models.

This module defines the configuration schema for WhOSSper Flow using Pydantic models.
Each configuration option includes a description explaining its purpose.
"""

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class WhisperModelSize(str, Enum):
    """Available Whisper model sizes.
    
    Smaller models are faster but less accurate. Larger models provide better
    transcription quality but require more memory and processing time.
    
    - tiny/tiny.en: ~39M params, fastest, basic accuracy
    - base/base.en: ~74M params, good balance for most uses
    - small/small.en: ~244M params, better accuracy
    - medium/medium.en: ~769M params, high accuracy
    - large variants: ~1.5B params, highest accuracy, slowest
    - turbo: ~809M params, optimized for speed with good accuracy
    """
    TINY = "tiny"
    TINY_EN = "tiny.en"
    BASE = "base"
    BASE_EN = "base.en"
    SMALL = "small"
    SMALL_EN = "small.en"
    MEDIUM = "medium"
    MEDIUM_EN = "medium.en"
    LARGE = "large"
    LARGE_V1 = "large-v1"
    LARGE_V2 = "large-v2"
    LARGE_V3 = "large-v3"
    TURBO = "turbo"


class DeviceType(str, Enum):
    """Device type for Whisper model inference.
    
    - auto: Automatically select best available device
    - cpu: Force CPU inference (slower, always available)
    - mps: Apple Silicon GPU acceleration (recommended for M1/M2/M3 Macs)
    - cuda: NVIDIA GPU acceleration (for systems with CUDA)
    """
    AUTO = "auto"
    CPU = "cpu"
    CUDA = "cuda"
    MPS = "mps"


class WhisperConfig(BaseModel):
    """Whisper transcription configuration.
    
    Controls the Whisper speech-to-text model settings.
    """
    model_size: WhisperModelSize = Field(
        default=WhisperModelSize.BASE,
        description="Size of the Whisper model. Larger models are more accurate but slower. Options: tiny, base, small, medium, large, turbo"
    )
    language: str = Field(
        default="en",
        description="ISO 639-1 language code for transcription (e.g., 'en', 'es', 'fr', 'de'). Use the model's native language for best results."
    )
    device: DeviceType = Field(
        default=DeviceType.AUTO,
        description="Device for inference. 'auto' selects best available, 'mps' for Apple Silicon GPU, 'cuda' for NVIDIA GPU, 'cpu' for CPU-only"
    )
    model_cache_dir: Optional[str] = Field(
        default=None,
        description="Directory where Whisper models are downloaded and cached. If null, uses ~/.cache/whisper. Set this to control disk usage or use a shared cache."
    )


class ShortcutsConfig(BaseModel):
    """Keyboard shortcuts configuration.
    
    Define the global keyboard shortcuts for dictation control.
    Format: modifier+modifier+key (e.g., 'ctrl+cmd+1', 'cmd+shift+d')
    """
    hold_to_dictate: str = Field(
        default="ctrl+cmd+1",
        description="Hold these keys to record, release to transcribe and insert text. Format: modifier+modifier+key"
    )
    toggle_dictation: str = Field(
        default="ctrl+cmd+2",
        description="Press once to start recording, press again to stop and insert text. Format: modifier+modifier+key"
    )


class EnhancementConfig(BaseModel):
    """LLM text enhancement configuration.
    
    Optionally post-process transcribed text using an OpenAI-compatible API
    to fix grammar, remove filler words, and improve readability.
    
    API Key Resolution Priority:
    1. api_key - Direct value (if non-empty)
    2. api_key_helper - Output of shell command
    3. api_key_env_var - Value from environment variable
    """
    enabled: bool = Field(
        default=False,
        description="Enable LLM text enhancement. Requires an API key to be configured."
    )
    api_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="Base URL for OpenAI-compatible API. Change for local LLMs like Ollama (http://localhost:11434/v1)"
    )
    api_key: str = Field(
        default="",
        description="Direct API key value. Highest priority. Leave empty to use api_key_helper or api_key_env_var."
    )
    api_key_helper: Optional[str] = Field(
        default=None,
        description="Shell command to retrieve API key. Runs with 30s timeout. Example: 'op read op://vault/openai/key' for 1Password"
    )
    api_key_env_var: Optional[str] = Field(
        default=None,
        description="Name of environment variable containing API key. Example: 'OPENAI_API_KEY'. Lowest priority."
    )
    model: str = Field(
        default="gpt-4o-mini",
        description="LLM model name for text enhancement. Examples: 'gpt-4o-mini', 'gpt-4o', 'llama3' (for Ollama)"
    )
    system_prompt_file: str = Field(
        default="prompts/default_enhancement.txt",
        description="Path to file containing the system prompt for text enhancement"
    )
    custom_system_prompt: Optional[str] = Field(
        default=None,
        description="Inline custom system prompt. If set, overrides system_prompt_file."
    )


class AudioConfig(BaseModel):
    """Audio recording configuration.
    
    Technical settings for microphone input. Generally don't need adjustment
    unless you have specific audio hardware requirements.
    """
    sample_rate: int = Field(
        default=16000,
        description="Audio sample rate in Hz. 16000 is optimal for Whisper. Higher values don't improve accuracy."
    )
    channels: int = Field(
        default=1,
        description="Number of audio channels. 1 (mono) is recommended for speech recognition."
    )
    chunk_size: int = Field(
        default=1024,
        description="Audio buffer chunk size in samples. Affects latency. Lower = more responsive, higher = more efficient."
    )
    min_recording_duration: float = Field(
        default=0.5,
        description="Minimum recording duration in seconds. Recordings shorter than this are discarded to avoid processing noise."
    )


class WhossperConfig(BaseModel):
    """Main configuration for WhOSSper Flow.
    
    This is the root configuration object containing all settings.
    Save as whossper.json in your project directory.
    """
    whisper: WhisperConfig = Field(
        default_factory=WhisperConfig,
        description="Whisper speech-to-text model settings"
    )
    shortcuts: ShortcutsConfig = Field(
        default_factory=ShortcutsConfig,
        description="Global keyboard shortcut settings"
    )
    enhancement: EnhancementConfig = Field(
        default_factory=EnhancementConfig,
        description="LLM text enhancement settings"
    )
    audio: AudioConfig = Field(
        default_factory=AudioConfig,
        description="Audio recording settings"
    )
    
    # General settings
    tmp_dir: str = Field(
        default="./tmp",
        description="Directory for temporary files (recorded audio WAV files before transcription). These are cleaned up after processing."
    )
    log_level: str = Field(
        default="INFO",
        description="Logging verbosity. Options: DEBUG, INFO, WARNING, ERROR. Use DEBUG for troubleshooting."
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
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
                        "enabled": False,
                        "api_base_url": "https://api.openai.com/v1",
                        "api_key": "",
                        "model": "gpt-4o-mini",
                        "system_prompt_file": "prompts/default_enhancement.txt"
                    },
                    "audio": {
                        "sample_rate": 16000,
                        "channels": 1
                    },
                    "tmp_dir": "./tmp",
                    "log_level": "INFO"
                }
            ]
        }
    }

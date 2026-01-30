"""Configuration schema using Pydantic models."""

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class WhisperModelSize(str, Enum):
    """Available Whisper model sizes."""
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
    """Device type for Whisper model inference."""
    AUTO = "auto"
    CPU = "cpu"
    CUDA = "cuda"
    MPS = "mps"  # Apple Silicon


class WhisperConfig(BaseModel):
    """Whisper transcription configuration."""
    model_size: WhisperModelSize = Field(
        default=WhisperModelSize.BASE,
        description="Size of the Whisper model to use"
    )
    language: str = Field(
        default="en",
        description="Language code for transcription"
    )
    device: DeviceType = Field(
        default=DeviceType.AUTO,
        description="Device to run inference on"
    )
    model_cache_dir: Optional[str] = Field(
        default=None,
        description="Directory to cache downloaded models"
    )


class ShortcutsConfig(BaseModel):
    """Keyboard shortcuts configuration."""
    hold_to_dictate: str = Field(
        default="ctrl+shift",
        description="Key combination to hold for dictation"
    )
    toggle_dictation: str = Field(
        default="ctrl+alt+d",
        description="Key combination to toggle dictation on/off"
    )


class EnhancementConfig(BaseModel):
    """OpenAI-compatible API enhancement configuration."""
    enabled: bool = Field(
        default=False,
        description="Whether to enable text enhancement"
    )
    api_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="Base URL for OpenAI-compatible API"
    )
    api_key: str = Field(
        default="",
        description="API key for authentication"
    )
    model: str = Field(
        default="gpt-4o-mini",
        description="Model to use for text enhancement"
    )
    system_prompt_file: str = Field(
        default="prompts/default_enhancement.txt",
        description="Path to system prompt file"
    )
    custom_system_prompt: Optional[str] = Field(
        default=None,
        description="Custom system prompt (overrides file)"
    )


class AudioConfig(BaseModel):
    """Audio recording configuration."""
    sample_rate: int = Field(
        default=16000,
        description="Audio sample rate in Hz"
    )
    channels: int = Field(
        default=1,
        description="Number of audio channels"
    )
    chunk_size: int = Field(
        default=1024,
        description="Audio chunk size for recording"
    )
    min_recording_duration: float = Field(
        default=0.5,
        description="Minimum recording duration in seconds"
    )


class WhossperConfig(BaseModel):
    """Main configuration for WhOSSper Flow."""
    whisper: WhisperConfig = Field(default_factory=WhisperConfig)
    shortcuts: ShortcutsConfig = Field(default_factory=ShortcutsConfig)
    enhancement: EnhancementConfig = Field(default_factory=EnhancementConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    
    # General settings
    tmp_dir: str = Field(
        default="./tmp",
        description="Directory for temporary files"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level"
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
                        "hold_to_dictate": "ctrl+shift",
                        "toggle_dictation": "ctrl+alt+d"
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

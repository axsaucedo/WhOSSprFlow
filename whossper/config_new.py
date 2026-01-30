"""WhOSSper Configuration - Schema and management in one module."""

import json
import logging
import os
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class ModelSize(str, Enum):
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
    LARGE_V2 = "large-v2"
    LARGE_V3 = "large-v3"
    TURBO = "turbo"


class DeviceType(str, Enum):
    """Device type for Whisper inference."""
    AUTO = "auto"
    CPU = "cpu"
    CUDA = "cuda"
    MPS = "mps"


# =============================================================================
# Config Sections
# =============================================================================

class WhisperConfig(BaseModel):
    """Whisper transcription settings."""
    model_size: ModelSize = Field(default=ModelSize.BASE)
    language: str = Field(default="en")
    device: DeviceType = Field(default=DeviceType.AUTO)
    model_cache_dir: Optional[str] = Field(default=None)


class ShortcutsConfig(BaseModel):
    """Keyboard shortcuts settings."""
    hold_to_dictate: str = Field(default="ctrl+cmd+1")
    toggle_dictation: str = Field(default="ctrl+cmd+2")


class EnhancementConfig(BaseModel):
    """LLM text enhancement settings."""
    enabled: bool = Field(default=False)
    api_base_url: str = Field(default="https://api.openai.com/v1")
    api_key: str = Field(default="")
    api_key_helper: Optional[str] = Field(default=None)
    api_key_env_var: Optional[str] = Field(default=None)
    model: str = Field(default="gpt-4o-mini")
    system_prompt_file: str = Field(default="prompts/default_enhancement.txt")
    custom_system_prompt: Optional[str] = Field(default=None)


class AudioConfig(BaseModel):
    """Audio recording settings."""
    sample_rate: int = Field(default=16000)
    channels: int = Field(default=1)
    min_duration: float = Field(default=0.5)


# =============================================================================
# Main Config
# =============================================================================

class Config(BaseModel):
    """Main WhOSSper configuration."""
    whisper: WhisperConfig = Field(default_factory=WhisperConfig)
    shortcuts: ShortcutsConfig = Field(default_factory=ShortcutsConfig)
    enhancement: EnhancementConfig = Field(default_factory=EnhancementConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    tmp_dir: str = Field(default="./tmp")
    log_level: str = Field(default="INFO")


# =============================================================================
# Config Loading/Saving
# =============================================================================

DEFAULT_CONFIG_PATHS = [
    Path("whossper.json"),
    Path("config.json"),
    Path.home() / ".config" / "whossper" / "config.json",
]


def find_config_file(explicit_path: Optional[str] = None) -> Optional[Path]:
    """Find the first existing config file."""
    if explicit_path:
        path = Path(explicit_path)
        if path.exists():
            return path
    
    for path in DEFAULT_CONFIG_PATHS:
        if path.exists():
            return path
    
    return None


def load_config(path: Optional[str] = None) -> Config:
    """Load configuration from file or return defaults.
    
    Args:
        path: Optional explicit path to config file.
        
    Returns:
        Config instance.
    """
    config_file = find_config_file(path)
    
    if config_file:
        logger.info(f"Loading config from {config_file}")
        try:
            with open(config_file, "r") as f:
                data = json.load(f)
            return Config.model_validate(data)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to load config: {e}, using defaults")
            return Config()
    else:
        logger.info("No config file found, using defaults")
        return Config()


def save_config(config: Config, path: str) -> Path:
    """Save configuration to file.
    
    Args:
        config: Configuration to save.
        path: Path to save to.
        
    Returns:
        Path where config was saved.
    """
    save_path = Path(path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(save_path, "w") as f:
        json.dump(config.model_dump(), f, indent=2)
    
    logger.info(f"Saved config to {save_path}")
    return save_path


def create_default_config(path: str) -> Path:
    """Create a default config file.
    
    Args:
        path: Path to create config at.
        
    Returns:
        Path to created file.
    """
    return save_config(Config(), path)


# =============================================================================
# Backward Compatibility Aliases
# =============================================================================

# Keep old names for compatibility during transition
WhisperModelSize = ModelSize
WhossperConfig = Config

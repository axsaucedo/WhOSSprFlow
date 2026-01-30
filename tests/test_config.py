"""Tests for simplified configuration module."""

import json
import pytest
from pathlib import Path

from whossper.config import (
    Config,
    WhisperConfig,
    ShortcutsConfig,
    EnhancementConfig,
    AudioConfig,
    ModelSize,
    DeviceType,
    load_config,
    save_config,
    create_default_config,
    find_config_file,
)


class TestModelSize:
    """Tests for ModelSize enum."""
    
    def test_has_expected_values(self):
        """Test enum has all expected model sizes."""
        assert ModelSize.TINY.value == "tiny"
        assert ModelSize.BASE.value == "base"
        assert ModelSize.SMALL.value == "small"
        assert ModelSize.MEDIUM.value == "medium"
        assert ModelSize.LARGE.value == "large"
        assert ModelSize.TURBO.value == "turbo"
    
    def test_from_string(self):
        """Test creating from string."""
        assert ModelSize("base") == ModelSize.BASE
        assert ModelSize("turbo") == ModelSize.TURBO


class TestDeviceType:
    """Tests for DeviceType enum."""
    
    def test_has_expected_values(self):
        """Test enum has all expected device types."""
        assert DeviceType.AUTO.value == "auto"
        assert DeviceType.CPU.value == "cpu"
        assert DeviceType.MPS.value == "mps"
        assert DeviceType.CUDA.value == "cuda"


class TestWhisperConfig:
    """Tests for WhisperConfig."""
    
    def test_defaults(self):
        """Test default values."""
        config = WhisperConfig()
        assert config.model_size == ModelSize.BASE
        assert config.language == "en"
        assert config.device == DeviceType.AUTO
        assert config.model_cache_dir is None
    
    def test_custom_values(self):
        """Test custom values."""
        config = WhisperConfig(
            model_size=ModelSize.LARGE,
            language="es",
            device=DeviceType.MPS
        )
        assert config.model_size == ModelSize.LARGE
        assert config.language == "es"
        assert config.device == DeviceType.MPS


class TestShortcutsConfig:
    """Tests for ShortcutsConfig."""
    
    def test_defaults(self):
        """Test default shortcuts."""
        config = ShortcutsConfig()
        assert config.hold_to_dictate == "ctrl+cmd+1"
        assert config.toggle_dictation == "ctrl+cmd+2"
    
    def test_custom_shortcuts(self):
        """Test custom shortcuts."""
        config = ShortcutsConfig(
            hold_to_dictate="cmd+space",
            toggle_dictation="cmd+d"
        )
        assert config.hold_to_dictate == "cmd+space"
        assert config.toggle_dictation == "cmd+d"


class TestEnhancementConfig:
    """Tests for EnhancementConfig."""
    
    def test_disabled_by_default(self):
        """Test enhancement is disabled by default."""
        config = EnhancementConfig()
        assert config.enabled is False
    
    def test_default_api_settings(self):
        """Test default API settings."""
        config = EnhancementConfig()
        assert config.api_base_url == "https://api.openai.com/v1"
        assert config.model == "gpt-4o-mini"
    
    def test_api_key_sources(self):
        """Test API key source fields exist."""
        config = EnhancementConfig()
        assert config.api_key == ""
        assert config.api_key_helper is None
        assert config.api_key_env_var is None


class TestAudioConfig:
    """Tests for AudioConfig."""
    
    def test_defaults(self):
        """Test default audio settings."""
        config = AudioConfig()
        assert config.sample_rate == 16000
        assert config.channels == 1
        assert config.min_duration == 0.5


class TestConfig:
    """Tests for main Config."""
    
    def test_defaults(self):
        """Test default config has all sections."""
        config = Config()
        assert isinstance(config.whisper, WhisperConfig)
        assert isinstance(config.shortcuts, ShortcutsConfig)
        assert isinstance(config.enhancement, EnhancementConfig)
        assert isinstance(config.audio, AudioConfig)
        assert config.tmp_dir == "./tmp"
        assert config.log_level == "INFO"
    
    def test_json_roundtrip(self):
        """Test config can be serialized and deserialized."""
        config = Config(
            whisper=WhisperConfig(model_size=ModelSize.SMALL),
            tmp_dir="/tmp/test"
        )
        
        # Serialize
        data = config.model_dump()
        json_str = json.dumps(data)
        
        # Deserialize
        loaded_data = json.loads(json_str)
        loaded_config = Config.model_validate(loaded_data)
        
        assert loaded_config.whisper.model_size == ModelSize.SMALL
        assert loaded_config.tmp_dir == "/tmp/test"


class TestLoadConfig:
    """Tests for load_config function."""
    
    def test_returns_defaults_when_no_file(self, tmp_path):
        """Test returns defaults when no config file exists."""
        config = load_config(str(tmp_path / "nonexistent.json"))
        assert isinstance(config, Config)
        assert config.whisper.model_size == ModelSize.BASE
    
    def test_loads_from_file(self, tmp_path):
        """Test loads config from file."""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "whisper": {"model_size": "small", "language": "es"}
        }))
        
        config = load_config(str(config_file))
        assert config.whisper.model_size == ModelSize.SMALL
        assert config.whisper.language == "es"
    
    def test_handles_invalid_json(self, tmp_path):
        """Test handles invalid JSON gracefully."""
        config_file = tmp_path / "bad.json"
        config_file.write_text("not valid json {")
        
        config = load_config(str(config_file))
        assert isinstance(config, Config)  # Falls back to defaults


class TestSaveConfig:
    """Tests for save_config function."""
    
    def test_saves_to_file(self, tmp_path):
        """Test saves config to file."""
        config = Config(whisper=WhisperConfig(model_size=ModelSize.TURBO))
        path = save_config(config, str(tmp_path / "out.json"))
        
        assert path.exists()
        
        # Verify content
        with open(path) as f:
            data = json.load(f)
        assert data["whisper"]["model_size"] == "turbo"
    
    def test_creates_parent_directories(self, tmp_path):
        """Test creates parent directories."""
        path = tmp_path / "subdir" / "deep" / "config.json"
        save_config(Config(), str(path))
        assert path.exists()


class TestCreateDefaultConfig:
    """Tests for create_default_config function."""
    
    def test_creates_default_config(self, tmp_path):
        """Test creates valid default config."""
        config = create_default_config()
        
        # Should be a valid Config with defaults
        assert isinstance(config, Config)
        assert config.whisper.model_size == ModelSize.BASE
        
        # Should be saveable
        path = tmp_path / "default.json"
        save_config(config, str(path))
        assert path.exists()


class TestFindConfigFile:
    """Tests for find_config_file function."""
    
    def test_finds_explicit_path(self, tmp_path):
        """Test finds explicit path when it exists."""
        config_file = tmp_path / "my_config.json"
        config_file.write_text("{}")
        
        result = find_config_file(str(config_file))
        assert result == config_file
    
    def test_returns_none_for_nonexistent(self, tmp_path):
        """Test returns None for nonexistent explicit path."""
        result = find_config_file(str(tmp_path / "nonexistent.json"))
        assert result is None

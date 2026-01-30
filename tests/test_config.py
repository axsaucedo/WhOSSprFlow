"""Tests for configuration schema and manager."""

import json
import pytest
from pathlib import Path

from whossper.config.schema import (
    WhossperConfig,
    WhisperConfig,
    ShortcutsConfig,
    EnhancementConfig,
    AudioConfig,
    WhisperModelSize,
    DeviceType,
)
from whossper.config.manager import ConfigManager


class TestWhisperConfig:
    """Tests for WhisperConfig schema."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = WhisperConfig()
        assert config.model_size == WhisperModelSize.BASE
        assert config.language == "en"
        assert config.device == DeviceType.AUTO
        assert config.model_cache_dir is None
    
    def test_custom_values(self):
        """Test setting custom configuration values."""
        config = WhisperConfig(
            model_size=WhisperModelSize.LARGE,
            language="es",
            device=DeviceType.MPS
        )
        assert config.model_size == WhisperModelSize.LARGE
        assert config.language == "es"
        assert config.device == DeviceType.MPS
    
    def test_model_size_enum(self):
        """Test all model size enum values."""
        sizes = [e.value for e in WhisperModelSize]
        assert "tiny" in sizes
        assert "base" in sizes
        assert "small" in sizes
        assert "medium" in sizes
        assert "large" in sizes
        assert "turbo" in sizes


class TestShortcutsConfig:
    """Tests for ShortcutsConfig schema."""
    
    def test_default_values(self):
        """Test default shortcut values."""
        config = ShortcutsConfig()
        assert config.hold_to_dictate == "ctrl+shift"
        assert config.toggle_dictation == "ctrl+alt+d"
    
    def test_custom_shortcuts(self):
        """Test setting custom shortcuts."""
        config = ShortcutsConfig(
            hold_to_dictate="cmd+space",
            toggle_dictation="cmd+alt+r"
        )
        assert config.hold_to_dictate == "cmd+space"
        assert config.toggle_dictation == "cmd+alt+r"


class TestEnhancementConfig:
    """Tests for EnhancementConfig schema."""
    
    def test_default_disabled(self):
        """Test enhancement is disabled by default."""
        config = EnhancementConfig()
        assert config.enabled is False
    
    def test_default_api_url(self):
        """Test default API URL."""
        config = EnhancementConfig()
        assert config.api_base_url == "https://api.openai.com/v1"
    
    def test_custom_api_settings(self):
        """Test custom API settings."""
        config = EnhancementConfig(
            enabled=True,
            api_base_url="http://localhost:8080/v1",
            api_key="test-key",
            model="gpt-4"
        )
        assert config.enabled is True
        assert config.api_base_url == "http://localhost:8080/v1"
        assert config.api_key == "test-key"
        assert config.model == "gpt-4"


class TestAudioConfig:
    """Tests for AudioConfig schema."""
    
    def test_default_values(self):
        """Test default audio configuration."""
        config = AudioConfig()
        assert config.sample_rate == 16000
        assert config.channels == 1
        assert config.chunk_size == 1024
        assert config.min_recording_duration == 0.5
    
    def test_custom_values(self):
        """Test custom audio configuration."""
        config = AudioConfig(
            sample_rate=44100,
            channels=2,
            chunk_size=2048
        )
        assert config.sample_rate == 44100
        assert config.channels == 2
        assert config.chunk_size == 2048


class TestWhossperConfig:
    """Tests for main WhossperConfig schema."""
    
    def test_default_config(self):
        """Test default complete configuration."""
        config = WhossperConfig()
        assert isinstance(config.whisper, WhisperConfig)
        assert isinstance(config.shortcuts, ShortcutsConfig)
        assert isinstance(config.enhancement, EnhancementConfig)
        assert isinstance(config.audio, AudioConfig)
        assert config.tmp_dir == "./tmp"
        assert config.log_level == "INFO"
    
    def test_json_serialization(self):
        """Test configuration can be serialized to JSON."""
        config = WhossperConfig()
        data = config.model_dump()
        
        assert "whisper" in data
        assert "shortcuts" in data
        assert "enhancement" in data
        assert "audio" in data
        
        # Verify it's JSON serializable
        json_str = json.dumps(data)
        assert json_str is not None
    
    def test_json_deserialization(self, sample_config_data):
        """Test configuration can be loaded from JSON data."""
        config = WhossperConfig.model_validate(sample_config_data)
        
        assert config.whisper.model_size == WhisperModelSize.BASE
        assert config.whisper.language == "en"
        assert config.shortcuts.hold_to_dictate == "ctrl+shift"
        assert config.enhancement.enabled is False


class TestConfigManager:
    """Tests for ConfigManager."""
    
    def test_load_default_when_no_file(self, tmp_dir):
        """Test loading default config when no file exists."""
        manager = ConfigManager(config_path=tmp_dir / "nonexistent.json")
        config = manager.load()
        
        assert isinstance(config, WhossperConfig)
        assert config.whisper.model_size == WhisperModelSize.BASE
    
    def test_load_from_file(self, config_file):
        """Test loading config from file."""
        manager = ConfigManager(config_path=config_file)
        config = manager.load()
        
        assert isinstance(config, WhossperConfig)
        assert config.whisper.language == "en"
    
    def test_save_config(self, tmp_dir):
        """Test saving configuration to file."""
        manager = ConfigManager()
        config = WhossperConfig(
            whisper=WhisperConfig(model_size=WhisperModelSize.SMALL)
        )
        
        save_path = tmp_dir / "saved_config.json"
        result = manager.save(config, save_path)
        
        assert result == save_path
        assert save_path.exists()
        
        # Verify saved content
        with open(save_path) as f:
            data = json.load(f)
        assert data["whisper"]["model_size"] == "small"
    
    def test_get_config_lazy_load(self, config_file):
        """Test get_config lazily loads configuration."""
        manager = ConfigManager(config_path=config_file)
        
        # First call should load
        config1 = manager.get_config()
        assert config1 is not None
        
        # Second call should return cached
        config2 = manager.get_config()
        assert config1 is config2
    
    def test_create_default_config_file(self, tmp_dir):
        """Test creating a default config file."""
        config_path = tmp_dir / "new_config.json"
        result = ConfigManager.create_default_config_file(config_path)
        
        assert result == config_path
        assert config_path.exists()
        
        # Verify it's valid JSON with expected structure
        with open(config_path) as f:
            data = json.load(f)
        assert "whisper" in data
        assert "shortcuts" in data
    
    def test_load_invalid_json(self, tmp_dir):
        """Test loading falls back to defaults on invalid JSON."""
        invalid_config = tmp_dir / "invalid.json"
        with open(invalid_config, "w") as f:
            f.write("not valid json {")
        
        manager = ConfigManager(config_path=invalid_config)
        config = manager.load()
        
        # Should fall back to defaults
        assert isinstance(config, WhossperConfig)
        assert config.whisper.model_size == WhisperModelSize.BASE

"""Test fixtures and configuration for pytest."""

import pytest
from pathlib import Path
import tempfile
import json


@pytest.fixture
def tmp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config_data():
    """Return sample configuration data."""
    return {
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


@pytest.fixture
def config_file(tmp_dir, sample_config_data):
    """Create a temporary config file."""
    config_path = tmp_dir / "whossper.json"
    with open(config_path, "w") as f:
        json.dump(sample_config_data, f)
    return config_path


@pytest.fixture
def fixtures_dir():
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"

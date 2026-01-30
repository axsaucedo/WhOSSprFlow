"""Tests for CLI module."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

from whossper.cli import app
from whossper.permissions.mac_permissions import PermissionStatus


runner = CliRunner()


class TestCliVersion:
    """Tests for version command."""
    
    def test_version_flag(self):
        """Test --version flag."""
        result = runner.invoke(app, ["--version"])
        
        assert result.exit_code == 0
        assert "WhOSSper Flow version" in result.output
    
    def test_version_short_flag(self):
        """Test -v flag."""
        result = runner.invoke(app, ["-v"])
        
        assert result.exit_code == 0
        assert "WhOSSper Flow version" in result.output


class TestCliCheck:
    """Tests for check command."""
    
    def test_check_command(self):
        """Test check command runs."""
        with patch('whossper.cli.PermissionsManager') as mock_perms:
            mock_instance = MagicMock()
            mock_perms.return_value = mock_instance
            mock_instance.check_all_permissions.return_value = {
                'microphone': PermissionStatus.GRANTED,
                'accessibility': PermissionStatus.GRANTED,
            }
            
            result = runner.invoke(app, ["check"])
            
            assert result.exit_code == 0
            assert "Permission Check" in result.output
    
    def test_check_shows_granted(self):
        """Test check shows granted permissions."""
        with patch('whossper.cli.PermissionsManager') as mock_perms:
            mock_instance = MagicMock()
            mock_perms.return_value = mock_instance
            mock_instance.check_all_permissions.return_value = {
                'microphone': PermissionStatus.GRANTED,
                'accessibility': PermissionStatus.GRANTED,
            }
            
            result = runner.invoke(app, ["check"])
            
            assert "Granted" in result.output
    
    def test_check_shows_denied(self):
        """Test check shows denied permissions."""
        with patch('whossper.cli.PermissionsManager') as mock_perms:
            mock_instance = MagicMock()
            mock_perms.return_value = mock_instance
            mock_instance.check_all_permissions.return_value = {
                'microphone': PermissionStatus.DENIED,
                'accessibility': PermissionStatus.GRANTED,
            }
            mock_instance.get_permission_instructions.return_value = {
                'microphone': 'Go to System Preferences > Security & Privacy > Privacy > Microphone',
            }
            
            result = runner.invoke(app, ["check"], input="n\n")
            
            assert "Denied" in result.output


class TestCliConfig:
    """Tests for config command."""
    
    def test_config_init(self, tmp_path):
        """Test config --init creates file."""
        config_path = tmp_path / "test_config.json"
        
        result = runner.invoke(app, ["config", "--init", "--path", str(config_path)])
        
        assert result.exit_code == 0
        assert config_path.exists()
        assert "Created config file" in result.output
    
    def test_config_show(self, tmp_path):
        """Test config --show displays configuration."""
        config_path = tmp_path / "test_config.json"
        config_data = {
            "whisper": {"model_size": "tiny", "language": "en"},
        }
        config_path.write_text(json.dumps(config_data))
        
        result = runner.invoke(app, ["config", "--show", "--path", str(config_path)])
        
        assert result.exit_code == 0
        assert "tiny" in result.output
    
    def test_config_set_model(self, tmp_path):
        """Test config --model sets model."""
        config_path = tmp_path / "test_config.json"
        config_path.write_text('{}')
        
        result = runner.invoke(app, ["config", "--model", "small", "--path", str(config_path)])
        
        assert result.exit_code == 0
        assert "Configuration updated" in result.output
        
        # Verify saved
        saved = json.loads(config_path.read_text())
        assert saved["whisper"]["model_size"] == "small"
    
    def test_config_set_invalid_model(self, tmp_path):
        """Test config with invalid model fails."""
        config_path = tmp_path / "test_config.json"
        config_path.write_text('{}')
        
        result = runner.invoke(app, ["config", "--model", "invalid", "--path", str(config_path)])
        
        assert result.exit_code == 1
        assert "Invalid model" in result.output
    
    def test_config_set_language(self, tmp_path):
        """Test config --language sets language."""
        config_path = tmp_path / "test_config.json"
        config_path.write_text('{}')
        
        result = runner.invoke(app, ["config", "--language", "es", "--path", str(config_path)])
        
        assert result.exit_code == 0
        
        saved = json.loads(config_path.read_text())
        assert saved["whisper"]["language"] == "es"
    
    def test_config_enable_enhancement(self, tmp_path):
        """Test config --enhancement enables enhancement."""
        config_path = tmp_path / "test_config.json"
        config_path.write_text('{}')
        
        result = runner.invoke(app, ["config", "--enhancement", "--path", str(config_path)])
        
        assert result.exit_code == 0
        
        saved = json.loads(config_path.read_text())
        assert saved["enhancement"]["enabled"] is True


class TestCliModels:
    """Tests for models command."""
    
    def test_models_lists_all(self):
        """Test models command lists all models."""
        result = runner.invoke(app, ["models"])
        
        assert result.exit_code == 0
        assert "tiny" in result.output
        assert "base" in result.output
        assert "small" in result.output
        assert "medium" in result.output
        assert "large" in result.output
        assert "turbo" in result.output
    
    def test_models_shows_parameters(self):
        """Test models command shows parameters."""
        result = runner.invoke(app, ["models"])
        
        assert "Parameters" in result.output
        assert "VRAM" in result.output


class TestCliStart:
    """Tests for start command."""
    
    def test_start_with_invalid_model(self):
        """Test start with invalid model fails."""
        result = runner.invoke(app, ["start", "--model", "invalid"])
        
        assert result.exit_code == 1
        assert "Invalid model size" in result.output
    
    def test_start_with_invalid_device(self):
        """Test start with invalid device fails."""
        result = runner.invoke(app, ["start", "--device", "invalid"])
        
        assert result.exit_code == 1
        assert "Invalid device" in result.output
    
    def test_start_permission_denied_cancel(self, tmp_path):
        """Test start when permissions denied and user cancels."""
        config_path = tmp_path / "config.json"
        config_path.write_text('{}')
        
        with patch('whossper.cli.PermissionsManager') as mock_perms:
            mock_instance = MagicMock()
            mock_perms.return_value = mock_instance
            mock_instance.check_all_permissions.return_value = {
                'microphone': PermissionStatus.DENIED,
                'accessibility': PermissionStatus.DENIED,
            }
            
            result = runner.invoke(app, [
                "start",
                "--config", str(config_path),
            ], input="n\n")
            
            assert result.exit_code == 1
    
    def test_start_skip_permission_check(self, tmp_path):
        """Test start with --skip-permission-check."""
        config_path = tmp_path / "config.json"
        config_path.write_text('{}')
        
        with patch('whossper.cli.DictationController') as mock_controller, \
             patch('whossper.cli.signal') as mock_signal:
            mock_instance = MagicMock()
            mock_controller.return_value = mock_instance
            mock_instance.start.return_value = True
            
            # Simulate immediate interrupt
            def raise_exit(*args, **kwargs):
                raise SystemExit(0)
            mock_signal.pause.side_effect = raise_exit
            
            result = runner.invoke(app, [
                "start",
                "--config", str(config_path),
                "--skip-permission-check",
            ])
            
            # Should have tried to start
            mock_instance.start.assert_called_once()
    
    def test_start_applies_cli_overrides(self, tmp_path):
        """Test start applies command-line overrides."""
        config_path = tmp_path / "config.json"
        config_path.write_text('{}')
        
        with patch('whossper.cli.DictationController') as mock_controller, \
             patch('whossper.cli.signal') as mock_signal:
            mock_instance = MagicMock()
            mock_controller.return_value = mock_instance
            mock_instance.start.return_value = True
            
            def raise_exit(*args, **kwargs):
                raise SystemExit(0)
            mock_signal.pause.side_effect = raise_exit
            
            result = runner.invoke(app, [
                "start",
                "--config", str(config_path),
                "--skip-permission-check",
                "--model", "small",
                "--language", "es",
                "--hold-shortcut", "ctrl+alt",
            ])
            
            # Check the config passed to controller
            call_args = mock_controller.call_args
            cfg = call_args[0][0]  # First positional arg
            
            assert cfg.whisper.model_size.value == "small"
            assert cfg.whisper.language == "es"
            assert cfg.shortcuts.hold_to_dictate == "ctrl+alt"
    
    def test_start_fails_when_controller_fails(self, tmp_path):
        """Test start fails when controller fails to start."""
        config_path = tmp_path / "config.json"
        config_path.write_text('{}')
        
        with patch('whossper.cli.DictationController') as mock_controller:
            mock_instance = MagicMock()
            mock_controller.return_value = mock_instance
            mock_instance.start.return_value = False
            
            result = runner.invoke(app, [
                "start",
                "--config", str(config_path),
                "--skip-permission-check",
            ])
            
            assert result.exit_code == 1
            assert "Failed to start" in result.output


class TestCliHelp:
    """Tests for help functionality."""
    
    def test_main_help(self):
        """Test main help."""
        result = runner.invoke(app, ["--help"])
        
        assert result.exit_code == 0
        assert "WhOSSper Flow" in result.output
        assert "start" in result.output
        assert "config" in result.output
        assert "check" in result.output
    
    def test_start_help(self):
        """Test start help."""
        result = runner.invoke(app, ["start", "--help"])
        
        assert result.exit_code == 0
        assert "--model" in result.output
        assert "--language" in result.output
        assert "--config" in result.output
    
    def test_config_help(self):
        """Test config help."""
        result = runner.invoke(app, ["config", "--help"])
        
        assert result.exit_code == 0
        assert "--init" in result.output
        assert "--show" in result.output
    
    def test_check_help(self):
        """Test check help."""
        result = runner.invoke(app, ["check", "--help"])
        
        assert result.exit_code == 0
        assert "permission" in result.output.lower()

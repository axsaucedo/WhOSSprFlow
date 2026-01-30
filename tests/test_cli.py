"""Tests for whossper.cli module."""

import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from pathlib import Path

from whossper.cli import app
from whossper import __version__


runner = CliRunner()


class TestVersionCommand:
    """Tests for version option."""
    
    def test_version_flag(self):
        """Test --version flag."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.stdout
    
    def test_version_short_flag(self):
        """Test -v flag."""
        result = runner.invoke(app, ["-v"])
        assert result.exit_code == 0
        assert "WhOSSper Flow version" in result.stdout


class TestCheckCommand:
    """Tests for check command."""
    
    @patch("whossper.cli.check_permissions")
    def test_check_all_granted(self, mock_check):
        """Test check when all permissions granted."""
        from whossper.core import PermissionStatus
        mock_check.return_value = {
            "microphone": PermissionStatus.GRANTED,
            "accessibility": PermissionStatus.GRANTED,
        }
        
        result = runner.invoke(app, ["check"])
        assert result.exit_code == 0
        assert "All permissions granted" in result.stdout
    
    @patch("whossper.cli.check_permissions")
    def test_check_denied(self, mock_check):
        """Test check with denied permissions."""
        from whossper.core import PermissionStatus
        mock_check.return_value = {
            "microphone": PermissionStatus.DENIED,
            "accessibility": PermissionStatus.GRANTED,
        }
        
        result = runner.invoke(app, ["check"])
        assert result.exit_code == 0
        assert "Denied" in result.stdout


class TestConfigCommand:
    """Tests for config command."""
    
    def test_config_show(self, tmp_path):
        """Test showing config."""
        result = runner.invoke(app, ["config", "--show"])
        assert result.exit_code == 0
        assert "Whisper Model" in result.stdout
        assert "Language" in result.stdout
    
    def test_config_init(self, tmp_path):
        """Test creating config file."""
        config_file = tmp_path / "test.json"
        
        result = runner.invoke(app, ["config", "--init", "--path", str(config_file)])
        assert result.exit_code == 0
        assert config_file.exists()
        assert "Created config file" in result.stdout


class TestModelsCommand:
    """Tests for models command."""
    
    def test_models_list(self):
        """Test listing models."""
        result = runner.invoke(app, ["models"])
        assert result.exit_code == 0
        assert "tiny" in result.stdout
        assert "base" in result.stdout
        assert "large" in result.stdout
        assert "turbo" in result.stdout


class TestStartCommand:
    """Tests for start command (mocked)."""
    
    @patch("whossper.cli.DictationController")
    @patch("whossper.cli.check_permissions")
    def test_start_missing_permissions_decline(self, mock_perms, mock_controller):
        """Test start with missing permissions, user declines."""
        from whossper.core import PermissionStatus
        mock_perms.return_value = {
            "microphone": PermissionStatus.DENIED,
            "accessibility": PermissionStatus.GRANTED,
        }
        
        result = runner.invoke(app, ["start"], input="n\n")
        assert result.exit_code == 1
    
    @patch("whossper.cli.DictationController")
    @patch("whossper.cli.check_permissions")
    def test_start_skip_permission_check(self, mock_perms, mock_controller):
        """Test start with --skip-permission-check."""
        from whossper.core import PermissionStatus
        mock_perms.return_value = {
            "microphone": PermissionStatus.DENIED,
            "accessibility": PermissionStatus.DENIED,
        }
        
        # Make controller.start() fail so we don't enter infinite loop
        mock_controller.return_value.start.return_value = False
        
        result = runner.invoke(app, ["start", "--skip-permission-check"])
        
        # Should not call check_permissions when skipping
        # Controller start fails, but permissions were skipped
        assert mock_controller.called
    
    @patch("whossper.cli.DictationController")
    @patch("whossper.cli.check_permissions")
    def test_start_invalid_model(self, mock_perms, mock_controller):
        """Test start with invalid model."""
        from whossper.core import PermissionStatus
        mock_perms.return_value = {
            "microphone": PermissionStatus.GRANTED,
            "accessibility": PermissionStatus.GRANTED,
        }
        
        result = runner.invoke(app, ["start", "--model", "invalid-model"])
        assert result.exit_code == 1
        assert "Invalid model" in result.stdout
    
    @patch("whossper.cli.DictationController")
    @patch("whossper.cli.check_permissions")
    def test_start_with_config_file(self, mock_perms, mock_controller, tmp_path):
        """Test start with config file."""
        from whossper.core import PermissionStatus
        from whossper.config import create_default_config, save_config
        
        mock_perms.return_value = {
            "microphone": PermissionStatus.GRANTED,
            "accessibility": PermissionStatus.GRANTED,
        }
        mock_controller.return_value.start.return_value = False
        
        # Create config
        config_file = tmp_path / "config.json"
        cfg = create_default_config()
        save_config(cfg, str(config_file))
        
        result = runner.invoke(app, ["start", "--config", str(config_file)])
        
        assert mock_controller.called


class TestHelpOutput:
    """Tests for help output."""
    
    def test_main_help(self):
        """Test main help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "WhOSSper Flow" in result.stdout
    
    def test_start_help(self):
        """Test start command help."""
        result = runner.invoke(app, ["start", "--help"])
        assert result.exit_code == 0
        assert "config" in result.stdout
        assert "model" in result.stdout
    
    def test_check_help(self):
        """Test check command help."""
        result = runner.invoke(app, ["check", "--help"])
        assert result.exit_code == 0
        assert "permissions" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

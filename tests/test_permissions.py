"""Tests for permissions manager module."""

import sys
import pytest
from unittest.mock import MagicMock, patch

from whossper.permissions.mac_permissions import (
    PermissionsManager,
    PermissionStatus,
)


class TestPermissionStatus:
    """Tests for PermissionStatus enum."""
    
    def test_granted_value(self):
        """Test GRANTED status value."""
        assert PermissionStatus.GRANTED.value == "granted"
    
    def test_denied_value(self):
        """Test DENIED status value."""
        assert PermissionStatus.DENIED.value == "denied"
    
    def test_unknown_value(self):
        """Test UNKNOWN status value."""
        assert PermissionStatus.UNKNOWN.value == "unknown"
    
    def test_not_applicable_value(self):
        """Test NOT_APPLICABLE status value."""
        assert PermissionStatus.NOT_APPLICABLE.value == "not_applicable"


class TestPermissionsManagerInit:
    """Tests for PermissionsManager initialization."""
    
    def test_initialization(self):
        """Test manager initializes correctly."""
        manager = PermissionsManager()
        assert manager is not None
    
    def test_is_macos_property(self):
        """Test is_macos property matches platform."""
        manager = PermissionsManager()
        assert manager.is_macos == (sys.platform == "darwin")


class TestMicrophonePermission:
    """Tests for microphone permission checking."""
    
    def test_non_macos_returns_not_applicable(self):
        """Test non-macOS returns NOT_APPLICABLE."""
        manager = PermissionsManager()
        # Manually set the internal flag
        manager._is_macos = False
        
        result = manager.check_microphone_permission()
        
        assert result == PermissionStatus.NOT_APPLICABLE
    
    @patch('pyaudio.PyAudio')
    def test_microphone_fallback_granted(self, mock_pyaudio_class):
        """Test microphone fallback returns GRANTED on success."""
        mock_audio = MagicMock()
        mock_pyaudio_class.return_value = mock_audio
        mock_stream = MagicMock()
        mock_audio.open.return_value = mock_stream
        
        manager = PermissionsManager()
        result = manager._check_microphone_fallback()
        
        assert result == PermissionStatus.GRANTED
    
    @patch('pyaudio.PyAudio')
    def test_microphone_fallback_denied(self, mock_pyaudio_class):
        """Test microphone fallback returns DENIED on error."""
        mock_pyaudio_class.side_effect = Exception("No microphone")
        
        manager = PermissionsManager()
        result = manager._check_microphone_fallback()
        
        assert result == PermissionStatus.DENIED


class TestAccessibilityPermission:
    """Tests for accessibility permission checking."""
    
    def test_non_macos_returns_not_applicable(self):
        """Test non-macOS returns NOT_APPLICABLE."""
        manager = PermissionsManager()
        manager._is_macos = False
        
        result = manager.check_accessibility_permission()
        
        assert result == PermissionStatus.NOT_APPLICABLE
    
    @patch('subprocess.run')
    def test_accessibility_fallback_granted(self, mock_run):
        """Test accessibility fallback returns GRANTED."""
        mock_run.return_value = MagicMock(returncode=0)
        
        manager = PermissionsManager()
        result = manager._check_accessibility_fallback()
        
        assert result == PermissionStatus.GRANTED
    
    @patch('subprocess.run')
    def test_accessibility_fallback_denied(self, mock_run):
        """Test accessibility fallback returns DENIED."""
        mock_run.return_value = MagicMock(returncode=1)
        
        manager = PermissionsManager()
        result = manager._check_accessibility_fallback()
        
        assert result == PermissionStatus.DENIED


class TestRequestPermission:
    """Tests for permission request methods."""
    
    @patch('pyaudio.PyAudio')
    def test_request_microphone_success(self, mock_pyaudio_class):
        """Test microphone permission request returns True."""
        mock_audio = MagicMock()
        mock_pyaudio_class.return_value = mock_audio
        mock_stream = MagicMock()
        mock_audio.open.return_value = mock_stream
        
        manager = PermissionsManager()
        result = manager.request_microphone_permission()
        
        assert result is True
    
    @patch('pyaudio.PyAudio')
    def test_request_microphone_failure(self, mock_pyaudio_class):
        """Test microphone permission request on failure."""
        mock_pyaudio_class.side_effect = Exception("Error")
        
        manager = PermissionsManager()
        result = manager.request_microphone_permission()
        
        assert result is False


class TestOpenSettings:
    """Tests for opening system settings."""
    
    def test_open_accessibility_non_macos(self):
        """Test opening accessibility settings on non-macOS."""
        manager = PermissionsManager()
        manager._is_macos = False
        
        result = manager.open_accessibility_settings()
        
        assert result is False
    
    def test_open_microphone_non_macos(self):
        """Test opening microphone settings on non-macOS."""
        manager = PermissionsManager()
        manager._is_macos = False
        
        result = manager.open_microphone_settings()
        
        assert result is False
    
    @patch('subprocess.run')
    def test_open_accessibility_success(self, mock_run):
        """Test opening accessibility settings success."""
        mock_run.return_value = MagicMock()
        
        manager = PermissionsManager()
        if manager.is_macos:
            result = manager.open_accessibility_settings()
            # Just verify it was called
            mock_run.assert_called()
    
    @patch('subprocess.run')
    def test_open_microphone_success(self, mock_run):
        """Test opening microphone settings success."""
        mock_run.return_value = MagicMock()
        
        manager = PermissionsManager()
        if manager.is_macos:
            result = manager.open_microphone_settings()
            mock_run.assert_called()


class TestCheckAllPermissions:
    """Tests for checking all permissions."""
    
    def test_check_all_returns_dict(self):
        """Test check_all_permissions returns dict."""
        manager = PermissionsManager()
        result = manager.check_all_permissions()
        
        assert isinstance(result, dict)
        assert "microphone" in result
        assert "accessibility" in result
    
    def test_check_all_values_are_status(self):
        """Test all values are PermissionStatus."""
        manager = PermissionsManager()
        result = manager.check_all_permissions()
        
        for value in result.values():
            assert isinstance(value, PermissionStatus)


class TestPermissionInstructions:
    """Tests for permission instructions."""
    
    def test_get_instructions_returns_string(self):
        """Test get_permission_instructions returns string."""
        manager = PermissionsManager()
        result = manager.get_permission_instructions()
        
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_instructions_contain_header(self):
        """Test instructions contain header."""
        manager = PermissionsManager()
        result = manager.get_permission_instructions()
        
        assert "WhOSSper Permissions Status" in result
    
    def test_instructions_contain_permission_names(self):
        """Test instructions mention permission names."""
        manager = PermissionsManager()
        result = manager.get_permission_instructions()
        
        assert "Microphone" in result or "microphone" in result
        assert "Accessibility" in result or "accessibility" in result


class TestAllPermissionsGranted:
    """Tests for all_permissions_granted method."""
    
    @patch.object(PermissionsManager, 'check_all_permissions')
    def test_all_granted_returns_true(self, mock_check):
        """Test returns True when all granted."""
        mock_check.return_value = {
            "microphone": PermissionStatus.GRANTED,
            "accessibility": PermissionStatus.GRANTED,
        }
        
        manager = PermissionsManager()
        result = manager.all_permissions_granted()
        
        assert result is True
    
    @patch.object(PermissionsManager, 'check_all_permissions')
    def test_not_applicable_counts_as_granted(self, mock_check):
        """Test NOT_APPLICABLE counts as granted."""
        mock_check.return_value = {
            "microphone": PermissionStatus.NOT_APPLICABLE,
            "accessibility": PermissionStatus.NOT_APPLICABLE,
        }
        
        manager = PermissionsManager()
        result = manager.all_permissions_granted()
        
        assert result is True
    
    @patch.object(PermissionsManager, 'check_all_permissions')
    def test_denied_returns_false(self, mock_check):
        """Test returns False when any denied."""
        mock_check.return_value = {
            "microphone": PermissionStatus.GRANTED,
            "accessibility": PermissionStatus.DENIED,
        }
        
        manager = PermissionsManager()
        result = manager.all_permissions_granted()
        
        assert result is False
    
    @patch.object(PermissionsManager, 'check_all_permissions')
    def test_unknown_returns_false(self, mock_check):
        """Test returns False when any unknown."""
        mock_check.return_value = {
            "microphone": PermissionStatus.UNKNOWN,
            "accessibility": PermissionStatus.GRANTED,
        }
        
        manager = PermissionsManager()
        result = manager.all_permissions_granted()
        
        assert result is False


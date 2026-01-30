"""Tests for dictation controller module."""

import os
import pytest
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

from whossper.core.dictation_controller import DictationController, DictationState
from whossper.config.schema import WhossperConfig, WhisperModelSize


@pytest.fixture
def config(tmp_dir):
    """Create a test configuration."""
    return WhossperConfig(
        tmp_dir=str(tmp_dir),
    )


@pytest.fixture
def mock_components():
    """Mock all expensive components."""
    with patch('whossper.core.dictation_controller.AudioRecorder') as mock_recorder, \
         patch('whossper.core.dictation_controller.WhisperTranscriber') as mock_transcriber, \
         patch('whossper.core.dictation_controller.TextInserter') as mock_inserter, \
         patch('whossper.core.dictation_controller.KeyboardListener') as mock_listener, \
         patch('whossper.core.dictation_controller.PermissionsManager') as mock_perms:
        
        # Configure mocks
        mock_recorder_instance = MagicMock()
        mock_recorder.return_value = mock_recorder_instance
        
        mock_transcriber_instance = MagicMock()
        mock_transcriber.return_value = mock_transcriber_instance
        
        mock_inserter_instance = MagicMock()
        mock_inserter.return_value = mock_inserter_instance
        
        mock_listener_instance = MagicMock()
        mock_listener.return_value = mock_listener_instance
        mock_listener_instance.start.return_value = True
        
        mock_perms_instance = MagicMock()
        mock_perms.return_value = mock_perms_instance
        mock_perms_instance.all_permissions_granted.return_value = True
        mock_perms_instance.check_all_permissions.return_value = {}
        
        yield {
            'recorder': mock_recorder_instance,
            'transcriber': mock_transcriber_instance,
            'inserter': mock_inserter_instance,
            'listener': mock_listener_instance,
            'perms': mock_perms_instance,
        }


class TestDictationState:
    """Tests for DictationState enum."""
    
    def test_idle_state(self):
        """Test IDLE state value."""
        assert DictationState.IDLE.value == "idle"
    
    def test_recording_state(self):
        """Test RECORDING state value."""
        assert DictationState.RECORDING.value == "recording"
    
    def test_transcribing_state(self):
        """Test TRANSCRIBING state value."""
        assert DictationState.TRANSCRIBING.value == "transcribing"
    
    def test_enhancing_state(self):
        """Test ENHANCING state value."""
        assert DictationState.ENHANCING.value == "enhancing"
    
    def test_inserting_state(self):
        """Test INSERTING state value."""
        assert DictationState.INSERTING.value == "inserting"
    
    def test_error_state(self):
        """Test ERROR state value."""
        assert DictationState.ERROR.value == "error"


class TestDictationControllerInit:
    """Tests for DictationController initialization."""
    
    def test_initialization(self, config, mock_components):
        """Test controller initializes correctly."""
        controller = DictationController(config)
        
        assert controller.state == DictationState.IDLE
        assert controller.config == config
    
    def test_creates_tmp_directory(self, tmp_dir, mock_components):
        """Test controller creates tmp directory."""
        new_tmp = tmp_dir / "subdir"
        config = WhossperConfig(tmp_dir=str(new_tmp))
        
        controller = DictationController(config)
        
        assert new_tmp.exists()
    
    def test_callbacks_stored(self, config, mock_components):
        """Test callbacks are stored."""
        state_cb = MagicMock()
        trans_cb = MagicMock()
        error_cb = MagicMock()
        
        controller = DictationController(
            config,
            on_state_change=state_cb,
            on_transcription=trans_cb,
            on_error=error_cb,
        )
        
        assert controller.on_state_change is state_cb
        assert controller.on_transcription is trans_cb
        assert controller.on_error is error_cb


class TestDictationControllerRecording:
    """Tests for recording functionality."""
    
    def test_start_recording_success(self, config, mock_components):
        """Test starting recording successfully."""
        mock_components['recorder'].start_recording.return_value = True
        
        controller = DictationController(config)
        result = controller.start_recording()
        
        assert result is True
        assert controller.state == DictationState.RECORDING
    
    def test_start_recording_failure(self, config, mock_components):
        """Test starting recording when it fails."""
        mock_components['recorder'].start_recording.return_value = False
        
        controller = DictationController(config)
        result = controller.start_recording()
        
        assert result is False
    
    def test_start_recording_wrong_state(self, config, mock_components):
        """Test starting recording when not idle."""
        mock_components['recorder'].start_recording.return_value = True
        
        controller = DictationController(config)
        controller.start_recording()  # Now in RECORDING state
        
        result = controller.start_recording()  # Try again
        
        assert result is False
    
    def test_stop_recording_when_not_recording(self, config, mock_components):
        """Test stopping when not recording."""
        controller = DictationController(config)
        result = controller.stop_recording()
        
        assert result is False
    
    def test_cancel_recording(self, config, mock_components):
        """Test cancelling recording."""
        mock_components['recorder'].start_recording.return_value = True
        
        controller = DictationController(config)
        controller.start_recording()
        controller.cancel_recording()
        
        assert controller.state == DictationState.IDLE
        mock_components['recorder'].cancel_recording.assert_called_once()


class TestDictationControllerStateChange:
    """Tests for state change callbacks."""
    
    def test_state_change_callback_called(self, config, mock_components):
        """Test state change callback is called."""
        callback = MagicMock()
        mock_components['recorder'].start_recording.return_value = True
        
        controller = DictationController(config, on_state_change=callback)
        controller.start_recording()
        
        callback.assert_called_with(DictationState.RECORDING)
    
    def test_state_change_callback_error_handled(self, config, mock_components):
        """Test state change callback error is handled."""
        callback = MagicMock(side_effect=Exception("Callback error"))
        mock_components['recorder'].start_recording.return_value = True
        
        controller = DictationController(config, on_state_change=callback)
        
        # Should not raise
        controller.start_recording()


class TestDictationControllerShortcuts:
    """Tests for keyboard shortcut setup."""
    
    def test_setup_shortcuts(self, config, mock_components):
        """Test setting up shortcuts."""
        controller = DictationController(config)
        result = controller.setup_shortcuts()
        
        assert result is True
        assert mock_components['listener'].register_shortcut.call_count >= 1
    
    def test_setup_hold_shortcut(self, config, mock_components):
        """Test hold-to-dictate shortcut is registered."""
        controller = DictationController(config)
        controller.setup_shortcuts()
        
        # Check register_shortcut was called with hold_to_dictate
        calls = mock_components['listener'].register_shortcut.call_args_list
        shortcuts_registered = [call[0][0] for call in calls]
        
        assert config.shortcuts.hold_to_dictate in shortcuts_registered


class TestDictationControllerStart:
    """Tests for starting the service."""
    
    def test_start_success(self, config, mock_components):
        """Test starting the service successfully."""
        controller = DictationController(config)
        result = controller.start()
        
        assert result is True
        mock_components['listener'].start.assert_called_once()
    
    def test_start_listener_fails(self, config, mock_components):
        """Test starting when listener fails."""
        mock_components['listener'].start.return_value = False
        
        controller = DictationController(config)
        result = controller.start()
        
        assert result is False


class TestDictationControllerStop:
    """Tests for stopping the service."""
    
    def test_stop_cleans_up(self, config, mock_components):
        """Test stopping cleans up resources."""
        controller = DictationController(config)
        controller.start()
        controller.stop()
        
        mock_components['listener'].stop.assert_called()
    
    def test_stop_cancels_recording(self, config, mock_components):
        """Test stopping cancels ongoing recording."""
        mock_components['recorder'].start_recording.return_value = True
        
        controller = DictationController(config)
        controller.start()
        controller.start_recording()
        controller.stop()
        
        mock_components['recorder'].cancel_recording.assert_called()


class TestDictationControllerContextManager:
    """Tests for context manager usage."""
    
    def test_context_manager_starts(self, config, mock_components):
        """Test context manager starts service."""
        with DictationController(config) as controller:
            mock_components['listener'].start.assert_called()
    
    def test_context_manager_stops(self, config, mock_components):
        """Test context manager stops service."""
        with DictationController(config) as controller:
            pass
        
        mock_components['listener'].stop.assert_called()


class TestDictationControllerPermissions:
    """Tests for permission checking."""
    
    def test_check_permissions(self, config, mock_components):
        """Test checking permissions."""
        from whossper.permissions.mac_permissions import PermissionStatus
        
        mock_components['perms'].check_all_permissions.return_value = {
            'microphone': PermissionStatus.GRANTED,
            'accessibility': PermissionStatus.GRANTED,
        }
        
        controller = DictationController(config)
        result = controller.check_permissions()
        
        assert 'microphone' in result
        assert 'accessibility' in result


class TestDictationControllerProcessing:
    """Tests for audio processing."""
    
    def test_process_audio_transcribes(self, config, mock_components, tmp_dir):
        """Test audio processing transcribes audio."""
        mock_components['transcriber'].transcribe_to_text.return_value = "Hello world"
        mock_components['inserter'].insert_text_with_fallback.return_value = True
        
        # Create a dummy audio file
        audio_file = tmp_dir / "test.wav"
        audio_file.write_bytes(b"fake audio data")
        
        controller = DictationController(config)
        controller._process_audio(str(audio_file))
        
        mock_components['transcriber'].transcribe_to_text.assert_called_once()
        mock_components['inserter'].insert_text_with_fallback.assert_called_once_with("Hello world")
    
    def test_process_audio_with_enhancement(self, tmp_dir, mock_components):
        """Test audio processing with enhancement enabled."""
        # Create config with enhancement
        config = WhossperConfig(
            tmp_dir=str(tmp_dir),
        )
        config.enhancement.enabled = True
        config.enhancement.api_key = "test-key"
        
        mock_components['transcriber'].transcribe_to_text.return_value = "um hello"
        
        with patch('whossper.core.dictation_controller.create_enhancer_from_config') as mock_create:
            mock_enhancer = MagicMock()
            mock_enhancer.enhance.return_value = "Hello!"
            mock_create.return_value = mock_enhancer
            
            audio_file = tmp_dir / "test.wav"
            audio_file.write_bytes(b"fake audio data")
            
            controller = DictationController(config)
            controller._process_audio(str(audio_file))
            
            mock_enhancer.enhance.assert_called_once()
            mock_components['inserter'].insert_text_with_fallback.assert_called_once_with("Hello!")
    
    def test_process_audio_cleans_up_file(self, config, mock_components, tmp_dir):
        """Test audio processing cleans up audio file."""
        mock_components['transcriber'].transcribe_to_text.return_value = "Hello"
        
        audio_file = tmp_dir / "test.wav"
        audio_file.write_bytes(b"fake audio data")
        
        controller = DictationController(config)
        controller._process_audio(str(audio_file))
        
        assert not audio_file.exists()


class TestDictationControllerToggle:
    """Tests for toggle dictation mode."""
    
    def test_toggle_starts_when_idle(self, config, mock_components):
        """Test toggle starts recording when idle."""
        mock_components['recorder'].start_recording.return_value = True
        
        controller = DictationController(config)
        controller._toggle_dictation()
        
        assert controller.state == DictationState.RECORDING
    
    def test_toggle_stops_when_recording(self, config, mock_components):
        """Test toggle stops recording when recording."""
        mock_components['recorder'].start_recording.return_value = True
        mock_components['recorder'].stop_recording.return_value = None
        
        controller = DictationController(config)
        controller.start_recording()
        controller._toggle_dictation()
        
        mock_components['recorder'].stop_recording.assert_called()

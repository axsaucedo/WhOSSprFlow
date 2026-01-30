"""Tests for whossper.core_new module."""

import numpy as np
import pytest
import threading
import time
from unittest.mock import MagicMock, patch, PropertyMock

from whossper.core_new import (
    DictationState,
    AudioRecorder,
    Transcriber,
    TextInserter,
    KeyboardShortcuts,
    ShortcutMode,
    PermissionStatus,
    check_microphone_permission,
    check_accessibility_permission,
    check_permissions,
    DictationController,
)
from whossper.config_new import Config, ModelSize, DeviceType


# =============================================================================
# DictationState Tests
# =============================================================================

class TestDictationState:
    """Tests for DictationState enum."""
    
    def test_state_values(self):
        """Test state enum values."""
        assert DictationState.IDLE.value == "idle"
        assert DictationState.RECORDING.value == "recording"
        assert DictationState.TRANSCRIBING.value == "transcribing"
        assert DictationState.ENHANCING.value == "enhancing"
        assert DictationState.INSERTING.value == "inserting"
        assert DictationState.ERROR.value == "error"
    
    def test_all_states(self):
        """Verify all expected states exist."""
        states = [s.value for s in DictationState]
        assert "idle" in states
        assert "recording" in states
        assert "transcribing" in states


# =============================================================================
# AudioRecorder Tests
# =============================================================================

class TestAudioRecorder:
    """Tests for AudioRecorder."""
    
    def test_init(self):
        """Test recorder initialization."""
        recorder = AudioRecorder()
        assert recorder.sample_rate == 16000
        assert recorder.channels == 1
        assert not recorder.is_recording
    
    def test_custom_params(self):
        """Test recorder with custom parameters."""
        recorder = AudioRecorder(sample_rate=44100, channels=2)
        assert recorder.sample_rate == 44100
        assert recorder.channels == 2
    
    @patch("whossper.core_new.sd.InputStream")
    def test_start_recording(self, mock_stream_class):
        """Test starting recording."""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream
        
        recorder = AudioRecorder()
        assert recorder.start() is True
        assert recorder.is_recording is True
        mock_stream.start.assert_called_once()
    
    @patch("whossper.core_new.sd.InputStream")
    def test_start_twice(self, mock_stream_class):
        """Test starting when already recording."""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream
        
        recorder = AudioRecorder()
        recorder.start()
        
        # Second start should return False
        assert recorder.start() is False
    
    @patch("whossper.core_new.sd.InputStream")
    def test_stop_recording(self, mock_stream_class):
        """Test stopping recording returns audio."""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream
        
        recorder = AudioRecorder()
        recorder.start()
        
        # Simulate recording some audio
        recorder._frames = [np.zeros((100,), dtype=np.float32)]
        
        audio = recorder.stop()
        assert audio is not None
        assert isinstance(audio, np.ndarray)
        assert len(audio) == 100
        assert not recorder.is_recording
        mock_stream.stop.assert_called()
        mock_stream.close.assert_called()
    
    def test_stop_without_start(self):
        """Test stopping without recording."""
        recorder = AudioRecorder()
        assert recorder.stop() is None
    
    @patch("whossper.core_new.sd.InputStream")
    def test_cancel_recording(self, mock_stream_class):
        """Test cancelling recording."""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream
        
        recorder = AudioRecorder()
        recorder.start()
        recorder._frames = [np.zeros((100,), dtype=np.float32)]
        
        recorder.cancel()
        assert not recorder.is_recording
        assert recorder._frames == []
    
    @patch("whossper.core_new.sd.InputStream")
    def test_duration_property(self, mock_stream_class):
        """Test duration calculation."""
        recorder = AudioRecorder(sample_rate=16000)
        recorder._frames = [np.zeros((16000,), dtype=np.float32)]
        
        assert recorder.duration == 1.0  # 16000 samples / 16000 Hz = 1s
    
    def test_duration_empty(self):
        """Test duration when no frames."""
        recorder = AudioRecorder()
        assert recorder.duration == 0.0


# =============================================================================
# Transcriber Tests
# =============================================================================

class TestTranscriber:
    """Tests for Transcriber."""
    
    def test_init(self):
        """Test transcriber initialization."""
        transcriber = Transcriber()
        assert transcriber.model_size == ModelSize.BASE
        assert transcriber.language == "en"
        assert transcriber.device_type == DeviceType.AUTO
    
    def test_custom_params(self):
        """Test transcriber with custom parameters."""
        transcriber = Transcriber(
            model_size=ModelSize.SMALL,
            language="es",
            device=DeviceType.CPU,
        )
        assert transcriber.model_size == ModelSize.SMALL
        assert transcriber.language == "es"
        assert transcriber.device_type == DeviceType.CPU
    
    def test_model_names(self):
        """Test model name mapping."""
        assert Transcriber.MODEL_NAMES[ModelSize.TINY] == "tiny"
        assert Transcriber.MODEL_NAMES[ModelSize.BASE] == "base"
        assert Transcriber.MODEL_NAMES[ModelSize.LARGE_V3] == "large-v3"
    
    @patch("whossper.core_new.torch.cuda.is_available", return_value=False)
    @patch("whossper.core_new.torch.backends.mps.is_available", return_value=False)
    def test_get_device_cpu(self, mock_mps, mock_cuda):
        """Test device detection returns CPU."""
        transcriber = Transcriber()
        assert transcriber._get_device() == "cpu"
    
    @patch("whossper.core_new.torch.cuda.is_available", return_value=True)
    def test_get_device_cuda(self, mock_cuda):
        """Test device detection returns CUDA."""
        transcriber = Transcriber()
        assert transcriber._get_device() == "cuda"
    
    @patch("whossper.core_new.torch.cuda.is_available", return_value=False)
    @patch("whossper.core_new.torch.backends.mps.is_available", return_value=True)
    def test_get_device_mps(self, mock_mps, mock_cuda):
        """Test device detection returns MPS."""
        transcriber = Transcriber()
        assert transcriber._get_device() == "mps"
    
    def test_forced_device(self):
        """Test explicit device setting."""
        transcriber = Transcriber(device=DeviceType.CPU)
        assert transcriber._get_device() == "cpu"
    
    @patch("whossper.core_new.whisper.load_model")
    @patch("whossper.core_new.torch.cuda.is_available", return_value=False)
    @patch("whossper.core_new.torch.backends.mps.is_available", return_value=False)
    def test_transcribe(self, mock_mps, mock_cuda, mock_load_model):
        """Test transcription."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "Hello world"}
        mock_load_model.return_value = mock_model
        
        transcriber = Transcriber()
        audio = np.zeros((16000,), dtype=np.float32)
        result = transcriber.transcribe(audio)
        
        assert result == "Hello world"
        mock_model.transcribe.assert_called_once()
    
    @patch("whossper.core_new.whisper.load_model")
    @patch("whossper.core_new.torch.cuda.is_available", return_value=False)
    @patch("whossper.core_new.torch.backends.mps.is_available", return_value=False)
    def test_unload(self, mock_mps, mock_cuda, mock_load_model):
        """Test model unload."""
        mock_model = MagicMock()
        mock_load_model.return_value = mock_model
        
        transcriber = Transcriber()
        _ = transcriber.model  # Load model
        transcriber.unload()
        
        assert transcriber._model is None


# =============================================================================
# TextInserter Tests
# =============================================================================

class TestTextInserter:
    """Tests for TextInserter."""
    
    def test_init(self):
        """Test inserter initialization."""
        inserter = TextInserter()
        assert inserter.paste_delay == 0.1
    
    def test_custom_delay(self):
        """Test custom paste delay."""
        inserter = TextInserter(paste_delay=0.5)
        assert inserter.paste_delay == 0.5
    
    def test_insert_empty(self):
        """Test inserting empty text."""
        inserter = TextInserter()
        assert inserter.insert("") is False
    
    @patch("whossper.core_new.pyperclip.copy")
    def test_insert_text(self, mock_copy):
        """Test text insertion copies to clipboard."""
        inserter = TextInserter(paste_delay=0.01)
        
        # Mock keyboard
        inserter.keyboard = MagicMock()
        inserter.keyboard.pressed = MagicMock()
        
        result = inserter.insert("Hello")
        
        mock_copy.assert_called_with("Hello")
    
    def test_type_empty(self):
        """Test typing empty text."""
        inserter = TextInserter()
        assert inserter.type_text("") is False


# =============================================================================
# KeyboardShortcuts Tests
# =============================================================================

class TestKeyboardShortcuts:
    """Tests for KeyboardShortcuts."""
    
    def test_init(self):
        """Test shortcuts initialization."""
        shortcuts = KeyboardShortcuts()
        assert not shortcuts.is_running
        assert shortcuts._shortcuts == {}
    
    def test_parse_shortcut_simple(self):
        """Test parsing simple shortcuts."""
        from pynput.keyboard import Key, KeyCode
        
        keys = KeyboardShortcuts.parse_shortcut("ctrl+c")
        assert Key.ctrl in keys
        assert KeyCode.from_char("c") in keys
    
    def test_parse_shortcut_complex(self):
        """Test parsing complex shortcuts."""
        from pynput.keyboard import Key, KeyCode
        
        keys = KeyboardShortcuts.parse_shortcut("ctrl+cmd+1")
        assert Key.ctrl in keys
        assert Key.cmd in keys
        assert KeyCode.from_char("1") in keys
    
    def test_parse_shortcut_spaces(self):
        """Test parsing shortcuts with spaces."""
        from pynput.keyboard import Key
        
        keys = KeyboardShortcuts.parse_shortcut("ctrl + cmd + shift")
        assert Key.ctrl in keys
        assert Key.cmd in keys
        assert Key.shift in keys
    
    def test_register_shortcut(self):
        """Test registering a shortcut."""
        shortcuts = KeyboardShortcuts()
        callback = MagicMock()
        
        shortcuts.register("ctrl+a", callback)
        
        assert len(shortcuts._shortcuts) == 1
    
    def test_register_toggle_shortcut(self):
        """Test registering toggle shortcut."""
        shortcuts = KeyboardShortcuts()
        callback = MagicMock()
        
        shortcuts.register("ctrl+b", callback, mode=ShortcutMode.TOGGLE)
        
        keys = list(shortcuts._shortcuts.keys())[0]
        assert shortcuts._shortcuts[keys]["mode"] == ShortcutMode.TOGGLE
    
    def test_register_hold_shortcut(self):
        """Test registering hold shortcut."""
        shortcuts = KeyboardShortcuts()
        on_press = MagicMock()
        on_release = MagicMock()
        
        shortcuts.register(
            "ctrl+c",
            on_press,
            mode=ShortcutMode.HOLD,
            on_release=on_release,
        )
        
        keys = list(shortcuts._shortcuts.keys())[0]
        assert shortcuts._shortcuts[keys]["mode"] == ShortcutMode.HOLD
        assert shortcuts._shortcuts[keys]["on_release"] == on_release
    
    @patch("whossper.core_new.keyboard.Listener")
    def test_start_stop(self, mock_listener_class):
        """Test starting and stopping listener."""
        mock_listener = MagicMock()
        mock_listener_class.return_value = mock_listener
        
        shortcuts = KeyboardShortcuts()
        
        assert shortcuts.start() is True
        assert shortcuts.is_running is True
        mock_listener.start.assert_called_once()
        
        shortcuts.stop()
        assert shortcuts.is_running is False


# =============================================================================
# Permission Tests
# =============================================================================

class TestPermissions:
    """Tests for permission checking."""
    
    def test_permission_status_values(self):
        """Test PermissionStatus enum values."""
        assert PermissionStatus.GRANTED.value == "granted"
        assert PermissionStatus.DENIED.value == "denied"
        assert PermissionStatus.UNKNOWN.value == "unknown"
    
    @patch("whossper.core_new.sd.InputStream")
    def test_check_microphone_granted(self, mock_stream):
        """Test microphone check when granted."""
        mock_stream.return_value.__enter__ = MagicMock()
        mock_stream.return_value.__exit__ = MagicMock()
        
        result = check_microphone_permission()
        assert result == PermissionStatus.GRANTED
    
    @patch("whossper.core_new.sd.InputStream")
    def test_check_microphone_denied(self, mock_stream):
        """Test microphone check when denied."""
        mock_stream.side_effect = Exception("Permission denied")
        
        result = check_microphone_permission()
        assert result == PermissionStatus.DENIED
    
    @patch("whossper.core_new.subprocess.run")
    def test_check_accessibility_granted(self, mock_run):
        """Test accessibility check when granted."""
        mock_run.return_value.returncode = 0
        
        result = check_accessibility_permission()
        assert result == PermissionStatus.GRANTED
    
    @patch("whossper.core_new.subprocess.run")
    def test_check_accessibility_denied(self, mock_run):
        """Test accessibility check when denied."""
        mock_run.return_value.returncode = 1
        
        result = check_accessibility_permission()
        assert result == PermissionStatus.DENIED
    
    @patch("whossper.core_new.check_microphone_permission")
    @patch("whossper.core_new.check_accessibility_permission")
    def test_check_all_permissions(self, mock_acc, mock_mic):
        """Test checking all permissions."""
        mock_mic.return_value = PermissionStatus.GRANTED
        mock_acc.return_value = PermissionStatus.GRANTED
        
        result = check_permissions()
        assert "microphone" in result
        assert "accessibility" in result


# =============================================================================
# DictationController Tests
# =============================================================================

class TestDictationController:
    """Tests for DictationController."""
    
    @pytest.fixture
    def config(self, tmp_path):
        """Create test config."""
        config = Config()
        config.tmp_dir = str(tmp_path / "tmp")
        return config
    
    def test_init(self, config):
        """Test controller initialization."""
        controller = DictationController(config)
        assert controller.state == DictationState.IDLE
        assert controller.config == config
    
    def test_init_with_callbacks(self, config):
        """Test initialization with callbacks."""
        on_state = MagicMock()
        on_text = MagicMock()
        on_error = MagicMock()
        
        controller = DictationController(
            config,
            on_state=on_state,
            on_text=on_text,
            on_error=on_error,
        )
        
        assert controller.on_state == on_state
        assert controller.on_text == on_text
        assert controller.on_error == on_error
    
    def test_state_callback(self, config):
        """Test state change callback."""
        states = []
        controller = DictationController(
            config,
            on_state=lambda s: states.append(s),
        )
        
        controller._set_state(DictationState.RECORDING)
        controller._set_state(DictationState.TRANSCRIBING)
        
        assert DictationState.RECORDING in states
        assert DictationState.TRANSCRIBING in states
    
    @patch.object(AudioRecorder, "start", return_value=True)
    def test_start_recording(self, mock_start, config):
        """Test starting recording."""
        controller = DictationController(config)
        
        assert controller.start_recording() is True
        assert controller.state == DictationState.RECORDING
    
    @patch.object(AudioRecorder, "start", return_value=False)
    def test_start_recording_failure(self, mock_start, config):
        """Test recording start failure."""
        controller = DictationController(config)
        
        assert controller.start_recording() is False
    
    def test_start_recording_wrong_state(self, config):
        """Test starting recording in wrong state."""
        controller = DictationController(config)
        controller._state = DictationState.TRANSCRIBING
        
        assert controller.start_recording() is False
    
    @patch.object(AudioRecorder, "start", return_value=True)
    @patch.object(AudioRecorder, "stop", return_value=np.zeros((32000,)))
    @patch.object(Transcriber, "transcribe", return_value="Test text")
    @patch("whossper.core_new.whisper.load_model")
    @patch("whossper.core_new.torch.cuda.is_available", return_value=False)
    @patch("whossper.core_new.torch.backends.mps.is_available", return_value=False)
    def test_stop_recording(self, mock_mps, mock_cuda, mock_load, mock_transcribe, mock_stop, mock_start, config):
        """Test stopping recording."""
        texts = []
        controller = DictationController(
            config,
            on_text=lambda t: texts.append(t),
        )
        
        controller.start_recording()
        assert controller.stop_recording() is True
        
        # Wait for processing
        controller.wait_for_processing(timeout=5.0)
        
        assert controller.state == DictationState.IDLE
    
    @patch.object(AudioRecorder, "start", return_value=True)
    @patch.object(AudioRecorder, "cancel")
    def test_cancel_recording(self, mock_cancel, mock_start, config):
        """Test cancelling recording."""
        controller = DictationController(config)
        
        controller.start_recording()
        controller.cancel_recording()
        
        mock_cancel.assert_called_once()
        assert controller.state == DictationState.IDLE
    
    def test_context_manager(self, config):
        """Test context manager protocol."""
        controller = DictationController(config)
        
        # Mock start and stop
        controller.start = MagicMock(return_value=True)
        controller.stop = MagicMock()
        
        with controller:
            controller.start.assert_called_once()
        
        controller.stop.assert_called_once()
    
    @patch("whossper.core_new.keyboard.Listener")
    def test_setup_shortcuts_hold(self, mock_listener_class, config):
        """Test hold-to-dictate shortcut setup."""
        config.shortcuts.hold_to_dictate = "ctrl+cmd+1"
        controller = DictationController(config)
        
        controller.setup_shortcuts()
        
        shortcuts = controller._get_shortcuts()
        assert len(shortcuts._shortcuts) >= 1
    
    @patch("whossper.core_new.keyboard.Listener")
    def test_setup_shortcuts_toggle(self, mock_listener_class, config):
        """Test toggle shortcut setup."""
        config.shortcuts.toggle_dictation = "ctrl+cmd+2"
        controller = DictationController(config)
        
        controller.setup_shortcuts()
        
        shortcuts = controller._get_shortcuts()
        assert len(shortcuts._shortcuts) >= 1


# =============================================================================
# Integration Tests (mocked)
# =============================================================================

class TestIntegration:
    """Integration tests with mocks."""
    
    @pytest.fixture
    def config(self, tmp_path):
        """Create test config."""
        config = Config()
        config.tmp_dir = str(tmp_path / "tmp")
        config.shortcuts.hold_to_dictate = "ctrl+cmd+1"
        return config
    
    @patch.object(AudioRecorder, "start", return_value=True)
    @patch.object(AudioRecorder, "stop", return_value=np.zeros((32000,), dtype=np.float32))
    @patch.object(Transcriber, "transcribe", return_value="Hello world")
    @patch.object(TextInserter, "insert", return_value=True)
    @patch("whossper.core_new.whisper.load_model")
    @patch("whossper.core_new.torch.cuda.is_available", return_value=False)
    @patch("whossper.core_new.torch.backends.mps.is_available", return_value=False)
    def test_full_dictation_flow(
        self, mock_mps, mock_cuda, mock_load, mock_insert, mock_transcribe, mock_stop, mock_start, config
    ):
        """Test full dictation flow."""
        states = []
        texts = []
        
        controller = DictationController(
            config,
            on_state=lambda s: states.append(s),
            on_text=lambda t: texts.append(t),
        )
        
        # Start recording
        assert controller.start_recording() is True
        assert DictationState.RECORDING in states
        
        # Stop recording (starts processing)
        assert controller.stop_recording() is True
        
        # Wait for processing
        controller.wait_for_processing(timeout=5.0)
        
        # Should have gone through states
        assert DictationState.TRANSCRIBING in states
        assert DictationState.INSERTING in states
        assert controller.state == DictationState.IDLE
        
        # Text should have been processed
        mock_transcribe.assert_called_once()
        mock_insert.assert_called_once_with("Hello world")
    
    @patch.object(AudioRecorder, "start", return_value=True)
    @patch.object(AudioRecorder, "stop", return_value=np.zeros((32000,), dtype=np.float32))
    @patch.object(Transcriber, "transcribe", return_value="Hello world")
    @patch.object(TextInserter, "insert", return_value=True)
    @patch("whossper.core_new.whisper.load_model")
    @patch("whossper.core_new.torch.cuda.is_available", return_value=False)
    @patch("whossper.core_new.torch.backends.mps.is_available", return_value=False)
    def test_flow_with_enhancer(
        self, mock_mps, mock_cuda, mock_load, mock_insert, mock_transcribe, mock_stop, mock_start, config
    ):
        """Test dictation flow with enhancer."""
        enhancer = MagicMock(return_value="ENHANCED Hello world")
        
        controller = DictationController(config, enhancer=enhancer)
        
        controller.start_recording()
        controller.stop_recording()
        controller.wait_for_processing(timeout=5.0)
        
        # Enhancer should have been called
        enhancer.assert_called_once_with("Hello world")
        
        # Enhanced text should be inserted
        mock_insert.assert_called_once_with("ENHANCED Hello world")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

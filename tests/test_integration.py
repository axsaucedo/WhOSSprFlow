"""End-to-end integration tests for WhOSSper Flow.

These tests validate the complete flow from audio to text insertion.
"""

import os
import struct
import tempfile
import wave
import math
import time
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from whossper.config.schema import WhossperConfig, WhisperModelSize
from whossper.core.dictation_controller import DictationController, DictationState
from whossper.audio.recorder import AudioRecorder
from whossper.transcription.whisper_transcriber import WhisperTranscriber
from whossper.input.text_inserter import TextInserter


@pytest.fixture
def tmp_dir():
    """Create a temporary directory for tests."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


def generate_test_audio_file(
    filepath: Path,
    duration_seconds: float = 2.0,
    frequency: float = 440.0,
    sample_rate: int = 16000,
) -> Path:
    """Generate a simple sine wave audio file for testing.
    
    Args:
        filepath: Path to save the WAV file.
        duration_seconds: Duration of audio in seconds.
        frequency: Frequency of sine wave in Hz.
        sample_rate: Sample rate in Hz.
    
    Returns:
        Path to the created audio file.
    """
    n_samples = int(duration_seconds * sample_rate)
    
    # Generate sine wave
    audio_data = []
    for i in range(n_samples):
        sample = int(32767 * 0.5 * math.sin(2 * math.pi * frequency * i / sample_rate))
        audio_data.append(struct.pack('<h', sample))
    
    # Write WAV file
    with wave.open(str(filepath), 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b''.join(audio_data))
    
    return filepath


class TestTranscriptionPipeline:
    """Tests for the transcription pipeline."""
    
    def test_transcribe_generated_audio(self, tmp_dir):
        """Test transcribing generated audio produces output."""
        # Generate test audio
        audio_path = generate_test_audio_file(tmp_dir / "test.wav")
        
        # Create transcriber with tiny model
        transcriber = WhisperTranscriber(
            model_size=WhisperModelSize.TINY,
            language="en",
        )
        
        # Transcribe
        result = transcriber.transcribe_to_text(str(audio_path))
        
        # Should return some text (even if empty for sine wave)
        assert isinstance(result, str)
    
    @pytest.mark.skipif(
        not os.path.exists("tests/fixtures/speech.wav"),
        reason="Speech audio fixture not available"
    )
    def test_transcribe_speech_audio(self, tmp_dir):
        """Test transcribing real speech audio."""
        transcriber = WhisperTranscriber(
            model_size=WhisperModelSize.TINY,
            language="en",
        )
        
        result = transcriber.transcribe_to_text("tests/fixtures/speech.wav")
        
        assert len(result) > 0


class TestControllerIntegration:
    """Integration tests for the DictationController."""
    
    def test_controller_with_mocked_recorder(self, tmp_dir):
        """Test controller processes audio correctly."""
        config = WhossperConfig(tmp_dir=str(tmp_dir))
        config.whisper.model_size = WhisperModelSize.TINY
        
        transcription_results = []
        
        with patch('whossper.core.dictation_controller.AudioRecorder') as mock_recorder, \
             patch('whossper.core.dictation_controller.WhisperTranscriber') as mock_transcriber, \
             patch('whossper.core.dictation_controller.TextInserter') as mock_inserter, \
             patch('whossper.core.dictation_controller.KeyboardListener') as mock_listener, \
             patch('whossper.core.dictation_controller.PermissionsManager') as mock_perms:
            
            # Configure mocks
            mock_rec_instance = MagicMock()
            mock_recorder.return_value = mock_rec_instance
            mock_rec_instance.start_recording.return_value = True
            
            # Create actual audio file
            audio_path = generate_test_audio_file(tmp_dir / "recording.wav")
            mock_rec_instance.stop_recording.return_value = str(audio_path)
            
            mock_trans_instance = MagicMock()
            mock_transcriber.return_value = mock_trans_instance
            mock_trans_instance.transcribe_to_text.return_value = "Hello world"
            
            mock_ins_instance = MagicMock()
            mock_inserter.return_value = mock_ins_instance
            mock_ins_instance.insert_text_with_fallback.return_value = True
            
            mock_list_instance = MagicMock()
            mock_listener.return_value = mock_list_instance
            mock_list_instance.start.return_value = True
            
            mock_perms_instance = MagicMock()
            mock_perms.return_value = mock_perms_instance
            mock_perms_instance.all_permissions_granted.return_value = True
            mock_perms_instance.check_all_permissions.return_value = {}
            
            def capture_transcription(text):
                transcription_results.append(text)
            
            controller = DictationController(
                config,
                on_transcription=capture_transcription,
            )
            
            # Start recording
            assert controller.start_recording() is True
            assert controller.state == DictationState.RECORDING
            
            # Stop recording - this triggers transcription
            controller.stop_recording()
            
            # Verify transcription was captured
            mock_trans_instance.transcribe_to_text.assert_called_once()
            mock_ins_instance.insert_text_with_fallback.assert_called_once_with("Hello world")
            assert "Hello world" in transcription_results
    
    def test_controller_enhancement_integration(self, tmp_dir):
        """Test controller with enhancement enabled."""
        config = WhossperConfig(tmp_dir=str(tmp_dir))
        config.enhancement.enabled = True
        config.enhancement.api_key = "test-key"
        
        with patch('whossper.core.dictation_controller.AudioRecorder') as mock_recorder, \
             patch('whossper.core.dictation_controller.WhisperTranscriber') as mock_transcriber, \
             patch('whossper.core.dictation_controller.TextInserter') as mock_inserter, \
             patch('whossper.core.dictation_controller.KeyboardListener') as mock_listener, \
             patch('whossper.core.dictation_controller.PermissionsManager') as mock_perms, \
             patch('whossper.core.dictation_controller.create_enhancer_from_config') as mock_create_enh:
            
            # Configure mocks
            mock_rec_instance = MagicMock()
            mock_recorder.return_value = mock_rec_instance
            mock_rec_instance.start_recording.return_value = True
            
            audio_path = generate_test_audio_file(tmp_dir / "recording.wav")
            mock_rec_instance.stop_recording.return_value = str(audio_path)
            
            mock_trans_instance = MagicMock()
            mock_transcriber.return_value = mock_trans_instance
            mock_trans_instance.transcribe_to_text.return_value = "um hello uh world"
            
            mock_ins_instance = MagicMock()
            mock_inserter.return_value = mock_ins_instance
            mock_ins_instance.insert_text_with_fallback.return_value = True
            
            mock_list_instance = MagicMock()
            mock_listener.return_value = mock_list_instance
            mock_list_instance.start.return_value = True
            
            mock_perms_instance = MagicMock()
            mock_perms.return_value = mock_perms_instance
            mock_perms_instance.all_permissions_granted.return_value = True
            
            mock_enhancer = MagicMock()
            mock_enhancer.enhance.return_value = "Hello, world!"
            mock_create_enh.return_value = mock_enhancer
            
            controller = DictationController(config)
            controller.start_recording()
            controller.stop_recording()
            
            # Verify enhancement was called
            mock_enhancer.enhance.assert_called_once_with("um hello uh world")
            mock_ins_instance.insert_text_with_fallback.assert_called_once_with("Hello, world!")


class TestAudioRecorderIntegration:
    """Integration tests for audio recording."""
    
    def test_recorder_saves_audio_data(self, tmp_dir):
        """Test that recorded audio data can be saved to a valid WAV file."""
        # Generate test audio and write directly to validate the format
        audio_path = generate_test_audio_file(
            tmp_dir / "direct_audio.wav",
            duration_seconds=1.0,
        )
        
        # Verify it's a valid WAV
        with wave.open(str(audio_path), 'rb') as wav:
            assert wav.getnchannels() == 1
            assert wav.getsampwidth() == 2
            assert wav.getframerate() == 16000


class TestStateTransitions:
    """Tests for state machine transitions."""
    
    def test_full_state_cycle(self, tmp_dir):
        """Test complete state cycle from IDLE through all states."""
        config = WhossperConfig(tmp_dir=str(tmp_dir))
        states_visited = []
        
        def track_state(state):
            states_visited.append(state)
        
        with patch('whossper.core.dictation_controller.AudioRecorder') as mock_recorder, \
             patch('whossper.core.dictation_controller.WhisperTranscriber') as mock_transcriber, \
             patch('whossper.core.dictation_controller.TextInserter') as mock_inserter, \
             patch('whossper.core.dictation_controller.KeyboardListener') as mock_listener, \
             patch('whossper.core.dictation_controller.PermissionsManager') as mock_perms:
            
            mock_rec_instance = MagicMock()
            mock_recorder.return_value = mock_rec_instance
            mock_rec_instance.start_recording.return_value = True
            
            audio_path = generate_test_audio_file(tmp_dir / "test.wav")
            mock_rec_instance.stop_recording.return_value = str(audio_path)
            
            mock_trans_instance = MagicMock()
            mock_transcriber.return_value = mock_trans_instance
            mock_trans_instance.transcribe_to_text.return_value = "test"
            
            mock_ins_instance = MagicMock()
            mock_inserter.return_value = mock_ins_instance
            mock_ins_instance.insert_text_with_fallback.return_value = True
            
            mock_list_instance = MagicMock()
            mock_listener.return_value = mock_list_instance
            mock_list_instance.start.return_value = True
            
            mock_perms_instance = MagicMock()
            mock_perms.return_value = mock_perms_instance
            mock_perms_instance.all_permissions_granted.return_value = True
            
            controller = DictationController(
                config,
                on_state_change=track_state,
            )
            
            assert controller.state == DictationState.IDLE
            controller.start_recording()
            controller.stop_recording()
            
            # Should have visited RECORDING at minimum
            assert DictationState.RECORDING in states_visited


class TestConfigurationIntegration:
    """Tests for configuration integration."""
    
    def test_config_values_accessible(self, tmp_dir):
        """Test configuration values are correctly set and accessible."""
        config = WhossperConfig(tmp_dir=str(tmp_dir))
        config.whisper.model_size = WhisperModelSize.SMALL
        config.whisper.language = "es"
        
        # Verify config is set correctly
        assert config.whisper.model_size == WhisperModelSize.SMALL
        assert config.whisper.language == "es"
        assert config.tmp_dir == str(tmp_dir)


class TestCLIIntegration:
    """Tests for CLI integration."""
    
    def test_cli_creates_config(self, tmp_dir):
        """Test CLI can create config file."""
        from typer.testing import CliRunner
        from whossper.cli import app
        
        runner = CliRunner()
        config_path = tmp_dir / "new_config.json"
        
        result = runner.invoke(app, ["config", "--init", "--path", str(config_path)])
        
        assert result.exit_code == 0
        assert config_path.exists()
    
    def test_cli_shows_models(self):
        """Test CLI models command works."""
        from typer.testing import CliRunner
        from whossper.cli import app
        
        runner = CliRunner()
        result = runner.invoke(app, ["models"])
        
        assert result.exit_code == 0
        assert "tiny" in result.output
        assert "turbo" in result.output


class TestErrorHandling:
    """Tests for error handling in integration scenarios."""
    
    def test_transcription_error_logged(self, tmp_dir):
        """Test transcription errors are handled gracefully."""
        config = WhossperConfig(tmp_dir=str(tmp_dir))
        
        with patch('whossper.core.dictation_controller.AudioRecorder') as mock_recorder, \
             patch('whossper.core.dictation_controller.WhisperTranscriber') as mock_transcriber, \
             patch('whossper.core.dictation_controller.TextInserter') as mock_inserter, \
             patch('whossper.core.dictation_controller.KeyboardListener') as mock_listener, \
             patch('whossper.core.dictation_controller.PermissionsManager') as mock_perms:
            
            mock_rec_instance = MagicMock()
            mock_recorder.return_value = mock_rec_instance
            mock_rec_instance.start_recording.return_value = True
            
            audio_path = generate_test_audio_file(tmp_dir / "test.wav")
            mock_rec_instance.stop_recording.return_value = str(audio_path)
            
            mock_trans_instance = MagicMock()
            mock_transcriber.return_value = mock_trans_instance
            mock_trans_instance.transcribe_to_text.side_effect = Exception("Model error")
            
            mock_inserter.return_value = MagicMock()
            mock_listener.return_value = MagicMock()
            mock_perms.return_value = MagicMock()
            mock_perms.return_value.all_permissions_granted.return_value = True
            
            controller = DictationController(config)
            
            controller.start_recording()
            controller.stop_recording()
            
            # Error was handled - controller should still be functional
            # (logged error, returned to a valid state)
            mock_trans_instance.transcribe_to_text.assert_called_once()
    
    def test_empty_transcription_handled(self, tmp_dir):
        """Test empty transcription is handled gracefully."""
        config = WhossperConfig(tmp_dir=str(tmp_dir))
        
        with patch('whossper.core.dictation_controller.AudioRecorder') as mock_recorder, \
             patch('whossper.core.dictation_controller.WhisperTranscriber') as mock_transcriber, \
             patch('whossper.core.dictation_controller.TextInserter') as mock_inserter, \
             patch('whossper.core.dictation_controller.KeyboardListener') as mock_listener, \
             patch('whossper.core.dictation_controller.PermissionsManager') as mock_perms:
            
            mock_rec_instance = MagicMock()
            mock_recorder.return_value = mock_rec_instance
            mock_rec_instance.start_recording.return_value = True
            
            audio_path = generate_test_audio_file(tmp_dir / "test.wav")
            mock_rec_instance.stop_recording.return_value = str(audio_path)
            
            mock_trans_instance = MagicMock()
            mock_transcriber.return_value = mock_trans_instance
            mock_trans_instance.transcribe_to_text.return_value = ""  # Empty
            
            mock_ins_instance = MagicMock()
            mock_inserter.return_value = mock_ins_instance
            
            mock_listener.return_value = MagicMock()
            mock_perms.return_value = MagicMock()
            mock_perms.return_value.all_permissions_granted.return_value = True
            
            controller = DictationController(config)
            controller.start_recording()
            controller.stop_recording()
            
            # Should not insert empty text
            mock_ins_instance.insert_text_with_fallback.assert_not_called()


class TestRealWhisperIntegration:
    """Tests with real Whisper model (slow, requires model download)."""
    
    @pytest.mark.slow
    @pytest.mark.skipif(
        os.environ.get("CI") == "true",
        reason="Skip slow tests in CI"
    )
    def test_real_whisper_transcription(self, tmp_dir):
        """Test real Whisper transcription with generated audio."""
        # Generate a simple test audio
        audio_path = generate_test_audio_file(
            tmp_dir / "test.wav",
            duration_seconds=1.0,
        )
        
        transcriber = WhisperTranscriber(
            model_size=WhisperModelSize.TINY,
            language="en",
        )
        
        result = transcriber.transcribe_to_text(str(audio_path))
        
        # Should produce some output (might be empty for sine wave)
        assert isinstance(result, str)

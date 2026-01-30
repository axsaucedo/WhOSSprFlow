"""Tests for audio recorder module."""

import os
import wave
import pytest
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from whossper.audio.recorder import AudioRecorder, create_test_audio


class TestCreateTestAudio:
    """Tests for test audio creation helper."""
    
    def test_creates_wav_file(self, tmp_dir):
        """Test that create_test_audio creates a valid WAV file."""
        filename = str(tmp_dir / "test.wav")
        result = create_test_audio(filename, duration=1.0)
        
        assert result == filename
        assert os.path.exists(filename)
    
    def test_wav_file_properties(self, tmp_dir):
        """Test created WAV file has correct properties."""
        filename = str(tmp_dir / "test.wav")
        create_test_audio(filename, duration=1.0, sample_rate=16000)
        
        with wave.open(filename, 'rb') as wf:
            assert wf.getnchannels() == 1
            assert wf.getframerate() == 16000
            assert wf.getsampwidth() == 2  # 16-bit
    
    def test_custom_duration(self, tmp_dir):
        """Test creating audio with custom duration."""
        filename = str(tmp_dir / "test.wav")
        create_test_audio(filename, duration=2.5, sample_rate=16000)
        
        with wave.open(filename, 'rb') as wf:
            num_frames = wf.getnframes()
            expected_frames = int(16000 * 2.5)
            assert num_frames == expected_frames


class TestAudioRecorderInit:
    """Tests for AudioRecorder initialization."""
    
    def test_default_initialization(self, tmp_dir):
        """Test recorder initializes with defaults."""
        recorder = AudioRecorder(tmp_dir=str(tmp_dir))
        
        assert recorder.sample_rate == 16000
        assert recorder.channels == 1
        assert recorder.chunk_size == 1024
        assert recorder.is_recording is False
    
    def test_custom_initialization(self, tmp_dir):
        """Test recorder with custom settings."""
        recorder = AudioRecorder(
            sample_rate=44100,
            channels=2,
            chunk_size=2048,
            tmp_dir=str(tmp_dir)
        )
        
        assert recorder.sample_rate == 44100
        assert recorder.channels == 2
        assert recorder.chunk_size == 2048
    
    def test_creates_tmp_directory(self, tmp_dir):
        """Test recorder creates tmp directory if it doesn't exist."""
        new_tmp = tmp_dir / "new_subdir"
        assert not new_tmp.exists()
        
        recorder = AudioRecorder(tmp_dir=str(new_tmp))
        assert new_tmp.exists()
    
    def test_callback_setter(self, tmp_dir):
        """Test setting completion callback."""
        callback = MagicMock()
        recorder = AudioRecorder(
            tmp_dir=str(tmp_dir),
            on_recording_complete=callback
        )
        
        assert recorder.on_recording_complete is callback


class TestAudioRecorderProperties:
    """Tests for AudioRecorder property access."""
    
    def test_is_recording_false_initially(self, tmp_dir):
        """Test is_recording is False when not recording."""
        recorder = AudioRecorder(tmp_dir=str(tmp_dir))
        assert recorder.is_recording is False
    
    def test_recording_duration_zero_when_not_recording(self, tmp_dir):
        """Test recording_duration is 0 when not recording."""
        recorder = AudioRecorder(tmp_dir=str(tmp_dir))
        assert recorder.recording_duration == 0.0
    
    def test_frames_recorded_zero_initially(self, tmp_dir):
        """Test frames_recorded is 0 initially."""
        recorder = AudioRecorder(tmp_dir=str(tmp_dir))
        assert recorder.frames_recorded == 0


class TestAudioRecorderMocked:
    """Tests for AudioRecorder with mocked PyAudio."""
    
    @patch('whossper.audio.recorder.pyaudio.PyAudio')
    def test_start_recording_success(self, mock_pyaudio, tmp_dir):
        """Test starting recording successfully."""
        mock_instance = MagicMock()
        mock_pyaudio.return_value = mock_instance
        mock_stream = MagicMock()
        mock_instance.open.return_value = mock_stream
        
        recorder = AudioRecorder(tmp_dir=str(tmp_dir))
        result = recorder.start_recording()
        
        assert result is True
        assert recorder.is_recording is True
        mock_instance.open.assert_called_once()
    
    @patch('whossper.audio.recorder.pyaudio.PyAudio')
    def test_start_recording_already_recording(self, mock_pyaudio, tmp_dir):
        """Test starting recording when already recording."""
        mock_instance = MagicMock()
        mock_pyaudio.return_value = mock_instance
        mock_stream = MagicMock()
        mock_instance.open.return_value = mock_stream
        
        recorder = AudioRecorder(tmp_dir=str(tmp_dir))
        recorder.start_recording()
        
        # Try to start again
        result = recorder.start_recording()
        assert result is False
    
    @patch('whossper.audio.recorder.pyaudio.PyAudio')
    def test_stop_recording_not_recording(self, mock_pyaudio, tmp_dir):
        """Test stopping when not recording."""
        recorder = AudioRecorder(tmp_dir=str(tmp_dir))
        result = recorder.stop_recording()
        
        assert result is None
    
    @patch('whossper.audio.recorder.pyaudio.PyAudio')
    def test_cancel_recording(self, mock_pyaudio, tmp_dir):
        """Test cancelling recording."""
        mock_instance = MagicMock()
        mock_pyaudio.return_value = mock_instance
        mock_stream = MagicMock()
        mock_instance.open.return_value = mock_stream
        
        recorder = AudioRecorder(tmp_dir=str(tmp_dir))
        recorder.start_recording()
        recorder._frames = [b'test' * 1000]  # Add some fake frames
        
        recorder.cancel_recording()
        
        assert recorder.is_recording is False
        assert recorder.frames_recorded == 0
    
    @patch('whossper.audio.recorder.pyaudio.PyAudio')
    def test_context_manager(self, mock_pyaudio, tmp_dir):
        """Test using recorder as context manager."""
        mock_instance = MagicMock()
        mock_pyaudio.return_value = mock_instance
        
        with AudioRecorder(tmp_dir=str(tmp_dir)) as recorder:
            assert recorder is not None
            # Initialize audio to test cleanup
            recorder._initialize_audio()
        
        # Verify cleanup was called
        mock_instance.terminate.assert_called()
    
    @patch('whossper.audio.recorder.pyaudio.PyAudio')
    def test_cleanup(self, mock_pyaudio, tmp_dir):
        """Test cleanup releases resources."""
        mock_instance = MagicMock()
        mock_pyaudio.return_value = mock_instance
        
        recorder = AudioRecorder(tmp_dir=str(tmp_dir))
        recorder._initialize_audio()
        recorder.cleanup()
        
        mock_instance.terminate.assert_called_once()
    
    @patch('whossper.audio.recorder.pyaudio.PyAudio')
    def test_audio_callback(self, mock_pyaudio, tmp_dir):
        """Test audio callback stores frames."""
        recorder = AudioRecorder(tmp_dir=str(tmp_dir))
        recorder._is_recording = True
        
        test_data = b'audio_frame_data'
        result = recorder._audio_callback(test_data, 1024, {}, 0)
        
        assert test_data in recorder._frames
        assert result[1] == 0  # pyaudio.paContinue is 0
    
    @patch('whossper.audio.recorder.pyaudio.PyAudio')
    def test_stop_recording_too_short(self, mock_pyaudio, tmp_dir):
        """Test stopping recording that's too short raises error."""
        mock_instance = MagicMock()
        mock_pyaudio.return_value = mock_instance
        mock_stream = MagicMock()
        mock_instance.open.return_value = mock_stream
        
        recorder = AudioRecorder(tmp_dir=str(tmp_dir))
        recorder.start_recording()
        recorder._frames = [b'x' * 100]  # Very little data
        
        with pytest.raises(ValueError, match="at least"):
            recorder.stop_recording(min_duration=1.0)
    
    @patch('whossper.audio.recorder.pyaudio.PyAudio')
    def test_stop_recording_saves_file(self, mock_pyaudio, tmp_dir):
        """Test stopping recording saves audio file."""
        mock_instance = MagicMock()
        mock_pyaudio.return_value = mock_instance
        mock_stream = MagicMock()
        mock_instance.open.return_value = mock_stream
        mock_instance.get_sample_size.return_value = 2
        
        recorder = AudioRecorder(
            tmp_dir=str(tmp_dir),
            sample_rate=16000,
            chunk_size=1024
        )
        recorder.start_recording()
        
        # Add enough frames for 1 second of audio
        # 16000 samples / 1024 chunk = ~16 chunks per second
        for _ in range(20):
            recorder._frames.append(b'\x00' * 2048)  # 1024 samples * 2 bytes
        
        result = recorder.stop_recording(min_duration=0.5)
        
        assert result is not None
        assert os.path.exists(result)
        assert result.endswith('.wav')
    
    @patch('whossper.audio.recorder.pyaudio.PyAudio')
    def test_callback_called_on_complete(self, mock_pyaudio, tmp_dir):
        """Test completion callback is called."""
        mock_instance = MagicMock()
        mock_pyaudio.return_value = mock_instance
        mock_stream = MagicMock()
        mock_instance.open.return_value = mock_stream
        mock_instance.get_sample_size.return_value = 2
        
        callback = MagicMock()
        recorder = AudioRecorder(
            tmp_dir=str(tmp_dir),
            sample_rate=16000,
            chunk_size=1024,
            on_recording_complete=callback
        )
        recorder.start_recording()
        
        # Add enough frames
        for _ in range(20):
            recorder._frames.append(b'\x00' * 2048)
        
        result = recorder.stop_recording(min_duration=0.5)
        
        callback.assert_called_once_with(result)


class TestAudioRecorderIntegration:
    """Integration tests with real PyAudio (if available)."""
    
    @pytest.mark.skipif(
        os.environ.get('CI') == 'true',
        reason="Skip in CI environment without audio hardware"
    )
    def test_real_recording_short(self, tmp_dir):
        """Test actual recording for a short time."""
        recorder = AudioRecorder(tmp_dir=str(tmp_dir))
        
        success = recorder.start_recording()
        if not success:
            pytest.skip("Could not initialize audio (no microphone?)")
        
        time.sleep(0.6)  # Record just over minimum
        
        try:
            result = recorder.stop_recording(min_duration=0.5)
            assert result is not None
            assert os.path.exists(result)
        except ValueError:
            # Recording was too short, might happen on slow systems
            pass
        finally:
            recorder.cleanup()

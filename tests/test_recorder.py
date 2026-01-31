"""Tests for whosspr.recorder module."""

import numpy as np
import pytest
from unittest.mock import patch, MagicMock

from whosspr.recorder import AudioRecorder


class TestAudioRecorder:
    """Tests for AudioRecorder class."""
    
    def test_init_defaults(self):
        """Test default initialization."""
        rec = AudioRecorder()
        assert rec.sample_rate == 16000
        assert rec.channels == 1
        assert not rec.is_recording
        assert rec.duration == 0.0
    
    def test_init_custom(self):
        """Test custom initialization."""
        rec = AudioRecorder(sample_rate=44100, channels=2)
        assert rec.sample_rate == 44100
        assert rec.channels == 2
    
    @patch("whosspr.recorder.sd.InputStream")
    def test_start_success(self, mock_stream_class):
        """Test successful recording start."""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream
        
        rec = AudioRecorder()
        result = rec.start()
        
        assert result is True
        assert rec.is_recording is True
        mock_stream.start.assert_called_once()
    
    @patch("whosspr.recorder.sd.InputStream")
    def test_start_already_recording(self, mock_stream_class):
        """Test start when already recording."""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream
        
        rec = AudioRecorder()
        rec.start()
        result = rec.start()  # Second call
        
        assert result is False
    
    @patch("whosspr.recorder.sd.InputStream")
    def test_stop_returns_audio(self, mock_stream_class):
        """Test stop returns recorded audio."""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream
        
        rec = AudioRecorder()
        rec.start()
        
        # Simulate callback adding frames
        rec._frames = [np.zeros(1000, dtype=np.float32)]
        
        audio = rec.stop()
        
        assert audio is not None
        assert len(audio) == 1000
        assert not rec.is_recording
    
    @patch("whosspr.recorder.sd.InputStream")
    def test_stop_when_not_recording(self, mock_stream_class):
        """Test stop when not recording."""
        rec = AudioRecorder()
        audio = rec.stop()
        assert audio is None
    
    @patch("whosspr.recorder.sd.InputStream")
    def test_cancel_discards_data(self, mock_stream_class):
        """Test cancel discards recorded data."""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream
        
        rec = AudioRecorder()
        rec.start()
        rec._frames = [np.zeros(1000, dtype=np.float32)]
        
        rec.cancel()
        
        assert not rec.is_recording
        assert rec._frames == []
    
    @patch("whosspr.recorder.sd.InputStream")
    def test_duration_during_recording(self, mock_stream_class):
        """Test duration calculation during recording."""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream
        
        rec = AudioRecorder(sample_rate=16000)
        rec.start()
        rec._frames = [np.zeros(16000, dtype=np.float32)]  # 1 second
        
        assert rec.duration == pytest.approx(1.0)

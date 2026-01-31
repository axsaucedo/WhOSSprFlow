"""Tests for whosspr.transcriber module."""

import numpy as np
import pytest
from unittest.mock import patch, MagicMock

from whosspr.transcriber import Transcriber, get_device, MODEL_NAMES
from whosspr.config import ModelSize, DeviceType


class TestGetDevice:
    """Tests for get_device function."""
    
    @patch("whosspr.transcriber.torch.cuda.is_available", return_value=False)
    @patch("whosspr.transcriber.torch.backends.mps.is_available", return_value=False)
    def test_auto_cpu(self, mock_mps, mock_cuda):
        """Test AUTO falls back to CPU."""
        assert get_device(DeviceType.AUTO) == "cpu"
    
    @patch("whosspr.transcriber.torch.cuda.is_available", return_value=True)
    def test_auto_cuda(self, mock_cuda):
        """Test AUTO uses CUDA when available."""
        assert get_device(DeviceType.AUTO) == "cuda"
    
    @patch("whosspr.transcriber.torch.cuda.is_available", return_value=False)
    @patch("whosspr.transcriber.torch.backends.mps.is_available", return_value=True)
    def test_auto_mps(self, mock_mps, mock_cuda):
        """Test AUTO uses MPS when available."""
        assert get_device(DeviceType.AUTO) == "mps"
    
    def test_explicit_cpu(self):
        """Test explicit CPU device."""
        assert get_device(DeviceType.CPU) == "cpu"


class TestTranscriber:
    """Tests for Transcriber class."""
    
    def test_init_defaults(self):
        """Test default initialization."""
        t = Transcriber()
        assert t.model_size == ModelSize.BASE
        assert t.language == "en"
    
    @patch("whosspr.transcriber.whisper.load_model")
    @patch("whosspr.transcriber.torch.cuda.is_available", return_value=False)
    @patch("whosspr.transcriber.torch.backends.mps.is_available", return_value=False)
    def test_transcribe(self, mock_mps, mock_cuda, mock_load):
        """Test transcription."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": " Hello world "}
        mock_load.return_value = mock_model
        
        t = Transcriber()
        audio = np.random.rand(16000).astype(np.float32)
        result = t.transcribe(audio)
        
        assert result == "Hello world"
        mock_model.transcribe.assert_called_once()
    
    @patch("whosspr.transcriber.whisper.load_model")
    @patch("whosspr.transcriber.torch.cuda.is_available", return_value=False)
    @patch("whosspr.transcriber.torch.backends.mps.is_available", return_value=False)
    def test_model_loads_once(self, mock_mps, mock_cuda, mock_load):
        """Test model is loaded only once."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "test"}
        mock_load.return_value = mock_model
        
        t = Transcriber()
        _ = t.model
        _ = t.model
        
        mock_load.assert_called_once()
    
    @patch("whosspr.transcriber.whisper.load_model")
    @patch("whosspr.transcriber.torch.cuda.is_available", return_value=False)
    @patch("whosspr.transcriber.torch.backends.mps.is_available", return_value=False)
    def test_unload(self, mock_mps, mock_cuda, mock_load):
        """Test model unloading."""
        mock_model = MagicMock()
        mock_load.return_value = mock_model
        
        t = Transcriber()
        _ = t.model
        t.unload()
        
        assert t._model is None


class TestModelNames:
    """Test model name mapping."""
    
    def test_all_model_sizes_mapped(self):
        """Verify all ModelSize values have mappings."""
        for size in ModelSize:
            assert size in MODEL_NAMES or size.value in [MODEL_NAMES.get(s) for s in MODEL_NAMES]

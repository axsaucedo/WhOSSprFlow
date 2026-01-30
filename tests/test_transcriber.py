"""Tests for Whisper transcriber module."""

import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

from whossper.transcription.whisper_transcriber import (
    WhisperTranscriber,
    get_model_info,
)
from whossper.config.schema import WhisperModelSize, DeviceType
from whossper.audio.recorder import create_test_audio


class TestWhisperTranscriberInit:
    """Tests for WhisperTranscriber initialization."""
    
    def test_default_initialization(self):
        """Test transcriber initializes with defaults."""
        transcriber = WhisperTranscriber()
        
        assert transcriber.model_size == WhisperModelSize.BASE
        assert transcriber.language == "en"
        assert transcriber.device_type == DeviceType.AUTO
        assert transcriber.is_model_loaded is False
    
    def test_custom_model_size(self):
        """Test transcriber with custom model size."""
        transcriber = WhisperTranscriber(model_size=WhisperModelSize.SMALL)
        assert transcriber.model_size == WhisperModelSize.SMALL
    
    def test_string_model_size(self):
        """Test transcriber accepts string model size."""
        transcriber = WhisperTranscriber(model_size="small")
        assert transcriber.model_size == WhisperModelSize.SMALL
    
    def test_custom_language(self):
        """Test transcriber with custom language."""
        transcriber = WhisperTranscriber(language="es")
        assert transcriber.language == "es"
    
    def test_custom_device(self):
        """Test transcriber with custom device."""
        transcriber = WhisperTranscriber(device=DeviceType.CPU)
        assert transcriber.device_type == DeviceType.CPU
    
    def test_string_device(self):
        """Test transcriber accepts string device."""
        transcriber = WhisperTranscriber(device="cpu")
        assert transcriber.device_type == DeviceType.CPU
    
    def test_model_cache_dir(self):
        """Test transcriber with custom cache directory."""
        transcriber = WhisperTranscriber(model_cache_dir="/tmp/whisper_cache")
        assert transcriber.model_cache_dir == "/tmp/whisper_cache"


class TestWhisperTranscriberDevice:
    """Tests for device selection."""
    
    @patch('torch.cuda.is_available', return_value=True)
    def test_auto_selects_cuda(self, mock_cuda):
        """Test AUTO selects CUDA when available."""
        transcriber = WhisperTranscriber(device=DeviceType.AUTO)
        assert transcriber.device == "cuda"
    
    @patch('torch.cuda.is_available', return_value=False)
    @patch('torch.backends.mps.is_available', return_value=True)
    def test_auto_selects_mps(self, mock_mps, mock_cuda):
        """Test AUTO selects MPS when CUDA unavailable."""
        transcriber = WhisperTranscriber(device=DeviceType.AUTO)
        assert transcriber.device == "mps"
    
    @patch('torch.cuda.is_available', return_value=False)
    @patch('torch.backends.mps.is_available', return_value=False)
    def test_auto_selects_cpu(self, mock_mps, mock_cuda):
        """Test AUTO selects CPU as fallback."""
        transcriber = WhisperTranscriber(device=DeviceType.AUTO)
        assert transcriber.device == "cpu"
    
    def test_explicit_cpu(self):
        """Test explicit CPU selection."""
        transcriber = WhisperTranscriber(device=DeviceType.CPU)
        assert transcriber.device == "cpu"


class TestWhisperTranscriberMocked:
    """Tests for WhisperTranscriber with mocked whisper module."""
    
    @patch('whossper.transcription.whisper_transcriber.whisper')
    def test_load_model(self, mock_whisper, tmp_dir):
        """Test model loading."""
        mock_model = MagicMock()
        mock_whisper.load_model.return_value = mock_model
        
        transcriber = WhisperTranscriber(
            model_size=WhisperModelSize.BASE,
            device=DeviceType.CPU
        )
        
        model = transcriber.model
        
        mock_whisper.load_model.assert_called_once_with(
            "base",
            device="cpu",
            download_root=None
        )
        assert model is mock_model
    
    @patch('whossper.transcription.whisper_transcriber.whisper')
    def test_load_model_with_cache_dir(self, mock_whisper, tmp_dir):
        """Test model loading with cache directory."""
        mock_model = MagicMock()
        mock_whisper.load_model.return_value = mock_model
        
        cache_dir = str(tmp_dir / "cache")
        transcriber = WhisperTranscriber(
            model_size=WhisperModelSize.BASE,
            device=DeviceType.CPU,
            model_cache_dir=cache_dir
        )
        
        _ = transcriber.model
        
        mock_whisper.load_model.assert_called_once_with(
            "base",
            device="cpu",
            download_root=cache_dir
        )
    
    @patch('whossper.transcription.whisper_transcriber.whisper')
    def test_model_cached(self, mock_whisper):
        """Test model is cached after first load."""
        mock_model = MagicMock()
        mock_whisper.load_model.return_value = mock_model
        
        transcriber = WhisperTranscriber(device=DeviceType.CPU)
        
        # Access model twice
        _ = transcriber.model
        _ = transcriber.model
        
        # Should only load once
        assert mock_whisper.load_model.call_count == 1
    
    @patch('whossper.transcription.whisper_transcriber.whisper')
    def test_transcribe(self, mock_whisper, tmp_dir):
        """Test transcription."""
        mock_model = MagicMock()
        mock_whisper.load_model.return_value = mock_model
        mock_model.transcribe.return_value = {
            "text": "Hello world",
            "segments": []
        }
        
        # Create test audio file
        audio_file = str(tmp_dir / "test.wav")
        create_test_audio(audio_file, duration=1.0)
        
        transcriber = WhisperTranscriber(device=DeviceType.CPU)
        result = transcriber.transcribe(audio_file)
        
        assert result["text"] == "Hello world"
        mock_model.transcribe.assert_called_once()
    
    @patch('whossper.transcription.whisper_transcriber.whisper')
    def test_transcribe_to_text(self, mock_whisper, tmp_dir):
        """Test transcription to text only."""
        mock_model = MagicMock()
        mock_whisper.load_model.return_value = mock_model
        mock_model.transcribe.return_value = {
            "text": "  Hello world  ",
            "segments": []
        }
        
        audio_file = str(tmp_dir / "test.wav")
        create_test_audio(audio_file, duration=1.0)
        
        transcriber = WhisperTranscriber(device=DeviceType.CPU)
        text = transcriber.transcribe_to_text(audio_file)
        
        assert text == "Hello world"  # Should be stripped
    
    @patch('whossper.transcription.whisper_transcriber.whisper')
    def test_transcribe_file_not_found(self, mock_whisper):
        """Test transcription with nonexistent file."""
        transcriber = WhisperTranscriber(device=DeviceType.CPU)
        
        with pytest.raises(FileNotFoundError):
            transcriber.transcribe("/nonexistent/file.wav")
    
    @patch('whossper.transcription.whisper_transcriber.whisper')
    def test_transcribe_custom_language(self, mock_whisper, tmp_dir):
        """Test transcription with language override."""
        mock_model = MagicMock()
        mock_whisper.load_model.return_value = mock_model
        mock_model.transcribe.return_value = {"text": "Hola mundo"}
        
        audio_file = str(tmp_dir / "test.wav")
        create_test_audio(audio_file, duration=1.0)
        
        transcriber = WhisperTranscriber(device=DeviceType.CPU, language="en")
        transcriber.transcribe(audio_file, language="es")
        
        call_args = mock_model.transcribe.call_args
        assert call_args[1]["language"] == "es"
    
    @patch('whossper.transcription.whisper_transcriber.whisper')
    def test_unload_model(self, mock_whisper):
        """Test model unloading."""
        mock_model = MagicMock()
        mock_whisper.load_model.return_value = mock_model
        
        transcriber = WhisperTranscriber(device=DeviceType.CPU)
        _ = transcriber.model
        
        assert transcriber.is_model_loaded is True
        
        transcriber.unload_model()
        
        assert transcriber.is_model_loaded is False
    
    @patch('whossper.transcription.whisper_transcriber.whisper')
    def test_get_available_models(self, mock_whisper):
        """Test getting available models."""
        mock_whisper.available_models.return_value = ["tiny", "base", "small"]
        
        transcriber = WhisperTranscriber(device=DeviceType.CPU)
        models = transcriber.get_available_models()
        
        assert models == ["tiny", "base", "small"]


class TestGetModelInfo:
    """Tests for get_model_info helper."""
    
    def test_returns_dict(self):
        """Test get_model_info returns a dict."""
        info = get_model_info()
        assert isinstance(info, dict)
    
    def test_contains_expected_models(self):
        """Test info contains expected models."""
        info = get_model_info()
        
        assert "tiny" in info
        assert "base" in info
        assert "small" in info
        assert "medium" in info
        assert "large" in info
        assert "turbo" in info
    
    def test_model_info_structure(self):
        """Test model info has expected structure."""
        info = get_model_info()
        
        for model_name, model_info in info.items():
            assert "params" in model_info
            assert "speed" in model_info
            assert "english_only" in model_info
    
    def test_english_only_models(self):
        """Test English-only models are marked correctly."""
        info = get_model_info()
        
        assert info["tiny.en"]["english_only"] is True
        assert info["base.en"]["english_only"] is True
        assert info["tiny"]["english_only"] is False
        assert info["base"]["english_only"] is False


class TestWhisperTranscriberModelNames:
    """Tests for model name mapping."""
    
    def test_all_model_sizes_mapped(self):
        """Test all model sizes have a mapping."""
        for size in WhisperModelSize:
            assert size in WhisperTranscriber.MODEL_NAMES
    
    def test_model_name_values(self):
        """Test model name values are correct."""
        assert WhisperTranscriber.MODEL_NAMES[WhisperModelSize.TINY] == "tiny"
        assert WhisperTranscriber.MODEL_NAMES[WhisperModelSize.BASE] == "base"
        assert WhisperTranscriber.MODEL_NAMES[WhisperModelSize.TURBO] == "turbo"


class TestWhisperTranscriberIntegration:
    """Integration tests with real Whisper (if model available)."""
    
    @pytest.mark.slow
    @pytest.mark.skipif(
        os.environ.get('SKIP_SLOW_TESTS') == 'true',
        reason="Skipping slow model loading test"
    )
    def test_real_transcription_tiny(self, tmp_dir):
        """Test actual transcription with tiny model."""
        # Create test audio (sine wave - won't produce meaningful text)
        audio_file = str(tmp_dir / "test.wav")
        create_test_audio(audio_file, duration=2.0, frequency=440)
        
        transcriber = WhisperTranscriber(
            model_size=WhisperModelSize.TINY,
            device=DeviceType.CPU
        )
        
        try:
            result = transcriber.transcribe(audio_file)
            
            # Just verify it returns a result with expected structure
            assert "text" in result
            assert isinstance(result["text"], str)
            
        finally:
            transcriber.unload_model()

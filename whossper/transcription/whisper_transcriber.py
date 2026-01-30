"""Whisper transcription service."""

import logging
import os
from pathlib import Path
from typing import Optional, Union

import torch
import whisper

from whossper.config.schema import WhisperModelSize, DeviceType


logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """Transcribes audio using local OpenAI Whisper model."""
    
    # Map our enum to whisper model names
    MODEL_NAMES = {
        WhisperModelSize.TINY: "tiny",
        WhisperModelSize.TINY_EN: "tiny.en",
        WhisperModelSize.BASE: "base",
        WhisperModelSize.BASE_EN: "base.en",
        WhisperModelSize.SMALL: "small",
        WhisperModelSize.SMALL_EN: "small.en",
        WhisperModelSize.MEDIUM: "medium",
        WhisperModelSize.MEDIUM_EN: "medium.en",
        WhisperModelSize.LARGE: "large",
        WhisperModelSize.LARGE_V1: "large-v1",
        WhisperModelSize.LARGE_V2: "large-v2",
        WhisperModelSize.LARGE_V3: "large-v3",
        WhisperModelSize.TURBO: "turbo",
    }
    
    def __init__(
        self,
        model_size: Union[WhisperModelSize, str] = WhisperModelSize.BASE,
        language: str = "en",
        device: Union[DeviceType, str] = DeviceType.AUTO,
        model_cache_dir: Optional[str] = None,
    ):
        """Initialize Whisper transcriber.
        
        Args:
            model_size: Size of the Whisper model to use.
            language: Language code for transcription.
            device: Device to run inference on.
            model_cache_dir: Directory to cache downloaded models.
        """
        # Handle string inputs
        if isinstance(model_size, str):
            model_size = WhisperModelSize(model_size)
        if isinstance(device, str):
            device = DeviceType(device)
            
        self.model_size = model_size
        self.language = language
        self.device_type = device
        self.model_cache_dir = model_cache_dir
        
        self._model: Optional[whisper.Whisper] = None
        self._device: Optional[str] = None
    
    def _get_device(self) -> str:
        """Determine the device to use for inference.
        
        Returns:
            Device string for torch.
        """
        if self.device_type == DeviceType.AUTO:
            if torch.cuda.is_available():
                return "cuda"
            elif torch.backends.mps.is_available():
                return "mps"
            else:
                return "cpu"
        else:
            return self.device_type.value
    
    def _load_model(self) -> whisper.Whisper:
        """Load the Whisper model.
        
        Returns:
            Loaded Whisper model.
        """
        if self._model is not None:
            return self._model
        
        self._device = self._get_device()
        model_name = self.MODEL_NAMES.get(self.model_size, self.model_size.value)
        
        logger.info(f"Loading Whisper model '{model_name}' on device '{self._device}'")
        
        # Set download root if specified
        download_root = self.model_cache_dir
        if download_root:
            os.makedirs(download_root, exist_ok=True)
        
        self._model = whisper.load_model(
            model_name,
            device=self._device,
            download_root=download_root
        )
        
        logger.info(f"Model loaded successfully")
        return self._model
    
    @property
    def model(self) -> whisper.Whisper:
        """Get the loaded model, loading if necessary."""
        return self._load_model()
    
    @property
    def device(self) -> str:
        """Get the device being used."""
        if self._device is None:
            self._device = self._get_device()
        return self._device
    
    @property
    def is_model_loaded(self) -> bool:
        """Check if model is currently loaded."""
        return self._model is not None
    
    def transcribe(
        self,
        audio_path: Union[str, Path],
        language: Optional[str] = None,
        task: str = "transcribe",
        **kwargs
    ) -> dict:
        """Transcribe audio file to text.
        
        Args:
            audio_path: Path to audio file.
            language: Override language for this transcription.
            task: "transcribe" or "translate".
            **kwargs: Additional arguments passed to whisper.transcribe.
            
        Returns:
            Transcription result dict with 'text', 'segments', etc.
            
        Raises:
            FileNotFoundError: If audio file doesn't exist.
            ValueError: If audio file is invalid.
        """
        import sys
        
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        lang = language or self.language
        
        logger.info(f"Transcribing {audio_path} with language={lang}")
        logger.debug(f"Audio file size: {audio_path.stat().st_size} bytes")
        
        # Flush to ensure logs are written before potential crash
        sys.stdout.flush()
        sys.stderr.flush()
        
        try:
            logger.debug("Calling whisper model.transcribe()...")
            print(f"DEBUG: About to call model.transcribe() on {audio_path}", file=sys.stderr, flush=True)
            
            result = self.model.transcribe(
                str(audio_path),
                language=lang,
                task=task,
                fp16=False,  # Disable FP16 to avoid potential issues
                **kwargs
            )
            
            print(f"DEBUG: model.transcribe() completed successfully", file=sys.stderr, flush=True)
            logger.debug(f"Whisper transcribe() returned successfully")
            
            text = result.get('text', '')
            logger.info(f"Transcription complete: {len(text)} chars")
            logger.debug(f"Transcription result: '{text}'")
            return result
            
        except Exception as e:
            print(f"DEBUG: model.transcribe() raised exception: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
            logger.exception(f"Transcription failed with exception: {type(e).__name__}: {e}")
            raise
    
    def transcribe_to_text(
        self,
        audio_path: Union[str, Path],
        language: Optional[str] = None,
        **kwargs
    ) -> str:
        """Transcribe audio file and return just the text.
        
        Args:
            audio_path: Path to audio file.
            language: Override language for this transcription.
            **kwargs: Additional arguments passed to transcribe.
            
        Returns:
            Transcribed text string.
        """
        result = self.transcribe(audio_path, language=language, **kwargs)
        return result.get("text", "").strip()
    
    def get_available_models(self) -> list[str]:
        """Get list of available Whisper model names.
        
        Returns:
            List of model name strings.
        """
        return whisper.available_models()
    
    def unload_model(self) -> None:
        """Unload the model to free memory."""
        if self._model is not None:
            del self._model
            self._model = None
            
            # Clear CUDA cache if using GPU
            if self._device == "cuda" and torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            logger.info("Model unloaded")
    
    def __del__(self):
        """Destructor to clean up resources."""
        self.unload_model()


def get_model_info() -> dict[str, dict]:
    """Get information about available Whisper models.
    
    Returns:
        Dict mapping model names to their info.
    """
    return {
        "tiny": {"params": "39M", "speed": "~10x", "english_only": False},
        "tiny.en": {"params": "39M", "speed": "~10x", "english_only": True},
        "base": {"params": "74M", "speed": "~7x", "english_only": False},
        "base.en": {"params": "74M", "speed": "~7x", "english_only": True},
        "small": {"params": "244M", "speed": "~4x", "english_only": False},
        "small.en": {"params": "244M", "speed": "~4x", "english_only": True},
        "medium": {"params": "769M", "speed": "~2x", "english_only": False},
        "medium.en": {"params": "769M", "speed": "~2x", "english_only": True},
        "large": {"params": "1.5B", "speed": "1x", "english_only": False},
        "large-v1": {"params": "1.5B", "speed": "1x", "english_only": False},
        "large-v2": {"params": "1.5B", "speed": "1x", "english_only": False},
        "large-v3": {"params": "1.5B", "speed": "1x", "english_only": False},
        "turbo": {"params": "809M", "speed": "~8x", "english_only": False},
    }


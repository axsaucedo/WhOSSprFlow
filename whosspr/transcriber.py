"""Whisper transcription.

Simple wrapper around OpenAI Whisper for speech-to-text.
"""

import logging
from typing import Optional

import numpy as np
import torch
import whisper

from whosspr.config import ModelSize, DeviceType


logger = logging.getLogger(__name__)


# Map enum values to whisper model names
MODEL_NAMES = {
    ModelSize.TINY: "tiny",
    ModelSize.TINY_EN: "tiny.en",
    ModelSize.BASE: "base",
    ModelSize.BASE_EN: "base.en",
    ModelSize.SMALL: "small",
    ModelSize.SMALL_EN: "small.en",
    ModelSize.MEDIUM: "medium",
    ModelSize.MEDIUM_EN: "medium.en",
    ModelSize.LARGE: "large",
    ModelSize.LARGE_V2: "large-v2",
    ModelSize.LARGE_V3: "large-v3",
    ModelSize.TURBO: "turbo",
}


def get_device(device_type: DeviceType) -> str:
    """Determine the best device for inference."""
    if device_type == DeviceType.AUTO:
        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"
        return "cpu"
    return device_type.value


class Transcriber:
    """Transcribes audio to text using Whisper."""
    
    def __init__(
        self,
        model_size: ModelSize = ModelSize.BASE,
        language: str = "en",
        device: DeviceType = DeviceType.AUTO,
    ):
        """Initialize transcriber.
        
        Args:
            model_size: Whisper model size.
            language: Language code (e.g., "en", "es").
            device: Device for inference (auto/cpu/cuda/mps).
        """
        self.model_size = model_size
        self.language = language
        self._device = get_device(device)
        self._model: Optional[whisper.Whisper] = None
    
    def _ensure_model(self) -> whisper.Whisper:
        """Load model if not already loaded."""
        if self._model is None:
            name = MODEL_NAMES.get(self.model_size, self.model_size.value)
            logger.info(f"Loading Whisper model '{name}' on {self._device}")
            self._model = whisper.load_model(name, device=self._device)
            logger.info("Model loaded")
        return self._model
    
    @property
    def model(self) -> whisper.Whisper:
        """Get the loaded model."""
        return self._ensure_model()
    
    @property
    def device(self) -> str:
        """Get the device being used."""
        return self._device
    
    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe audio to text.
        
        Args:
            audio: Audio as numpy array (float32, 16kHz mono).
            
        Returns:
            Transcribed text.
        """
        # Ensure correct format
        if audio.ndim > 1:
            audio = audio.flatten()
        audio = audio.astype(np.float32)
        
        logger.info(f"Transcribing {len(audio)/16000:.2f}s of audio")
        
        result = self.model.transcribe(audio, language=self.language, fp16=False)
        text = result.get("text", "").strip()
        
        logger.info(f"Transcribed: {text[:50]}..." if len(text) > 50 else f"Transcribed: {text}")
        return text
    
    def unload(self) -> None:
        """Unload model to free memory."""
        if self._model is not None:
            del self._model
            self._model = None
            if self._device == "cuda":
                torch.cuda.empty_cache()
            logger.info("Model unloaded")

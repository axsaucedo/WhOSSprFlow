"""Audio recording using sounddevice.

Simple, focused module for capturing audio from the microphone.
"""

import logging
from typing import Optional

import numpy as np
import sounddevice as sd


logger = logging.getLogger(__name__)


class AudioRecorder:
    """Records audio from the microphone using sounddevice.
    
    Uses a callback-based approach where sounddevice handles threading internally.
    No additional locks needed - the callback appends to a list which is thread-safe
    for single-producer scenarios.
    """
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        """Initialize recorder.
        
        Args:
            sample_rate: Sample rate in Hz (default 16000 for Whisper).
            channels: Number of channels (default 1 for mono).
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self._frames: list[np.ndarray] = []
        self._stream: Optional[sd.InputStream] = None
        self._recording = False
    
    def _callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        """Audio stream callback - called by sounddevice's internal thread."""
        if status:
            logger.warning(f"Audio status: {status}")
        if self._recording:
            self._frames.append(indata.copy())
    
    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._recording
    
    @property
    def duration(self) -> float:
        """Get current recording duration in seconds."""
        if not self._frames:
            return 0.0
        total = sum(len(f) for f in self._frames)
        return total / self.sample_rate
    
    def start(self) -> bool:
        """Start recording.
        
        Returns:
            True if started successfully.
        """
        if self._recording:
            return False
        
        try:
            self._frames = []
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=np.float32,
                callback=self._callback,
            )
            self._stream.start()
            self._recording = True
            logger.info("Recording started")
            return True
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            return False
    
    def stop(self) -> Optional[np.ndarray]:
        """Stop recording and return audio data.
        
        Returns:
            Audio as numpy array (float32, mono), or None if no data.
        """
        if not self._recording:
            return None
        
        self._recording = False
        
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        
        if not self._frames:
            return None
        
        audio = np.concatenate(self._frames, axis=0).flatten()
        self._frames = []
        
        logger.info(f"Recorded {len(audio)/self.sample_rate:.2f}s")
        return audio
    
    def cancel(self) -> None:
        """Cancel recording, discarding any data."""
        self._recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._frames = []
        logger.info("Recording cancelled")

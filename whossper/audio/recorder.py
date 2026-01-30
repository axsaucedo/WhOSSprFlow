"""Audio recorder using PyAudio."""

import logging
import tempfile
import threading
import time
import wave
from pathlib import Path
from typing import Callable, Optional

import pyaudio


logger = logging.getLogger(__name__)


class AudioRecorder:
    """Records audio from the microphone using PyAudio."""
    
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024,
        audio_format: int = pyaudio.paInt16,
        tmp_dir: str = "./tmp",
        on_recording_complete: Optional[Callable[[str], None]] = None,
    ):
        """Initialize audio recorder.
        
        Args:
            sample_rate: Audio sample rate in Hz.
            channels: Number of audio channels.
            chunk_size: Size of audio chunks for recording.
            audio_format: PyAudio format constant.
            tmp_dir: Directory for temporary audio files.
            on_recording_complete: Callback when recording completes.
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.audio_format = audio_format
        self.tmp_dir = Path(tmp_dir)
        self.on_recording_complete = on_recording_complete
        
        self._audio: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None
        self._frames: list[bytes] = []
        self._is_recording = False
        self._start_time: float = 0
        self._lock = threading.Lock()
        
        # Ensure tmp directory exists
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
    
    def _initialize_audio(self) -> bool:
        """Initialize PyAudio instance.
        
        Returns:
            True if initialization succeeded.
        """
        if self._audio is None:
            try:
                self._audio = pyaudio.PyAudio()
                logger.debug("PyAudio initialized successfully")
                return True
            except Exception as e:
                logger.error(f"Failed to initialize PyAudio: {e}")
                self._audio = None
                return False
        return True
    
    def _cleanup_stream(self) -> None:
        """Clean up the audio stream."""
        with self._lock:
            if self._stream is not None:
                try:
                    if self._stream.is_active():
                        self._stream.stop_stream()
                    self._stream.close()
                except Exception as e:
                    logger.warning(f"Stream cleanup error: {e}")
                finally:
                    self._stream = None
    
    def _audio_callback(
        self,
        in_data: bytes,
        frame_count: int,
        time_info: dict,
        status: int
    ) -> tuple[bytes, int]:
        """Audio stream callback to collect frames.
        
        Args:
            in_data: Audio data from stream.
            frame_count: Number of frames.
            time_info: Timing information.
            status: Stream status.
            
        Returns:
            Tuple of (data, continue flag).
        """
        with self._lock:
            if self._is_recording:
                self._frames.append(in_data)
        return (in_data, pyaudio.paContinue)
    
    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._is_recording
    
    @property
    def recording_duration(self) -> float:
        """Get current recording duration in seconds."""
        if not self._is_recording:
            return 0.0
        return time.time() - self._start_time
    
    @property
    def frames_recorded(self) -> int:
        """Get number of frames recorded."""
        return len(self._frames)
    
    def start_recording(self) -> bool:
        """Start audio recording.
        
        Returns:
            True if recording started successfully.
        """
        if self._is_recording:
            logger.warning("Already recording")
            return False
        
        if not self._initialize_audio():
            return False
        
        try:
            self._frames = []
            
            self._stream = self._audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback
            )
            
            self._is_recording = True
            self._start_time = time.time()
            
            logger.info("Started recording")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self._cleanup_stream()
            return False
    
    def stop_recording(self, min_duration: float = 0.5) -> Optional[str]:
        """Stop audio recording and save to file.
        
        Args:
            min_duration: Minimum recording duration in seconds.
            
        Returns:
            Path to recorded audio file, or None if failed.
            
        Raises:
            ValueError: If recording is too short.
        """
        if not self._is_recording:
            logger.warning("Not currently recording")
            return None
        
        try:
            # Calculate actual duration from frames
            duration = (len(self._frames) * self.chunk_size) / self.sample_rate
            
            if duration < min_duration:
                logger.warning(f"Recording too short: {duration:.2f}s < {min_duration}s")
                raise ValueError(
                    f"Recording must be at least {min_duration} seconds long "
                    f"(was {duration:.2f}s)"
                )
            
            if not self._frames:
                logger.error("No audio frames captured")
                return None
            
            # Save to temp file
            audio_file = self._save_audio()
            
            logger.info(f"Stopped recording, saved to {audio_file} ({duration:.2f}s)")
            
            # Call completion callback if set
            if self.on_recording_complete and audio_file:
                self.on_recording_complete(audio_file)
            
            return audio_file
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to stop recording: {e}")
            return None
        finally:
            self._cleanup_stream()
            self._is_recording = False
    
    def _save_audio(self) -> Optional[str]:
        """Save recorded frames to a WAV file.
        
        Returns:
            Path to saved file, or None if failed.
        """
        if not self._frames or self._audio is None:
            return None
        
        try:
            # Create temp file in our tmp directory
            timestamp = int(time.time() * 1000)
            filename = self.tmp_dir / f"recording_{timestamp}.wav"
            
            with wave.open(str(filename), 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self._audio.get_sample_size(self.audio_format))
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join(self._frames))
            
            return str(filename)
            
        except Exception as e:
            logger.error(f"Failed to save audio: {e}")
            return None
    
    def cancel_recording(self) -> None:
        """Cancel recording without saving."""
        logger.info("Cancelling recording")
        self._cleanup_stream()
        self._is_recording = False
        self._frames = []
    
    def cleanup(self) -> None:
        """Clean up all resources."""
        self._cleanup_stream()
        if self._audio is not None:
            try:
                self._audio.terminate()
            except Exception as e:
                logger.warning(f"PyAudio termination error: {e}")
            finally:
                self._audio = None
    
    def __del__(self):
        """Destructor to clean up resources."""
        self.cleanup()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
        return False


def create_test_audio(
    filename: str,
    duration: float = 2.0,
    sample_rate: int = 16000,
    frequency: float = 440.0
) -> str:
    """Create a test audio file with a sine wave.
    
    Args:
        filename: Output filename.
        duration: Duration in seconds.
        sample_rate: Sample rate in Hz.
        frequency: Frequency of sine wave in Hz.
        
    Returns:
        Path to created file.
    """
    import struct
    import math
    
    num_samples = int(sample_rate * duration)
    
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        
        for i in range(num_samples):
            value = int(32767 * 0.5 * math.sin(2 * math.pi * frequency * i / sample_rate))
            wf.writeframes(struct.pack('<h', value))
    
    return filename


"""WhOSSper Core - Audio recording, transcription, keyboard shortcuts, and text insertion.

This module consolidates all core functionality into a single file for simplicity.
"""

import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
import wave
from enum import Enum
from pathlib import Path
from typing import Callable, Optional, Set

import numpy as np
import sounddevice as sd
import torch
import whisper
import pyperclip
from pynput import keyboard
from pynput.keyboard import Key, KeyCode, Controller

from whossper.config_new import Config, ModelSize, DeviceType


logger = logging.getLogger(__name__)


# =============================================================================
# Dictation State
# =============================================================================

class DictationState(str, Enum):
    """Current state of the dictation system."""
    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"
    ENHANCING = "enhancing"
    INSERTING = "inserting"
    ERROR = "error"


# =============================================================================
# Audio Recorder (using sounddevice)
# =============================================================================

class AudioRecorder:
    """Simple audio recording using sounddevice."""
    
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        dtype: np.dtype = np.float32,
    ):
        """Initialize audio recorder.
        
        Args:
            sample_rate: Sample rate in Hz.
            channels: Number of audio channels.
            dtype: NumPy dtype for audio data.
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        
        self._recording = False
        self._frames: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._stream: Optional[sd.InputStream] = None
    
    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info,
        status: sd.CallbackFlags
    ) -> None:
        """Callback for audio stream."""
        if status:
            logger.warning(f"Audio stream status: {status}")
        
        with self._lock:
            if self._recording:
                self._frames.append(indata.copy())
    
    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._recording
    
    def start(self) -> bool:
        """Start recording audio.
        
        Returns:
            True if recording started successfully.
        """
        if self._recording:
            logger.warning("Already recording")
            return False
        
        try:
            self._frames = []
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                callback=self._audio_callback,
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
            NumPy array of audio data, or None if no data.
        """
        if not self._recording:
            logger.warning("Not recording")
            return None
        
        self._recording = False
        
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        
        with self._lock:
            if not self._frames:
                logger.warning("No audio frames recorded")
                return None
            
            audio = np.concatenate(self._frames, axis=0)
            self._frames = []
        
        duration = len(audio) / self.sample_rate
        logger.info(f"Recording stopped: {duration:.2f}s, {len(audio)} samples")
        return audio
    
    def cancel(self) -> None:
        """Cancel recording without returning data."""
        self._recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            self._frames = []
        logger.info("Recording cancelled")
    
    @property
    def duration(self) -> float:
        """Get current recording duration in seconds."""
        with self._lock:
            if not self._frames:
                return 0.0
            total_samples = sum(len(f) for f in self._frames)
            return total_samples / self.sample_rate


# =============================================================================
# Transcriber (using Whisper)
# =============================================================================

class Transcriber:
    """Whisper-based audio transcription."""
    
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
    
    def __init__(
        self,
        model_size: ModelSize = ModelSize.BASE,
        language: str = "en",
        device: DeviceType = DeviceType.AUTO,
        cache_dir: Optional[str] = None,
    ):
        """Initialize transcriber.
        
        Args:
            model_size: Whisper model size.
            language: Language code for transcription.
            device: Device to run inference on.
            cache_dir: Directory for model cache.
        """
        self.model_size = model_size
        self.language = language
        self.device_type = device
        self.cache_dir = cache_dir
        
        self._model: Optional[whisper.Whisper] = None
        self._device: Optional[str] = None
    
    def _get_device(self) -> str:
        """Determine device for inference."""
        if self.device_type == DeviceType.AUTO:
            if torch.cuda.is_available():
                return "cuda"
            elif torch.backends.mps.is_available():
                return "mps"
            else:
                return "cpu"
        return self.device_type.value
    
    def _load_model(self) -> whisper.Whisper:
        """Load Whisper model (lazy loading)."""
        if self._model is not None:
            return self._model
        
        self._device = self._get_device()
        model_name = self.MODEL_NAMES.get(self.model_size, self.model_size.value)
        
        logger.info(f"Loading Whisper model '{model_name}' on '{self._device}'")
        
        self._model = whisper.load_model(
            model_name,
            device=self._device,
            download_root=self.cache_dir,
        )
        
        logger.info("Model loaded")
        return self._model
    
    @property
    def model(self) -> whisper.Whisper:
        """Get loaded model."""
        return self._load_model()
    
    @property
    def device(self) -> str:
        """Get device being used."""
        if self._device is None:
            self._device = self._get_device()
        return self._device
    
    def transcribe(
        self,
        audio: np.ndarray,
        language: Optional[str] = None,
    ) -> str:
        """Transcribe audio to text.
        
        Args:
            audio: Audio data as numpy array (float32, 16kHz).
            language: Optional language override.
            
        Returns:
            Transcribed text.
        """
        lang = language or self.language
        
        # Ensure audio is float32 and 1D
        if audio.ndim > 1:
            audio = audio.flatten()
        audio = audio.astype(np.float32)
        
        logger.info(f"Transcribing {len(audio)/16000:.2f}s of audio")
        
        result = self.model.transcribe(
            audio,
            language=lang,
            fp16=False,
        )
        
        text = result.get("text", "").strip()
        logger.info(f"Transcribed: {text[:50]}..." if len(text) > 50 else f"Transcribed: {text}")
        return text
    
    def unload(self) -> None:
        """Unload model to free memory."""
        if self._model is not None:
            del self._model
            self._model = None
            if self._device == "cuda" and torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info("Model unloaded")


# =============================================================================
# Text Inserter
# =============================================================================

class TextInserter:
    """Insert text into applications via clipboard paste."""
    
    def __init__(self, paste_delay: float = 0.1):
        """Initialize text inserter.
        
        Args:
            paste_delay: Delay after paste to ensure completion.
        """
        self.keyboard = Controller()
        self.paste_delay = paste_delay
    
    def insert(self, text: str) -> bool:
        """Insert text using clipboard paste (Cmd+V).
        
        Args:
            text: Text to insert.
            
        Returns:
            True if successful.
        """
        if not text:
            logger.warning("Empty text, nothing to insert")
            return False
        
        try:
            # Copy to clipboard
            pyperclip.copy(text)
            time.sleep(0.05)
            
            # Paste with Cmd+V
            with self.keyboard.pressed(Key.cmd):
                self.keyboard.press('v')
                self.keyboard.release('v')
            
            time.sleep(self.paste_delay)
            logger.info(f"Inserted {len(text)} chars")
            return True
            
        except Exception as e:
            logger.error(f"Failed to insert text: {e}")
            return False
    
    def type_text(self, text: str, delay: float = 0.01) -> bool:
        """Insert text by typing each character.
        
        Args:
            text: Text to type.
            delay: Delay between keystrokes.
            
        Returns:
            True if successful.
        """
        if not text:
            return False
        
        try:
            for char in text:
                self.keyboard.type(char)
                time.sleep(delay)
            return True
        except Exception as e:
            logger.error(f"Failed to type text: {e}")
            return False


# =============================================================================
# Keyboard Shortcuts
# =============================================================================

class ShortcutMode(str, Enum):
    """Shortcut activation mode."""
    HOLD = "hold"
    TOGGLE = "toggle"


class KeyboardShortcuts:
    """Global keyboard shortcut handler."""
    
    KEY_MAP = {
        "ctrl": Key.ctrl, "control": Key.ctrl,
        "cmd": Key.cmd, "command": Key.cmd,
        "alt": Key.alt, "option": Key.alt,
        "shift": Key.shift,
        "space": Key.space,
        "enter": Key.enter, "return": Key.enter,
        "tab": Key.tab,
        "escape": Key.esc, "esc": Key.esc,
        "f1": Key.f1, "f2": Key.f2, "f3": Key.f3, "f4": Key.f4,
        "f5": Key.f5, "f6": Key.f6, "f7": Key.f7, "f8": Key.f8,
        "f9": Key.f9, "f10": Key.f10, "f11": Key.f11, "f12": Key.f12,
    }
    
    def __init__(self):
        """Initialize keyboard shortcuts handler."""
        self._listener: Optional[keyboard.Listener] = None
        self._pressed: Set = set()
        self._shortcuts: dict = {}
        self._running = False
        self._lock = threading.Lock()
    
    @classmethod
    def parse_shortcut(cls, shortcut: str) -> frozenset:
        """Parse shortcut string to key set.
        
        Args:
            shortcut: String like "ctrl+cmd+1".
            
        Returns:
            Frozenset of keys.
        """
        keys = set()
        for part in shortcut.lower().replace(" ", "").split("+"):
            if part in cls.KEY_MAP:
                keys.add(cls.KEY_MAP[part])
            elif len(part) == 1:
                keys.add(KeyCode.from_char(part))
            else:
                logger.warning(f"Unknown key: {part}")
        return frozenset(keys)
    
    def _normalize(self, key) -> Key:
        """Normalize key (left/right modifiers to generic)."""
        if hasattr(key, 'name'):
            if key in (Key.ctrl_l, Key.ctrl_r):
                return Key.ctrl
            if key in (Key.alt_l, Key.alt_r):
                return Key.alt
            if key in (Key.shift_l, Key.shift_r):
                return Key.shift
            if key in (Key.cmd_l, Key.cmd_r):
                return Key.cmd
        return key
    
    def register(
        self,
        shortcut: str,
        on_press: Callable[[], None],
        mode: ShortcutMode = ShortcutMode.TOGGLE,
        on_release: Optional[Callable[[], None]] = None,
    ) -> None:
        """Register a keyboard shortcut.
        
        Args:
            shortcut: Shortcut string like "ctrl+cmd+1".
            on_press: Callback when shortcut is activated.
            mode: HOLD or TOGGLE.
            on_release: For HOLD mode, called on release.
        """
        keys = self.parse_shortcut(shortcut)
        if not keys:
            logger.error(f"Invalid shortcut: {shortcut}")
            return
        
        with self._lock:
            self._shortcuts[keys] = {
                "on_press": on_press,
                "on_release": on_release,
                "mode": mode,
                "active": False,
            }
        logger.info(f"Registered shortcut: {shortcut} ({mode.value})")
    
    def _on_press(self, key) -> None:
        """Handle key press."""
        norm = self._normalize(key)
        with self._lock:
            self._pressed.add(key)
            if norm != key:
                self._pressed.add(norm)
            
            for keys, info in self._shortcuts.items():
                if keys.issubset(self._pressed) and not info["active"]:
                    info["active"] = True
                    try:
                        info["on_press"]()
                    except Exception as e:
                        logger.error(f"Shortcut callback error: {e}")
    
    def _on_release(self, key) -> None:
        """Handle key release."""
        norm = self._normalize(key)
        with self._lock:
            self._pressed.discard(key)
            self._pressed.discard(norm)
            
            for keys, info in self._shortcuts.items():
                if info["active"] and not keys.issubset(self._pressed):
                    info["active"] = False
                    if info["mode"] == ShortcutMode.HOLD and info["on_release"]:
                        try:
                            info["on_release"]()
                        except Exception as e:
                            logger.error(f"Release callback error: {e}")
    
    def start(self) -> bool:
        """Start listening for shortcuts.
        
        Returns:
            True if started successfully.
        """
        if self._running:
            return False
        
        try:
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            )
            self._listener.start()
            self._running = True
            logger.info("Keyboard listener started")
            return True
        except Exception as e:
            logger.error(f"Failed to start listener: {e}")
            return False
    
    def stop(self) -> None:
        """Stop listening."""
        if self._listener:
            self._listener.stop()
            self._listener = None
        self._running = False
        self._pressed.clear()
        logger.info("Keyboard listener stopped")
    
    @property
    def is_running(self) -> bool:
        """Check if listener is running."""
        return self._running
    
    @property
    def is_alive(self) -> bool:
        """Check if listener thread is alive."""
        return self._listener is not None and self._listener.is_alive()


# =============================================================================
# Permissions Checker
# =============================================================================

class PermissionStatus(str, Enum):
    """Permission status."""
    GRANTED = "granted"
    DENIED = "denied"
    UNKNOWN = "unknown"


def check_microphone_permission() -> PermissionStatus:
    """Check if microphone permission is granted."""
    if sys.platform != "darwin":
        return PermissionStatus.GRANTED
    
    try:
        # Try to open a brief audio stream
        with sd.InputStream(channels=1, samplerate=16000):
            pass
        return PermissionStatus.GRANTED
    except Exception:
        return PermissionStatus.DENIED


def check_accessibility_permission() -> PermissionStatus:
    """Check if accessibility permission is granted."""
    if sys.platform != "darwin":
        return PermissionStatus.GRANTED
    
    try:
        result = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to return ""'],
            capture_output=True,
            timeout=5,
        )
        return PermissionStatus.GRANTED if result.returncode == 0 else PermissionStatus.DENIED
    except Exception:
        return PermissionStatus.UNKNOWN


def check_permissions() -> dict[str, PermissionStatus]:
    """Check all required permissions."""
    return {
        "microphone": check_microphone_permission(),
        "accessibility": check_accessibility_permission(),
    }


# =============================================================================
# Dictation Controller
# =============================================================================

class DictationController:
    """Main controller orchestrating recording, transcription, and text insertion."""
    
    def __init__(
        self,
        config: Config,
        on_state: Optional[Callable[[DictationState], None]] = None,
        on_text: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        enhancer: Optional[Callable[[str], str]] = None,
    ):
        """Initialize dictation controller.
        
        Args:
            config: Application configuration.
            on_state: Callback when state changes.
            on_text: Callback when transcription completes.
            on_error: Callback when error occurs.
            enhancer: Optional function to enhance transcribed text.
        """
        self.config = config
        self.on_state = on_state
        self.on_text = on_text
        self.on_error = on_error
        self.enhancer = enhancer
        
        self._state = DictationState.IDLE
        self._lock = threading.Lock()
        
        # Ensure tmp directory
        Path(config.tmp_dir).mkdir(parents=True, exist_ok=True)
        
        # Components (lazy init)
        self._recorder: Optional[AudioRecorder] = None
        self._transcriber: Optional[Transcriber] = None
        self._inserter: Optional[TextInserter] = None
        self._shortcuts: Optional[KeyboardShortcuts] = None
        self._processing_thread: Optional[threading.Thread] = None
        
        logger.info("DictationController initialized")
    
    @property
    def state(self) -> DictationState:
        """Get current state."""
        return self._state
    
    def _set_state(self, state: DictationState) -> None:
        """Set state and notify callback."""
        with self._lock:
            if self._state != state:
                self._state = state
                logger.debug(f"State: {state.value}")
                if self.on_state:
                    try:
                        self.on_state(state)
                    except Exception as e:
                        logger.error(f"State callback error: {e}")
    
    def _get_recorder(self) -> AudioRecorder:
        """Get or create audio recorder."""
        if self._recorder is None:
            self._recorder = AudioRecorder(
                sample_rate=self.config.audio.sample_rate,
                channels=self.config.audio.channels,
            )
        return self._recorder
    
    def _get_transcriber(self) -> Transcriber:
        """Get or create transcriber."""
        if self._transcriber is None:
            self._transcriber = Transcriber(
                model_size=self.config.whisper.model_size,
                language=self.config.whisper.language,
                device=self.config.whisper.device,
                cache_dir=self.config.whisper.model_cache_dir,
            )
        return self._transcriber
    
    def _get_inserter(self) -> TextInserter:
        """Get or create text inserter."""
        if self._inserter is None:
            self._inserter = TextInserter()
        return self._inserter
    
    def _get_shortcuts(self) -> KeyboardShortcuts:
        """Get or create keyboard shortcuts handler."""
        if self._shortcuts is None:
            self._shortcuts = KeyboardShortcuts()
        return self._shortcuts
    
    def start_recording(self) -> bool:
        """Start audio recording.
        
        Returns:
            True if recording started.
        """
        if self._state != DictationState.IDLE:
            logger.warning(f"Cannot record in state: {self._state}")
            return False
        
        if self._get_recorder().start():
            self._set_state(DictationState.RECORDING)
            return True
        
        self._handle_error("Failed to start recording")
        return False
    
    def stop_recording(self) -> bool:
        """Stop recording and process audio.
        
        Returns:
            True if processing started.
        """
        if self._state != DictationState.RECORDING:
            logger.warning(f"Cannot stop in state: {self._state}")
            return False
        
        audio = self._get_recorder().stop()
        
        if audio is None or len(audio) / self.config.audio.sample_rate < self.config.audio.min_duration:
            logger.warning("Recording too short")
            self._set_state(DictationState.IDLE)
            return False
        
        # Process in background
        self._processing_thread = threading.Thread(
            target=self._process_audio,
            args=(audio,),
            daemon=True,
        )
        self._processing_thread.start()
        return True
    
    def cancel_recording(self) -> None:
        """Cancel current recording."""
        if self._state == DictationState.RECORDING:
            self._get_recorder().cancel()
            self._set_state(DictationState.IDLE)
    
    def _process_audio(self, audio: np.ndarray) -> None:
        """Process recorded audio (runs in background thread)."""
        try:
            # Transcribe
            self._set_state(DictationState.TRANSCRIBING)
            text = self._get_transcriber().transcribe(audio)
            
            if not text:
                logger.warning("Empty transcription")
                self._set_state(DictationState.IDLE)
                return
            
            # Enhance if available
            if self.enhancer:
                self._set_state(DictationState.ENHANCING)
                try:
                    text = self.enhancer(text)
                except Exception as e:
                    logger.warning(f"Enhancement failed: {e}")
            
            # Insert text
            self._set_state(DictationState.INSERTING)
            self._get_inserter().insert(text)
            
            # Notify
            if self.on_text:
                try:
                    self.on_text(text)
                except Exception as e:
                    logger.error(f"Text callback error: {e}")
            
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            self._handle_error(str(e))
        finally:
            self._set_state(DictationState.IDLE)
    
    def _handle_error(self, message: str) -> None:
        """Handle error."""
        logger.error(message)
        self._set_state(DictationState.ERROR)
        if self.on_error:
            try:
                self.on_error(message)
            except Exception:
                pass
        time.sleep(0.5)
        self._set_state(DictationState.IDLE)
    
    def _toggle_dictation(self) -> None:
        """Toggle recording on/off."""
        if self._state == DictationState.IDLE:
            self.start_recording()
        elif self._state == DictationState.RECORDING:
            self.stop_recording()
    
    def setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts from config."""
        shortcuts = self._get_shortcuts()
        
        if self.config.shortcuts.hold_to_dictate:
            shortcuts.register(
                self.config.shortcuts.hold_to_dictate,
                on_press=self.start_recording,
                mode=ShortcutMode.HOLD,
                on_release=self.stop_recording,
            )
        
        if self.config.shortcuts.toggle_dictation:
            shortcuts.register(
                self.config.shortcuts.toggle_dictation,
                on_press=self._toggle_dictation,
                mode=ShortcutMode.TOGGLE,
            )
    
    def start(self) -> bool:
        """Start the dictation service.
        
        Returns:
            True if started successfully.
        """
        # Pre-load model
        logger.info("Pre-loading Whisper model...")
        _ = self._get_transcriber().model
        logger.info("Model loaded")
        
        # Setup and start shortcuts
        self.setup_shortcuts()
        if not self._get_shortcuts().start():
            self._handle_error("Failed to start keyboard listener")
            return False
        
        logger.info("Dictation service started")
        return True
    
    def stop(self) -> None:
        """Stop the dictation service."""
        if self._state == DictationState.RECORDING:
            self.cancel_recording()
        
        if self._shortcuts:
            self._shortcuts.stop()
        
        if self._transcriber:
            self._transcriber.unload()
        
        logger.info("Dictation service stopped")
    
    def wait_for_processing(self, timeout: Optional[float] = None) -> bool:
        """Wait for background processing to complete.
        
        Args:
            timeout: Max time to wait.
            
        Returns:
            True if completed.
        """
        if self._processing_thread:
            self._processing_thread.join(timeout=timeout)
            return not self._processing_thread.is_alive()
        return True
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        self.stop()
        return False

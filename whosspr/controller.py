"""Dictation controller - orchestrates recording, transcription, and insertion.

This is the main coordinator that ties together all the components.
Simplified design: sequential processing, minimal threading.
"""

import logging
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from whosspr.config import Config
from whosspr.recorder import AudioRecorder
from whosspr.transcriber import Transcriber
from whosspr.inserter import TextInserter
from whosspr.keyboard import KeyboardShortcuts, ShortcutMode


logger = logging.getLogger(__name__)


class DictationState(str, Enum):
    """Current state of the dictation system."""
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"  # transcribing + enhancing + inserting


class DictationController:
    """Orchestrates the dictation workflow.
    
    Flow: User presses shortcut → record audio → transcribe → enhance → insert text.
    
    Design decisions:
    - Sequential processing (user waits during transcription anyway)
    - State callbacks for UI feedback
    - Optional enhancer function
    """
    
    def __init__(
        self,
        config: Config,
        on_state: Optional[Callable[[DictationState], None]] = None,
        on_text: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        enhancer: Optional[Callable[[str], str]] = None,
    ):
        """Initialize controller.
        
        Args:
            config: Application configuration.
            on_state: Called when state changes.
            on_text: Called with transcribed text.
            on_error: Called on errors.
            enhancer: Optional function to enhance transcribed text.
        """
        self.config = config
        self.on_state = on_state
        self.on_text = on_text
        self.on_error = on_error
        self.enhancer = enhancer
        
        self._state = DictationState.IDLE
        
        # Create tmp directory
        Path(config.tmp_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self._recorder = AudioRecorder(
            sample_rate=config.audio.sample_rate,
            channels=config.audio.channels,
        )
        self._transcriber = Transcriber(
            model_size=config.whisper.model_size,
            language=config.whisper.language,
            device=config.whisper.device,
        )
        self._inserter = TextInserter()
        self._prepend_space = config.audio.prepend_space
        self._shortcuts = KeyboardShortcuts()
    
    @property
    def state(self) -> DictationState:
        """Get current state."""
        return self._state
    
    def _set_state(self, state: DictationState) -> None:
        """Update state and notify callback."""
        if self._state != state:
            self._state = state
            logger.debug(f"State: {state.value}")
            if self.on_state:
                try:
                    self.on_state(state)
                except Exception as e:
                    logger.error(f"State callback error: {e}")
    
    def _handle_error(self, message: str) -> None:
        """Handle an error."""
        logger.error(message)
        if self.on_error:
            try:
                self.on_error(message)
            except Exception:
                pass
        self._set_state(DictationState.IDLE)
    
    def start_recording(self) -> bool:
        """Start recording audio.
        
        Returns:
            True if recording started.
        """
        if self._state != DictationState.IDLE:
            return False
        
        if self._recorder.start():
            self._set_state(DictationState.RECORDING)
            return True
        
        self._handle_error("Failed to start recording")
        return False
    
    def stop_recording(self) -> bool:
        """Stop recording and process the audio.
        
        This processes synchronously - transcription blocks anyway.
        
        Returns:
            True if processing completed successfully.
        """
        if self._state != DictationState.RECORDING:
            return False
        
        audio = self._recorder.stop()
        
        # Check minimum duration
        if audio is None or len(audio) / self.config.audio.sample_rate < self.config.audio.min_duration:
            logger.warning("Recording too short")
            self._set_state(DictationState.IDLE)
            return False
        
        return self._process_audio(audio)
    
    def _process_audio(self, audio: np.ndarray) -> bool:
        """Process recorded audio: transcribe → enhance → insert.
        
        Returns:
            True if successful.
        """
        self._set_state(DictationState.PROCESSING)
        
        try:
            # Transcribe
            text = self._transcriber.transcribe(audio)
            
            if not text:
                logger.warning("Empty transcription")
                self._set_state(DictationState.IDLE)
                return False
            
            # Enhance if available
            if self.enhancer:
                try:
                    text = self.enhancer(text)
                except Exception as e:
                    logger.warning(f"Enhancement failed: {e}")
            
            # Insert text
            self._inserter.insert(text, prepend_space=self._prepend_space)
            
            # Notify
            if self.on_text:
                try:
                    self.on_text(text)
                except Exception as e:
                    logger.error(f"Text callback error: {e}")
            
            self._set_state(DictationState.IDLE)
            return True
            
        except Exception as e:
            self._handle_error(f"Processing failed: {e}")
            return False
    
    def cancel_recording(self) -> None:
        """Cancel current recording."""
        if self._state == DictationState.RECORDING:
            self._recorder.cancel()
            self._set_state(DictationState.IDLE)
    
    def _toggle_recording(self) -> None:
        """Toggle recording on/off (for toggle mode shortcuts)."""
        if self._state == DictationState.IDLE:
            self.start_recording()
        elif self._state == DictationState.RECORDING:
            self.stop_recording()
    
    def _setup_shortcuts(self) -> None:
        """Configure keyboard shortcuts from config."""
        if self.config.shortcuts.hold_to_dictate:
            self._shortcuts.register(
                self.config.shortcuts.hold_to_dictate,
                on_activate=self.start_recording,
                mode=ShortcutMode.HOLD,
                on_deactivate=self.stop_recording,
            )
        
        if self.config.shortcuts.toggle_dictation:
            self._shortcuts.register(
                self.config.shortcuts.toggle_dictation,
                on_activate=self._toggle_recording,
                mode=ShortcutMode.TOGGLE,
            )
    
    def start(self) -> bool:
        """Start the dictation service.
        
        Pre-loads the Whisper model and starts listening for shortcuts.
        
        Returns:
            True if started successfully.
        """
        # Pre-load model
        logger.info("Loading Whisper model...")
        _ = self._transcriber.model
        
        # Setup shortcuts
        self._setup_shortcuts()
        
        if not self._shortcuts.start():
            self._handle_error("Failed to start keyboard listener")
            return False
        
        logger.info("Dictation service started")
        return True
    
    def stop(self) -> None:
        """Stop the dictation service."""
        if self._state == DictationState.RECORDING:
            self.cancel_recording()
        
        self._shortcuts.stop()
        self._transcriber.unload()
        
        logger.info("Dictation service stopped")
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        self.stop()
        return False

"""Main dictation controller orchestrating all components."""

import logging
import os
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from whossper.audio.recorder import AudioRecorder
from whossper.transcription.whisper_transcriber import WhisperTranscriber
from whossper.input.text_inserter import TextInserter
from whossper.input.keyboard_listener import KeyboardListener, ShortcutMode
from whossper.enhancement.openai_enhancer import TextEnhancer, create_enhancer_from_config
from whossper.config.schema import WhossperConfig
from whossper.permissions.mac_permissions import PermissionsManager, PermissionStatus


logger = logging.getLogger(__name__)


class DictationState(str, Enum):
    """Current state of the dictation system."""
    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"
    ENHANCING = "enhancing"
    INSERTING = "inserting"
    ERROR = "error"


class DictationController:
    """Orchestrates audio recording, transcription, and text insertion.
    
    This is the main controller that ties together all components
    to provide the dictation functionality.
    """
    
    def __init__(
        self,
        config: WhossperConfig,
        on_state_change: Optional[Callable[[DictationState], None]] = None,
        on_transcription: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        """Initialize dictation controller.
        
        Args:
            config: Application configuration.
            on_state_change: Callback when state changes.
            on_transcription: Callback when transcription is complete.
            on_error: Callback when an error occurs.
        """
        self.config = config
        self.on_state_change = on_state_change
        self.on_transcription = on_transcription
        self.on_error = on_error
        
        self._state = DictationState.IDLE
        self._lock = threading.Lock()
        
        # Ensure tmp directory exists
        self._tmp_dir = Path(config.tmp_dir)
        self._tmp_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components (lazy loading for expensive ones)
        self._audio_recorder: Optional[AudioRecorder] = None
        self._transcriber: Optional[WhisperTranscriber] = None
        self._text_inserter: Optional[TextInserter] = None
        self._keyboard_listener: Optional[KeyboardListener] = None
        self._text_enhancer: Optional[TextEnhancer] = None
        self._permissions_manager = PermissionsManager()
        
        # Thread for processing
        self._processing_thread: Optional[threading.Thread] = None
        
        logger.info("DictationController initialized")
    
    @property
    def state(self) -> DictationState:
        """Get current dictation state."""
        return self._state
    
    def _set_state(self, new_state: DictationState) -> None:
        """Set state and notify callback."""
        with self._lock:
            if self._state != new_state:
                self._state = new_state
                logger.debug(f"State changed to: {new_state.value}")
                if self.on_state_change:
                    try:
                        self.on_state_change(new_state)
                    except Exception as e:
                        logger.error(f"State change callback error: {e}")
    
    def _get_audio_recorder(self) -> AudioRecorder:
        """Get or create audio recorder."""
        if self._audio_recorder is None:
            self._audio_recorder = AudioRecorder(
                sample_rate=self.config.audio.sample_rate,
                channels=self.config.audio.channels,
                chunk_size=self.config.audio.chunk_size,
                tmp_dir=str(self._tmp_dir),
            )
        return self._audio_recorder
    
    def _get_transcriber(self) -> WhisperTranscriber:
        """Get or create transcriber."""
        if self._transcriber is None:
            self._transcriber = WhisperTranscriber(
                model_size=self.config.whisper.model_size,
                language=self.config.whisper.language,
                device=self.config.whisper.device,
                model_cache_dir=self.config.whisper.model_cache_dir,
            )
        return self._transcriber
    
    def _get_text_inserter(self) -> TextInserter:
        """Get or create text inserter."""
        if self._text_inserter is None:
            self._text_inserter = TextInserter()
        return self._text_inserter
    
    def _get_keyboard_listener(self) -> KeyboardListener:
        """Get or create keyboard listener."""
        if self._keyboard_listener is None:
            self._keyboard_listener = KeyboardListener()
        return self._keyboard_listener
    
    def _get_text_enhancer(self) -> Optional[TextEnhancer]:
        """Get or create text enhancer if enabled."""
        if self._text_enhancer is None and self.config.enhancement.enabled:
            self._text_enhancer = create_enhancer_from_config(
                api_key=self.config.enhancement.api_key,
                api_key_helper=self.config.enhancement.api_key_helper,
                api_key_env_var=self.config.enhancement.api_key_env_var,
                api_base_url=self.config.enhancement.api_base_url,
                model=self.config.enhancement.model,
                system_prompt_file=self.config.enhancement.system_prompt_file,
                custom_system_prompt=self.config.enhancement.custom_system_prompt,
            )
        return self._text_enhancer
    
    def check_permissions(self) -> dict[str, PermissionStatus]:
        """Check all required permissions.
        
        Returns:
            Dict of permission statuses.
        """
        return self._permissions_manager.check_all_permissions()
    
    def start_recording(self) -> bool:
        """Start audio recording.
        
        Returns:
            True if recording started successfully.
        """
        if self._state != DictationState.IDLE:
            logger.warning(f"Cannot start recording in state: {self._state}")
            return False
        
        recorder = self._get_audio_recorder()
        
        if recorder.start_recording():
            self._set_state(DictationState.RECORDING)
            logger.info("Recording started")
            return True
        else:
            self._handle_error("Failed to start recording")
            return False
    
    def stop_recording(self) -> bool:
        """Stop recording and process the audio.
        
        Returns:
            True if recording was stopped.
        """
        if self._state != DictationState.RECORDING:
            logger.warning(f"Cannot stop recording in state: {self._state}")
            return False
        
        recorder = self._get_audio_recorder()
        
        try:
            audio_file = recorder.stop_recording(
                min_duration=self.config.audio.min_recording_duration
            )
            
            if audio_file:
                # Process in background thread with exception handling
                def thread_wrapper():
                    """Wrapper to catch any unhandled exceptions in thread."""
                    import sys
                    import traceback
                    try:
                        self._process_audio(audio_file)
                    except Exception as e:
                        print(f"FATAL: Unhandled exception in processing thread: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
                        traceback.print_exc(file=sys.stderr)
                        sys.stderr.flush()
                
                self._processing_thread = threading.Thread(
                    target=thread_wrapper,
                    daemon=True
                )
                self._processing_thread.start()
                return True
            else:
                self._set_state(DictationState.IDLE)
                return False
                
        except ValueError as e:
            logger.warning(f"Recording too short: {e}")
            self._set_state(DictationState.IDLE)
            return False
        except Exception as e:
            self._handle_error(f"Failed to stop recording: {e}")
            return False
    
    def wait_for_processing(self, timeout: Optional[float] = None) -> bool:
        """Wait for background processing to complete.
        
        Args:
            timeout: Maximum time to wait in seconds. None for no timeout.
            
        Returns:
            True if processing completed, False if still running or timeout.
        """
        if self._processing_thread is not None:
            self._processing_thread.join(timeout=timeout)
            return not self._processing_thread.is_alive()
        return True
    
    def cancel_recording(self) -> None:
        """Cancel current recording without processing."""
        if self._state == DictationState.RECORDING:
            recorder = self._get_audio_recorder()
            recorder.cancel_recording()
            self._set_state(DictationState.IDLE)
            logger.info("Recording cancelled")
    
    def _process_audio(self, audio_file: str) -> None:
        """Process recorded audio file.
        
        Args:
            audio_file: Path to recorded audio file.
        """
        import sys
        import traceback
        
        logger.debug(f"_process_audio() started for: {audio_file}")
        
        try:
            # Transcribe
            self._set_state(DictationState.TRANSCRIBING)
            logger.debug(f"Starting transcription of: {audio_file}")
            
            logger.debug("Getting transcriber...")
            transcriber = self._get_transcriber()
            logger.debug(f"Transcriber obtained: {transcriber}")
            
            logger.debug("Calling transcribe_to_text()...")
            text = transcriber.transcribe_to_text(audio_file)
            logger.debug(f"transcribe_to_text() returned: '{text}'")
            
            if not text:
                logger.warning("Empty transcription")
                self._set_state(DictationState.IDLE)
                return
            
            logger.info(f"Transcribed: {text[:100]}...")
            
            # Enhance if enabled
            enhancer = self._get_text_enhancer()
            if enhancer:
                self._set_state(DictationState.ENHANCING)
                logger.debug("Starting text enhancement")
                try:
                    text = enhancer.enhance(text)
                    logger.info(f"Enhanced: {text[:100]}...")
                except Exception as e:
                    logger.warning(f"Enhancement failed, using raw transcription: {e}", exc_info=True)
            
            # Insert text
            self._set_state(DictationState.INSERTING)
            logger.debug(f"Inserting text: '{text}'")
            
            logger.debug("Getting text inserter...")
            inserter = self._get_text_inserter()
            logger.debug(f"Text inserter obtained: {inserter}")
            
            logger.debug("Calling insert_text_with_fallback()...")
            try:
                inserter.insert_text_with_fallback(text)
                logger.debug("Text insertion complete")
            except Exception as e:
                logger.exception(f"Text insertion failed: {e}")
                raise
            
            # Notify callback
            if self.on_transcription:
                try:
                    logger.debug("Calling on_transcription callback...")
                    self.on_transcription(text)
                    logger.debug("on_transcription callback complete")
                except Exception as e:
                    logger.error(f"Transcription callback error: {e}", exc_info=True)
            
            logger.debug("_process_audio() completed successfully")
            
        except Exception as e:
            logger.error(f"Processing failed with exception: {type(e).__name__}: {e}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            # Also print to stderr in case logging is broken
            print(f"CRITICAL ERROR in _process_audio: {type(e).__name__}: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            self._handle_error(f"Processing failed: {e}")
        finally:
            logger.debug("_process_audio() finally block")
            # Clean up audio file
            try:
                os.unlink(audio_file)
                logger.debug(f"Cleaned up: {audio_file}")
            except Exception as e:
                logger.warning(f"Failed to clean up audio file: {e}")
            
            self._set_state(DictationState.IDLE)
            logger.debug("_process_audio() exiting")
    
    def _handle_error(self, message: str) -> None:
        """Handle error condition."""
        logger.error(message)
        self._set_state(DictationState.ERROR)
        
        if self.on_error:
            try:
                self.on_error(message)
            except Exception as e:
                logger.error(f"Error callback failed: {e}")
        
        # Return to idle after brief delay
        time.sleep(0.5)
        self._set_state(DictationState.IDLE)
    
    def setup_shortcuts(self) -> bool:
        """Set up keyboard shortcuts from configuration.
        
        Returns:
            True if shortcuts were registered.
        """
        listener = self._get_keyboard_listener()
        
        # Hold-to-dictate shortcut
        if self.config.shortcuts.hold_to_dictate:
            listener.register_shortcut(
                self.config.shortcuts.hold_to_dictate,
                callback=self.start_recording,
                mode=ShortcutMode.HOLD,
                on_release=self.stop_recording,
            )
            logger.info(f"Registered hold-to-dictate: {self.config.shortcuts.hold_to_dictate}")
        
        # Toggle dictation shortcut
        if self.config.shortcuts.toggle_dictation:
            listener.register_shortcut(
                self.config.shortcuts.toggle_dictation,
                callback=self._toggle_dictation,
                mode=ShortcutMode.TOGGLE,
            )
            logger.info(f"Registered toggle-dictation: {self.config.shortcuts.toggle_dictation}")
        
        return True
    
    def _toggle_dictation(self) -> None:
        """Toggle dictation on/off for toggle mode."""
        if self._state == DictationState.IDLE:
            self.start_recording()
        elif self._state == DictationState.RECORDING:
            self.stop_recording()
    
    def start(self) -> bool:
        """Start the dictation service with keyboard shortcuts.
        
        Returns:
            True if started successfully.
        """
        # Check permissions
        perms = self.check_permissions()
        if not self._permissions_manager.all_permissions_granted():
            logger.warning("Not all permissions granted")
            logger.info(self._permissions_manager.get_permission_instructions())
        
        # Pre-load the Whisper model
        logger.info("Pre-loading Whisper model...")
        self._get_transcriber()
        
        # Setup shortcuts
        self.setup_shortcuts()
        
        # Start listening
        listener = self._get_keyboard_listener()
        if listener.start():
            logger.info("Dictation service started")
            return True
        else:
            self._handle_error("Failed to start keyboard listener")
            return False
    
    def stop(self) -> None:
        """Stop the dictation service."""
        # Cancel any ongoing recording
        if self._state == DictationState.RECORDING:
            self.cancel_recording()
        
        # Stop keyboard listener
        if self._keyboard_listener:
            self._keyboard_listener.stop()
        
        # Clean up resources
        if self._audio_recorder:
            self._audio_recorder.cleanup()
        
        if self._transcriber:
            self._transcriber.unload_model()
        
        logger.info("Dictation service stopped")
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False
    
    def run_forever(self) -> None:
        """Run the dictation service until interrupted.
        
        This blocks the main thread and handles keyboard shortcuts.
        """
        if not self.start():
            raise RuntimeError("Failed to start dictation service")
        
        try:
            logger.info("Dictation service running. Press Ctrl+C to stop.")
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.stop()


"""Transcription module using Whisper."""

from .whisper_transcriber import WhisperTranscriber, get_model_info

__all__ = ["WhisperTranscriber", "get_model_info"]

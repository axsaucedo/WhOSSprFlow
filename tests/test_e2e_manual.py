#!/usr/bin/env python3
"""Manual End-to-End Tests for WhOSSpr Flow.

These tests require user interaction and cannot be automated.
They validate real-world usage scenarios with actual audio input.

Run with: python tests/test_e2e_manual.py
Or: pytest tests/test_e2e_manual.py -v -s --manual

Each test will prompt you for input and verify results.
"""

import os
import sys
import time
import threading
from typing import Optional

import pytest

# Add project root to path
sys.path.insert(0, str(__file__).replace("/tests/test_e2e_manual.py", ""))

from whosspr.config import Config, load_config
from whosspr.recorder import AudioRecorder
from whosspr.transcriber import Transcriber
from whosspr.controller import DictationController, DictationState
from whosspr.permissions import check_all, PermissionStatus


# Skip all tests in this module unless --manual is passed or run directly
_RUN_MANUAL = os.environ.get("WHOSSPR_MANUAL_TESTS") == "1"


def skip_unless_manual():
    """Decorator to skip manual tests unless explicitly enabled."""
    return pytest.mark.skipif(
        not _RUN_MANUAL and "pytest" in sys.modules,
        reason="Manual test: set WHOSSPER_MANUAL_TESTS=1 or run directly with python"
    )


# =============================================================================
# Console Utilities
# =============================================================================

def print_header(text: str) -> None:
    """Print a header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def print_step(step: int, text: str) -> None:
    """Print a step instruction."""
    print(f"  [{step}] {text}")


def prompt_user(question: str, default: str = "y") -> bool:
    """Prompt user for yes/no."""
    suffix = "[Y/n]" if default == "y" else "[y/N]"
    response = input(f"\n  {question} {suffix}: ").strip().lower()
    if not response:
        return default == "y"
    return response in ("y", "yes")


def wait_for_key(message: str = "Press Enter to continue...") -> None:
    """Wait for user to press Enter."""
    input(f"\n  {message}")


# =============================================================================
# Permission Tests
# =============================================================================

@skip_unless_manual()
def test_permissions() -> bool:
    """Test that required permissions are granted.
    
    Returns:
        True if all permissions granted.
    """
    print_header("TEST: Check Permissions")
    
    print("  Checking required macOS permissions...")
    perms = check_all()
    
    all_ok = True
    for name, status in perms.items():
        icon = "✅" if status == PermissionStatus.GRANTED else "❌"
        print(f"  {icon} {name}: {status.value}")
        if status != PermissionStatus.GRANTED:
            all_ok = False
    
    if not all_ok:
        print("\n  ⚠️  Some permissions are missing!")
        print("  Please grant permissions in System Preferences:")
        print("    - Microphone: Security & Privacy → Privacy → Microphone")
        print("    - Accessibility: Security & Privacy → Privacy → Accessibility")
        return False
    
    print("\n  ✅ All permissions granted!")
    return True


# =============================================================================
# Audio Recording Tests
# =============================================================================

@skip_unless_manual()
def test_audio_recording() -> bool:
    """Test audio recording with sounddevice.
    
    Returns:
        True if test passed.
    """
    print_header("TEST: Audio Recording")
    
    print_step(1, "This test will record audio from your microphone")
    print_step(2, "When prompted, say a few words clearly")
    print_step(3, "The test will verify audio was captured")
    
    wait_for_key("Press Enter when ready to start recording (3 seconds)...")
    
    recorder = AudioRecorder()
    
    print("\n  🎤 Recording... Say something!")
    
    if not recorder.start():
        print("  ❌ Failed to start recording")
        return False
    
    # Record for 3 seconds
    for i in range(3, 0, -1):
        print(f"  Recording: {i}s remaining...", end="\r")
        time.sleep(1)
    
    audio = recorder.stop()
    
    if audio is None:
        print("\n  ❌ No audio data captured")
        return False
    
    duration = len(audio) / recorder.sample_rate
    print(f"\n  ✅ Recorded {duration:.2f} seconds of audio")
    print(f"     Samples: {len(audio)}")
    print(f"     Sample rate: {recorder.sample_rate} Hz")
    
    # Check if there's actual audio (not just silence)
    import numpy as np
    rms = np.sqrt(np.mean(audio ** 2))
    
    if rms < 0.001:
        print("  ⚠️  Audio appears to be very quiet or silent")
    else:
        print(f"  Audio level (RMS): {rms:.4f}")
    
    return prompt_user("Did the recording work correctly?")


# =============================================================================
# Transcription Tests
# =============================================================================

@skip_unless_manual()
def test_transcription() -> bool:
    """Test Whisper transcription.
    
    Returns:
        True if test passed.
    """
    print_header("TEST: Audio Transcription")
    
    print_step(1, "This test will record and transcribe your speech")
    print_step(2, "When prompted, say: 'Hello, this is a test'")
    print_step(3, "The transcription will be displayed")
    
    print("\n  ⚠️  Note: First run will download the Whisper model (~150MB)")
    
    wait_for_key("Press Enter when ready to start...")
    
    # Record audio
    recorder = AudioRecorder()
    
    print("\n  🎤 Recording... Say: 'Hello, this is a test'")
    
    if not recorder.start():
        print("  ❌ Failed to start recording")
        return False
    
    for i in range(3, 0, -1):
        print(f"  Recording: {i}s remaining...", end="\r")
        time.sleep(1)
    
    audio = recorder.stop()
    
    if audio is None or len(audio) < 1600:  # Less than 0.1s
        print("\n  ❌ No audio data captured")
        return False
    
    print(f"\n  Recorded {len(audio)/16000:.2f}s")
    
    # Transcribe
    print("  ⏳ Transcribing (loading model if first run)...")
    
    try:
        transcriber = Transcriber()
        text = transcriber.transcribe(audio)
        
        print(f"\n  📝 Transcription: '{text}'")
        
        if not text:
            print("  ⚠️  No text transcribed")
        
        transcriber.unload()
        
    except Exception as e:
        print(f"  ❌ Transcription failed: {e}")
        return False
    
    return prompt_user("Was the transcription correct (or close)?")


# =============================================================================
# Full Dictation Flow Tests
# =============================================================================

@skip_unless_manual()
def test_hold_to_dictate() -> bool:
    """Test hold-to-dictate flow.
    
    Returns:
        True if test passed.
    """
    print_header("TEST: Hold-to-Dictate Flow")
    
    print_step(1, "This tests the complete dictation workflow")
    print_step(2, "Open a text editor (Notes, TextEdit, etc.)")
    print_step(3, "Hold Ctrl+Cmd+1 and say something")
    print_step(4, "Release the keys - text should appear")
    
    print("\n  Default shortcut: Ctrl+Cmd+1 (hold to record)")
    
    wait_for_key("Press Enter when you have a text editor focused...")
    
    config = Config()
    config.shortcuts.hold_to_dictate = "ctrl+cmd+1"
    
    states = []
    texts = []
    errors = []
    
    def on_state(state):
        states.append(state)
        icons = {
            DictationState.IDLE: "⏸️",
            DictationState.RECORDING: "🎤",
            DictationState.PROCESSING: "⏳",
        }
        print(f"\r  State: {icons.get(state, '')} {state.value}     ", end="", flush=True)
    
    def on_text(text):
        texts.append(text)
        print(f"\n  ✅ Transcribed: '{text}'")
    
    def on_error(error):
        errors.append(error)
        print(f"\n  ❌ Error: {error}")
    
    controller = DictationController(
        config,
        on_state=on_state,
        on_text=on_text,
        on_error=on_error,
    )
    
    print("\n  Starting dictation service...")
    print("  Hold Ctrl+Cmd+1 to record, release to transcribe.")
    print("  Press Enter when done testing.\n")
    
    if not controller.start():
        print("  ❌ Failed to start dictation service")
        return False
    
    # Wait for user
    try:
        input("")
    except KeyboardInterrupt:
        pass
    
    controller.stop()
    
    print(f"\n  Test summary:")
    print(f"    State changes: {len(states)}")
    print(f"    Transcriptions: {len(texts)}")
    print(f"    Errors: {len(errors)}")
    
    return prompt_user("Did the hold-to-dictate work correctly?")


@skip_unless_manual()
def test_toggle_dictation() -> bool:
    """Test toggle dictation flow.
    
    Returns:
        True if test passed.
    """
    print_header("TEST: Toggle Dictation Flow")
    
    print_step(1, "Open a text editor (Notes, TextEdit, etc.)")
    print_step(2, "Press Ctrl+Cmd+2 to START recording")
    print_step(3, "Say something")
    print_step(4, "Press Ctrl+Cmd+2 again to STOP and transcribe")
    
    print("\n  Default shortcut: Ctrl+Cmd+2 (toggle)")
    
    wait_for_key("Press Enter when you have a text editor focused...")
    
    config = Config()
    config.shortcuts.hold_to_dictate = ""  # Disable hold
    config.shortcuts.toggle_dictation = "ctrl+cmd+2"
    
    texts = []
    
    def on_state(state):
        icons = {
            DictationState.IDLE: "⏸️",
            DictationState.RECORDING: "🎤",
            DictationState.PROCESSING: "⏳",
        }
        print(f"\r  State: {icons.get(state, '')} {state.value}     ", end="", flush=True)
    
    def on_text(text):
        texts.append(text)
        print(f"\n  ✅ Transcribed: '{text}'")
    
    controller = DictationController(
        config,
        on_state=on_state,
        on_text=on_text,
    )
    
    print("\n  Starting dictation service...")
    print("  Press Ctrl+Cmd+2 to toggle recording on/off.")
    print("  Press Enter when done testing.\n")
    
    if not controller.start():
        print("  ❌ Failed to start dictation service")
        return False
    
    try:
        input("")
    except KeyboardInterrupt:
        pass
    
    controller.stop()
    
    print(f"\n  Transcriptions: {len(texts)}")
    
    return prompt_user("Did the toggle dictation work correctly?")


# =============================================================================
# Main Test Runner
# =============================================================================

def run_all_tests() -> None:
    """Run all manual E2E tests."""
    print_header("WhOSSpr Flow - Manual E2E Tests")
    
    print("  These tests require user interaction.")
    print("  Follow the prompts and provide input when asked.")
    print("  You will need a working microphone and a text editor.")
    
    wait_for_key()
    
    results = {}
    
    # Run tests
    tests = [
        ("Permissions", test_permissions),
        ("Audio Recording", test_audio_recording),
        ("Transcription", test_transcription),
        ("Hold-to-Dictate", test_hold_to_dictate),
        ("Toggle Dictation", test_toggle_dictation),
    ]
    
    for name, test_func in tests:
        try:
            passed = test_func()
            results[name] = "✅ PASSED" if passed else "❌ FAILED"
        except KeyboardInterrupt:
            results[name] = "⏭️ SKIPPED"
            print("\n  Test skipped.")
        except Exception as e:
            results[name] = f"💥 ERROR: {e}"
            print(f"\n  ❌ Test error: {e}")
        
        if name != tests[-1][0]:
            if not prompt_user("Continue to next test?"):
                break
    
    # Summary
    print_header("Test Results Summary")
    
    for name, result in results.items():
        print(f"  {name}: {result}")
    
    passed = sum(1 for r in results.values() if "PASSED" in r)
    total = len(results)
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n  🎉 All tests passed!")
    else:
        print("\n  ⚠️  Some tests failed or were skipped.")


def run_quick_test() -> None:
    """Run a quick recording + transcription test."""
    print_header("WhOSSpr Flow - Quick Test")
    
    if not test_permissions():
        return
    
    if not test_audio_recording():
        return
    
    if not test_transcription():
        return
    
    print("\n  ✅ Quick test complete!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Manual E2E tests for WhOSSpr")
    parser.add_argument("--quick", action="store_true", help="Run quick test only")
    parser.add_argument("--permissions", action="store_true", help="Check permissions only")
    parser.add_argument("--recording", action="store_true", help="Test recording only")
    parser.add_argument("--transcription", action="store_true", help="Test transcription only")
    parser.add_argument("--hold", action="store_true", help="Test hold-to-dictate only")
    parser.add_argument("--toggle", action="store_true", help="Test toggle dictation only")
    
    args = parser.parse_args()
    
    try:
        if args.quick:
            run_quick_test()
        elif args.permissions:
            test_permissions()
        elif args.recording:
            test_audio_recording()
        elif args.transcription:
            test_transcription()
        elif args.hold:
            test_hold_to_dictate()
        elif args.toggle:
            test_toggle_dictation()
        else:
            run_all_tests()
    except KeyboardInterrupt:
        print("\n\n  Tests interrupted by user.")

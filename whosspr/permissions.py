"""macOS permission checks.

Checks for microphone and accessibility permissions.
"""

import subprocess
import sys
from enum import Enum

import sounddevice as sd


class PermissionStatus(str, Enum):
    """Permission status."""
    GRANTED = "granted"
    DENIED = "denied"
    UNKNOWN = "unknown"


def check_microphone() -> PermissionStatus:
    """Check if microphone permission is granted."""
    if sys.platform != "darwin":
        return PermissionStatus.GRANTED
    
    try:
        with sd.InputStream(channels=1, samplerate=16000):
            pass
        return PermissionStatus.GRANTED
    except Exception:
        return PermissionStatus.DENIED


def check_accessibility() -> PermissionStatus:
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


def check_all() -> dict[str, PermissionStatus]:
    """Check all required permissions.
    
    Returns:
        Dict mapping permission name to status.
    """
    return {
        "microphone": check_microphone(),
        "accessibility": check_accessibility(),
    }

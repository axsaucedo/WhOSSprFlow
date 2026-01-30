"""macOS permissions manager."""

import logging
import subprocess
import sys
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class PermissionStatus(str, Enum):
    """Permission status."""
    GRANTED = "granted"
    DENIED = "denied"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class PermissionsManager:
    """Manages macOS permissions for microphone and accessibility."""
    
    def __init__(self):
        """Initialize permissions manager."""
        self._is_macos = sys.platform == "darwin"
    
    @property
    def is_macos(self) -> bool:
        """Check if running on macOS."""
        return self._is_macos
    
    def check_microphone_permission(self) -> PermissionStatus:
        """Check microphone access permission.
        
        Returns:
            PermissionStatus indicating current state.
        """
        if not self._is_macos:
            return PermissionStatus.NOT_APPLICABLE
        
        try:
            # Try to import AVFoundation to check permission
            # This will work if we have proper entitlements
            import objc
            from AVFoundation import AVCaptureDevice, AVMediaTypeAudio
            from AVFoundation import (
                AVAuthorizationStatusAuthorized,
                AVAuthorizationStatusDenied,
                AVAuthorizationStatusNotDetermined,
            )
            
            status = AVCaptureDevice.authorizationStatusForMediaType_(AVMediaTypeAudio)
            
            if status == AVAuthorizationStatusAuthorized:
                return PermissionStatus.GRANTED
            elif status == AVAuthorizationStatusDenied:
                return PermissionStatus.DENIED
            else:
                return PermissionStatus.UNKNOWN
                
        except ImportError:
            logger.warning("AVFoundation not available, using fallback check")
            return self._check_microphone_fallback()
        except Exception as e:
            logger.error(f"Error checking microphone permission: {e}")
            return PermissionStatus.UNKNOWN
    
    def _check_microphone_fallback(self) -> PermissionStatus:
        """Fallback method to check microphone by trying to use it.
        
        Returns:
            PermissionStatus based on PyAudio test.
        """
        try:
            import pyaudio
            
            audio = pyaudio.PyAudio()
            try:
                # Try to open an input stream
                stream = audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    frames_per_buffer=1024,
                    start=False  # Don't actually start recording
                )
                stream.close()
                return PermissionStatus.GRANTED
            finally:
                audio.terminate()
                
        except Exception as e:
            logger.debug(f"Microphone fallback check failed: {e}")
            return PermissionStatus.DENIED
    
    def check_accessibility_permission(self) -> PermissionStatus:
        """Check accessibility permission for keyboard control.
        
        Returns:
            PermissionStatus indicating current state.
        """
        if not self._is_macos:
            return PermissionStatus.NOT_APPLICABLE
        
        try:
            # Use ApplicationServices to check accessibility
            from ApplicationServices import AXIsProcessTrusted
            
            if AXIsProcessTrusted():
                return PermissionStatus.GRANTED
            else:
                return PermissionStatus.DENIED
                
        except ImportError:
            logger.warning("ApplicationServices not available, using fallback")
            return self._check_accessibility_fallback()
        except Exception as e:
            logger.error(f"Error checking accessibility permission: {e}")
            return PermissionStatus.UNKNOWN
    
    def _check_accessibility_fallback(self) -> PermissionStatus:
        """Fallback method using tccutil.
        
        Returns:
            PermissionStatus.
        """
        try:
            # Check using system_profiler
            result = subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to return ""'],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return PermissionStatus.GRANTED
            else:
                return PermissionStatus.DENIED
                
        except Exception as e:
            logger.debug(f"Accessibility fallback check failed: {e}")
            return PermissionStatus.UNKNOWN
    
    def request_microphone_permission(self) -> bool:
        """Request microphone permission.
        
        This will trigger the system permission dialog.
        
        Returns:
            True if permission was requested (not necessarily granted).
        """
        if not self._is_macos:
            return True
        
        try:
            import pyaudio
            
            # Opening an audio stream triggers the permission request
            audio = pyaudio.PyAudio()
            try:
                stream = audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    frames_per_buffer=1024
                )
                stream.close()
                return True
            finally:
                audio.terminate()
                
        except Exception as e:
            logger.error(f"Failed to request microphone permission: {e}")
            return False
    
    def open_accessibility_settings(self) -> bool:
        """Open System Preferences to Accessibility settings.
        
        Returns:
            True if settings were opened.
        """
        if not self._is_macos:
            logger.warning("Not on macOS, cannot open settings")
            return False
        
        try:
            subprocess.run([
                "open",
                "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
            ], check=True)
            return True
        except Exception as e:
            logger.error(f"Failed to open accessibility settings: {e}")
            return False
    
    def open_microphone_settings(self) -> bool:
        """Open System Preferences to Microphone settings.
        
        Returns:
            True if settings were opened.
        """
        if not self._is_macos:
            logger.warning("Not on macOS, cannot open settings")
            return False
        
        try:
            subprocess.run([
                "open",
                "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"
            ], check=True)
            return True
        except Exception as e:
            logger.error(f"Failed to open microphone settings: {e}")
            return False
    
    def check_all_permissions(self) -> dict[str, PermissionStatus]:
        """Check all required permissions.
        
        Returns:
            Dict mapping permission name to status.
        """
        return {
            "microphone": self.check_microphone_permission(),
            "accessibility": self.check_accessibility_permission(),
        }
    
    def get_permission_instructions(self) -> str:
        """Get human-readable permission instructions.
        
        Returns:
            Instructions string.
        """
        statuses = self.check_all_permissions()
        
        lines = ["WhOSSper Permissions Status:", "=" * 30]
        
        for name, status in statuses.items():
            emoji = {
                PermissionStatus.GRANTED: "✅",
                PermissionStatus.DENIED: "❌",
                PermissionStatus.UNKNOWN: "❓",
                PermissionStatus.NOT_APPLICABLE: "➖",
            }.get(status, "❓")
            
            lines.append(f"{emoji} {name.title()}: {status.value}")
        
        # Add instructions for denied permissions
        if statuses.get("microphone") == PermissionStatus.DENIED:
            lines.extend([
                "",
                "To enable Microphone access:",
                "1. Open System Preferences > Security & Privacy > Privacy",
                "2. Select 'Microphone' from the left sidebar",
                "3. Check the box next to your terminal/Python application",
            ])
        
        if statuses.get("accessibility") == PermissionStatus.DENIED:
            lines.extend([
                "",
                "To enable Accessibility access:",
                "1. Open System Preferences > Security & Privacy > Privacy",
                "2. Select 'Accessibility' from the left sidebar",
                "3. Click the lock to make changes",
                "4. Add your terminal/Python application to the list",
            ])
        
        return "\n".join(lines)
    
    def all_permissions_granted(self) -> bool:
        """Check if all required permissions are granted.
        
        Returns:
            True if all permissions are granted.
        """
        statuses = self.check_all_permissions()
        
        for status in statuses.values():
            if status not in (PermissionStatus.GRANTED, PermissionStatus.NOT_APPLICABLE):
                return False
        
        return True


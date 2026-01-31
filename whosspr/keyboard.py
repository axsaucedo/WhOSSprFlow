"""Keyboard shortcut handling.

Global keyboard shortcut detection using pynput.
"""

import logging
from enum import Enum
from typing import Callable, Optional, Set

from pynput import keyboard
from pynput.keyboard import Key, KeyCode


logger = logging.getLogger(__name__)


class ShortcutMode(str, Enum):
    """How the shortcut is activated."""
    HOLD = "hold"      # Press and hold, action on release
    TOGGLE = "toggle"  # Press to toggle on/off


# Map string names to pynput keys
KEY_MAP = {
    "ctrl": Key.ctrl, "control": Key.ctrl,
    "cmd": Key.cmd, "command": Key.cmd,
    "alt": Key.alt, "option": Key.alt,
    "shift": Key.shift,
    "space": Key.space,
    "enter": Key.enter, "return": Key.enter,
    "tab": Key.tab,
    "esc": Key.esc, "escape": Key.esc,
    "f1": Key.f1, "f2": Key.f2, "f3": Key.f3, "f4": Key.f4,
    "f5": Key.f5, "f6": Key.f6, "f7": Key.f7, "f8": Key.f8,
    "f9": Key.f9, "f10": Key.f10, "f11": Key.f11, "f12": Key.f12,
}


def parse_shortcut(shortcut: str) -> frozenset:
    """Parse a shortcut string like 'ctrl+cmd+1' to a set of keys."""
    keys = set()
    for part in shortcut.lower().replace(" ", "").split("+"):
        if part in KEY_MAP:
            keys.add(KEY_MAP[part])
        elif len(part) == 1:
            keys.add(KeyCode.from_char(part))
        else:
            logger.warning(f"Unknown key: {part}")
    return frozenset(keys)


def normalize_key(key) -> Key:
    """Normalize left/right modifiers to generic versions."""
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


class KeyboardShortcuts:
    """Listens for global keyboard shortcuts."""
    
    def __init__(self):
        """Initialize the shortcut handler."""
        self._listener: Optional[keyboard.Listener] = None
        self._pressed: Set = set()
        self._shortcuts: dict = {}
        self._running = False
    
    def register(
        self,
        shortcut: str,
        on_activate: Callable[[], None],
        mode: ShortcutMode = ShortcutMode.TOGGLE,
        on_deactivate: Optional[Callable[[], None]] = None,
    ) -> None:
        """Register a keyboard shortcut.
        
        Args:
            shortcut: Shortcut string (e.g., "ctrl+cmd+1").
            on_activate: Called when shortcut is activated.
            mode: HOLD or TOGGLE.
            on_deactivate: For HOLD mode, called when keys released.
        """
        keys = parse_shortcut(shortcut)
        if not keys:
            logger.error(f"Invalid shortcut: {shortcut}")
            return
        
        self._shortcuts[keys] = {
            "on_activate": on_activate,
            "on_deactivate": on_deactivate,
            "mode": mode,
            "active": False,
        }
        logger.info(f"Registered shortcut: {shortcut} ({mode.value})")
    
    def _on_press(self, key) -> None:
        """Handle key press."""
        norm = normalize_key(key)
        self._pressed.add(key)
        if norm != key:
            self._pressed.add(norm)
        
        for keys, info in self._shortcuts.items():
            if keys.issubset(self._pressed) and not info["active"]:
                info["active"] = True
                try:
                    info["on_activate"]()
                except Exception as e:
                    logger.error(f"Shortcut callback error: {e}")
    
    def _on_release(self, key) -> None:
        """Handle key release."""
        norm = normalize_key(key)
        self._pressed.discard(key)
        self._pressed.discard(norm)
        
        for keys, info in self._shortcuts.items():
            if info["active"] and not keys.issubset(self._pressed):
                info["active"] = False
                if info["mode"] == ShortcutMode.HOLD and info["on_deactivate"]:
                    try:
                        info["on_deactivate"]()
                    except Exception as e:
                        logger.error(f"Deactivate callback error: {e}")
    
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
        """Stop listening for shortcuts."""
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

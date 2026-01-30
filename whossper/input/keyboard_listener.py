"""Keyboard listener for global shortcuts."""

import logging
import threading
import time
from enum import Enum
from typing import Callable, Optional, Set

from pynput import keyboard
from pynput.keyboard import Key, KeyCode


logger = logging.getLogger(__name__)


class ShortcutMode(str, Enum):
    """Shortcut activation mode."""
    HOLD = "hold"      # Active while keys are held
    TOGGLE = "toggle"  # Toggle on/off with each press


class KeyboardListener:
    """Listens for global keyboard shortcuts.
    
    Supports both "hold-to-activate" and "toggle" modes for shortcuts.
    """
    
    # Map string names to pynput keys
    KEY_MAP = {
        # Modifiers
        "ctrl": Key.ctrl,
        "control": Key.ctrl,
        "cmd": Key.cmd,
        "command": Key.cmd,
        "alt": Key.alt,
        "option": Key.alt,
        "shift": Key.shift,
        
        # Special keys
        "space": Key.space,
        "enter": Key.enter,
        "return": Key.enter,
        "tab": Key.tab,
        "escape": Key.esc,
        "esc": Key.esc,
        "backspace": Key.backspace,
        "delete": Key.delete,
        
        # Arrow keys
        "up": Key.up,
        "down": Key.down,
        "left": Key.left,
        "right": Key.right,
        
        # Function keys
        "f1": Key.f1,
        "f2": Key.f2,
        "f3": Key.f3,
        "f4": Key.f4,
        "f5": Key.f5,
        "f6": Key.f6,
        "f7": Key.f7,
        "f8": Key.f8,
        "f9": Key.f9,
        "f10": Key.f10,
        "f11": Key.f11,
        "f12": Key.f12,
    }
    
    def __init__(self):
        """Initialize keyboard listener."""
        self._listener: Optional[keyboard.Listener] = None
        self._pressed_keys: Set = set()
        self._shortcuts: dict = {}
        self._toggle_states: dict = {}
        self._running = False
        self._lock = threading.Lock()
    
    @classmethod
    def parse_shortcut(cls, shortcut_str: str) -> Set:
        """Parse a shortcut string into a set of keys.
        
        Args:
            shortcut_str: Shortcut like "ctrl+shift" or "cmd+alt+d".
            
        Returns:
            Set of pynput key objects.
        """
        keys = set()
        parts = shortcut_str.lower().replace(" ", "").split("+")
        
        for part in parts:
            if part in cls.KEY_MAP:
                keys.add(cls.KEY_MAP[part])
            elif len(part) == 1:
                # Single character
                keys.add(KeyCode.from_char(part))
            else:
                logger.warning(f"Unknown key: {part}")
        
        return keys
    
    def register_shortcut(
        self,
        shortcut: str,
        callback: Callable[[], None],
        mode: ShortcutMode = ShortcutMode.TOGGLE,
        on_release: Optional[Callable[[], None]] = None,
    ) -> None:
        """Register a keyboard shortcut.
        
        Args:
            shortcut: Shortcut string like "ctrl+shift" or "cmd+d".
            callback: Function to call when shortcut is activated.
            mode: HOLD (while pressed) or TOGGLE (each press toggles).
            on_release: For HOLD mode, called when keys are released.
        """
        keys = self.parse_shortcut(shortcut)
        
        if not keys:
            logger.error(f"Could not parse shortcut: {shortcut}")
            return
        
        # Use frozenset for hashability
        key_combo = frozenset(keys)
        
        with self._lock:
            self._shortcuts[key_combo] = {
                "callback": callback,
                "mode": mode,
                "on_release": on_release,
                "shortcut_str": shortcut,
                "active": False,
            }
            if mode == ShortcutMode.TOGGLE:
                self._toggle_states[key_combo] = False
        
        logger.info(f"Registered shortcut: {shortcut} ({mode.value})")
    
    def unregister_shortcut(self, shortcut: str) -> bool:
        """Unregister a keyboard shortcut.
        
        Args:
            shortcut: Shortcut string to unregister.
            
        Returns:
            True if shortcut was found and removed.
        """
        keys = self.parse_shortcut(shortcut)
        key_combo = frozenset(keys)
        
        with self._lock:
            if key_combo in self._shortcuts:
                del self._shortcuts[key_combo]
                if key_combo in self._toggle_states:
                    del self._toggle_states[key_combo]
                logger.info(f"Unregistered shortcut: {shortcut}")
                return True
        
        return False
    
    def _normalize_key(self, key) -> Optional[Key]:
        """Normalize a key to a comparable form.
        
        Args:
            key: pynput key object.
            
        Returns:
            Normalized key.
        """
        # Handle left/right modifiers
        if hasattr(key, 'name'):
            if key in (Key.ctrl_l, Key.ctrl_r):
                return Key.ctrl
            elif key in (Key.alt_l, Key.alt_r):
                return Key.alt
            elif key in (Key.shift_l, Key.shift_r):
                return Key.shift
            elif key in (Key.cmd_l, Key.cmd_r):
                return Key.cmd
        return key
    
    def _on_press(self, key) -> None:
        """Handle key press event."""
        normalized = self._normalize_key(key)
        
        with self._lock:
            self._pressed_keys.add(key)
            if normalized and normalized != key:
                self._pressed_keys.add(normalized)
            
            # Check all shortcuts
            for key_combo, shortcut_info in self._shortcuts.items():
                if self._is_shortcut_pressed(key_combo):
                    mode = shortcut_info["mode"]
                    
                    if mode == ShortcutMode.TOGGLE:
                        # Only trigger on first press
                        if not shortcut_info["active"]:
                            shortcut_info["active"] = True
                            self._toggle_states[key_combo] = not self._toggle_states[key_combo]
                            
                            logger.debug(
                                f"Toggle shortcut: {shortcut_info['shortcut_str']} "
                                f"-> {self._toggle_states[key_combo]}"
                            )
                            
                            try:
                                shortcut_info["callback"]()
                            except Exception as e:
                                logger.error(f"Shortcut callback error: {e}")
                    
                    elif mode == ShortcutMode.HOLD:
                        if not shortcut_info["active"]:
                            shortcut_info["active"] = True
                            
                            logger.debug(f"Hold shortcut activated: {shortcut_info['shortcut_str']}")
                            
                            try:
                                shortcut_info["callback"]()
                            except Exception as e:
                                logger.error(f"Shortcut callback error: {e}")
    
    def _on_release(self, key) -> None:
        """Handle key release event."""
        normalized = self._normalize_key(key)
        
        with self._lock:
            self._pressed_keys.discard(key)
            if normalized and normalized != key:
                self._pressed_keys.discard(normalized)
            
            # Check all shortcuts for release
            for key_combo, shortcut_info in self._shortcuts.items():
                mode = shortcut_info["mode"]
                
                # For toggle mode, mark as inactive when any key released
                if mode == ShortcutMode.TOGGLE and shortcut_info["active"]:
                    if not self._is_shortcut_pressed(key_combo):
                        shortcut_info["active"] = False
                
                # For hold mode, trigger on_release callback
                elif mode == ShortcutMode.HOLD and shortcut_info["active"]:
                    if not self._is_shortcut_pressed(key_combo):
                        shortcut_info["active"] = False
                        
                        logger.debug(f"Hold shortcut released: {shortcut_info['shortcut_str']}")
                        
                        if shortcut_info["on_release"]:
                            try:
                                shortcut_info["on_release"]()
                            except Exception as e:
                                logger.error(f"Release callback error: {e}")
    
    def _is_shortcut_pressed(self, key_combo: frozenset) -> bool:
        """Check if all keys in a shortcut are currently pressed.
        
        Args:
            key_combo: Frozenset of keys.
            
        Returns:
            True if all keys are pressed.
        """
        return key_combo.issubset(self._pressed_keys)
    
    def get_toggle_state(self, shortcut: str) -> bool:
        """Get the current toggle state for a shortcut.
        
        Args:
            shortcut: Shortcut string.
            
        Returns:
            Current toggle state (True/False).
        """
        keys = self.parse_shortcut(shortcut)
        key_combo = frozenset(keys)
        
        with self._lock:
            return self._toggle_states.get(key_combo, False)
    
    def set_toggle_state(self, shortcut: str, state: bool) -> None:
        """Set the toggle state for a shortcut.
        
        Args:
            shortcut: Shortcut string.
            state: New toggle state.
        """
        keys = self.parse_shortcut(shortcut)
        key_combo = frozenset(keys)
        
        with self._lock:
            if key_combo in self._toggle_states:
                self._toggle_states[key_combo] = state
    
    def start(self) -> bool:
        """Start the keyboard listener.
        
        Returns:
            True if started successfully.
        """
        if self._running:
            logger.warning("Listener already running")
            return False
        
        try:
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release
            )
            self._listener.start()
            self._running = True
            
            logger.info("Keyboard listener started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start keyboard listener: {e}")
            return False
    
    def stop(self) -> None:
        """Stop the keyboard listener."""
        if self._listener:
            self._listener.stop()
            self._listener = None
        
        self._running = False
        self._pressed_keys.clear()
        
        logger.info("Keyboard listener stopped")
    
    @property
    def is_running(self) -> bool:
        """Check if listener is running."""
        return self._running
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False


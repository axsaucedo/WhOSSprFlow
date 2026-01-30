"""Text inserter for injecting text into applications."""

import logging
import time
from typing import Optional

import pyperclip
from pynput.keyboard import Key, Controller


logger = logging.getLogger(__name__)


class TextInserter:
    """Inserts text into applications via clipboard and keyboard simulation."""
    
    def __init__(
        self,
        typing_delay: float = 0.01,
        paste_delay: float = 0.1,
    ):
        """Initialize text inserter.
        
        Args:
            typing_delay: Delay between keystrokes when typing directly.
            paste_delay: Delay after pasting to ensure completion.
        """
        self.keyboard = Controller()
        self.typing_delay = typing_delay
        self.paste_delay = paste_delay
    
    def insert_text_via_paste(self, text: str) -> bool:
        """Insert text using clipboard and Cmd+V paste.
        
        This is the preferred method as it's faster and more reliable.
        
        Args:
            text: Text to insert.
            
        Returns:
            True if successful.
        """
        if not text:
            logger.warning("Empty text, nothing to insert")
            return False
        
        try:
            # Store original clipboard content
            original_clipboard = self._get_clipboard_safe()
            
            # Copy text to clipboard
            pyperclip.copy(text)
            logger.debug(f"Copied text to clipboard ({len(text)} chars)")
            
            # Small delay to ensure clipboard is updated
            time.sleep(0.05)
            
            # Simulate Cmd+V (paste)
            with self.keyboard.pressed(Key.cmd):
                self.keyboard.press('v')
                self.keyboard.release('v')
            
            # Wait for paste to complete
            time.sleep(self.paste_delay)
            
            logger.info(f"Inserted {len(text)} chars via paste")
            
            # Optionally restore original clipboard (disabled by default for performance)
            # pyperclip.copy(original_clipboard)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to insert text via paste: {e}")
            return False
    
    def insert_text_via_typing(self, text: str) -> bool:
        """Insert text by simulating keystrokes.
        
        Slower but works in more contexts where paste might fail.
        
        Args:
            text: Text to insert.
            
        Returns:
            True if successful.
        """
        if not text:
            logger.warning("Empty text, nothing to insert")
            return False
        
        try:
            for char in text:
                self.keyboard.type(char)
                time.sleep(self.typing_delay)
            
            logger.info(f"Typed {len(text)} chars")
            return True
            
        except Exception as e:
            logger.error(f"Failed to type text: {e}")
            return False
    
    def insert_text(self, text: str, method: str = "paste") -> bool:
        """Insert text using specified method.
        
        Args:
            text: Text to insert.
            method: "paste" for clipboard, "type" for keystrokes.
            
        Returns:
            True if successful.
        """
        if method == "paste":
            return self.insert_text_via_paste(text)
        elif method == "type":
            return self.insert_text_via_typing(text)
        else:
            logger.error(f"Unknown insertion method: {method}")
            return False
    
    def insert_text_with_fallback(self, text: str) -> bool:
        """Insert text, falling back to typing if paste fails.
        
        Args:
            text: Text to insert.
            
        Returns:
            True if successful.
        """
        if self.insert_text_via_paste(text):
            return True
        
        logger.warning("Paste failed, falling back to typing")
        return self.insert_text_via_typing(text)
    
    def get_selected_text(self) -> str:
        """Get the currently selected text using Cmd+C.
        
        Returns:
            Selected text, or empty string if none.
        """
        try:
            # Store current clipboard content
            original_clipboard = self._get_clipboard_safe()
            
            # Clear clipboard
            pyperclip.copy('')
            
            # Simulate Cmd+C (copy)
            with self.keyboard.pressed(Key.cmd):
                self.keyboard.press('c')
                self.keyboard.release('c')
            
            # Wait for copy to complete
            time.sleep(0.2)
            
            # Get selected text
            selected_text = pyperclip.paste()
            
            # If clipboard is still empty, nothing was selected
            if not selected_text:
                logger.debug("No text selected")
                # Restore original clipboard
                if original_clipboard:
                    pyperclip.copy(original_clipboard)
                return ""
            
            logger.info(f"Got selected text: {len(selected_text)} chars")
            return selected_text
            
        except Exception as e:
            logger.error(f"Failed to get selected text: {e}")
            return ""
    
    def replace_selected_text(self, new_text: str) -> bool:
        """Replace currently selected text with new text.
        
        Args:
            new_text: Text to replace selection with.
            
        Returns:
            True if successful.
        """
        return self.insert_text_via_paste(new_text)
    
    def _get_clipboard_safe(self) -> str:
        """Safely get clipboard content.
        
        Returns:
            Clipboard content or empty string.
        """
        try:
            return pyperclip.paste() or ""
        except Exception:
            return ""
    
    def send_key(self, key: str) -> bool:
        """Send a single key press.
        
        Args:
            key: Key to press (e.g., "enter", "tab", "escape").
            
        Returns:
            True if successful.
        """
        key_map = {
            "enter": Key.enter,
            "return": Key.enter,
            "tab": Key.tab,
            "escape": Key.esc,
            "esc": Key.esc,
            "space": Key.space,
            "backspace": Key.backspace,
            "delete": Key.delete,
            "up": Key.up,
            "down": Key.down,
            "left": Key.left,
            "right": Key.right,
        }
        
        try:
            key_obj = key_map.get(key.lower())
            if key_obj:
                self.keyboard.press(key_obj)
                self.keyboard.release(key_obj)
            else:
                # Assume it's a single character
                self.keyboard.press(key)
                self.keyboard.release(key)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send key '{key}': {e}")
            return False
    
    def send_hotkey(self, *keys: str) -> bool:
        """Send a hotkey combination.
        
        Args:
            *keys: Keys to press together (e.g., "cmd", "shift", "z").
            
        Returns:
            True if successful.
        """
        modifier_map = {
            "cmd": Key.cmd,
            "command": Key.cmd,
            "ctrl": Key.ctrl,
            "control": Key.ctrl,
            "alt": Key.alt,
            "option": Key.alt,
            "shift": Key.shift,
        }
        
        try:
            # Separate modifiers from the final key
            modifiers = []
            final_key = None
            
            for key in keys:
                key_lower = key.lower()
                if key_lower in modifier_map:
                    modifiers.append(modifier_map[key_lower])
                else:
                    final_key = key
            
            if not final_key:
                logger.error("No final key specified for hotkey")
                return False
            
            # Press modifiers
            for mod in modifiers:
                self.keyboard.press(mod)
            
            # Press and release final key
            self.keyboard.press(final_key)
            self.keyboard.release(final_key)
            
            # Release modifiers in reverse order
            for mod in reversed(modifiers):
                self.keyboard.release(mod)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send hotkey: {e}")
            return False


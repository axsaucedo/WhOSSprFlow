"""Text insertion via clipboard paste.

Inserts text into the active application using the clipboard.
"""

import logging
import time

import pyperclip
from pynput.keyboard import Key, Controller


logger = logging.getLogger(__name__)


class TextInserter:
    """Inserts text into applications via clipboard paste (Cmd+V)."""
    
    def __init__(self, paste_delay: float = 0.1):
        """Initialize inserter.
        
        Args:
            paste_delay: Delay after paste to ensure completion.
        """
        self._keyboard = Controller()
        self._paste_delay = paste_delay
    
    def insert(self, text: str, prepend_space: bool = True) -> bool:
        """Insert text at cursor position using Cmd+V.
        
        Args:
            text: Text to insert.
            prepend_space: If True, add leading space before text.
            
        Returns:
            True if successful.
        """
        if not text:
            return False
        
        # Add leading space for natural spacing between dictations
        if prepend_space and not text.startswith((' ', '\n', '\t')):
            text = ' ' + text
        
        try:
            pyperclip.copy(text)
            time.sleep(0.05)
            
            with self._keyboard.pressed(Key.cmd):
                self._keyboard.press('v')
                self._keyboard.release('v')
            
            time.sleep(self._paste_delay)
            logger.info(f"Inserted {len(text)} chars")
            return True
        except Exception as e:
            logger.error(f"Insert failed: {e}")
            return False

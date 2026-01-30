"""Tests for text inserter module."""

import pytest
from unittest.mock import MagicMock, patch, call
from pynput.keyboard import Key

from whossper.input.text_inserter import TextInserter


class TestTextInserterInit:
    """Tests for TextInserter initialization."""
    
    def test_default_initialization(self):
        """Test inserter initializes with defaults."""
        inserter = TextInserter()
        
        assert inserter.typing_delay == 0.01
        assert inserter.paste_delay == 0.1
        assert inserter.keyboard is not None
    
    def test_custom_delays(self):
        """Test inserter with custom delays."""
        inserter = TextInserter(typing_delay=0.05, paste_delay=0.2)
        
        assert inserter.typing_delay == 0.05
        assert inserter.paste_delay == 0.2


class TestTextInserterPaste:
    """Tests for paste-based text insertion."""
    
    @patch('whossper.input.text_inserter.pyperclip')
    @patch('whossper.input.text_inserter.time.sleep')
    def test_insert_via_paste(self, mock_sleep, mock_pyperclip):
        """Test inserting text via paste."""
        mock_pyperclip.paste.return_value = ""
        
        inserter = TextInserter()
        inserter.keyboard = MagicMock()
        
        result = inserter.insert_text_via_paste("Hello World")
        
        assert result is True
        mock_pyperclip.copy.assert_called_with("Hello World")
        inserter.keyboard.pressed.assert_called()
    
    @patch('whossper.input.text_inserter.pyperclip')
    def test_insert_empty_text_returns_false(self, mock_pyperclip):
        """Test inserting empty text returns False."""
        inserter = TextInserter()
        
        result = inserter.insert_text_via_paste("")
        
        assert result is False
        mock_pyperclip.copy.assert_not_called()
    
    @patch('whossper.input.text_inserter.pyperclip')
    def test_insert_none_text_returns_false(self, mock_pyperclip):
        """Test inserting None text returns False."""
        inserter = TextInserter()
        
        result = inserter.insert_text_via_paste(None)
        
        assert result is False


class TestTextInserterTyping:
    """Tests for typing-based text insertion."""
    
    @patch('whossper.input.text_inserter.time.sleep')
    def test_insert_via_typing(self, mock_sleep):
        """Test inserting text via typing."""
        inserter = TextInserter()
        inserter.keyboard = MagicMock()
        
        result = inserter.insert_text_via_typing("Hi")
        
        assert result is True
        # Should type each character
        assert inserter.keyboard.type.call_count == 2
    
    @patch('whossper.input.text_inserter.time.sleep')
    def test_typing_with_delay(self, mock_sleep):
        """Test typing respects delay between characters."""
        inserter = TextInserter(typing_delay=0.05)
        inserter.keyboard = MagicMock()
        
        inserter.insert_text_via_typing("ABC")
        
        # Should sleep between each character
        assert mock_sleep.call_count == 3
        mock_sleep.assert_called_with(0.05)
    
    def test_typing_empty_text_returns_false(self):
        """Test typing empty text returns False."""
        inserter = TextInserter()
        
        result = inserter.insert_text_via_typing("")
        
        assert result is False


class TestTextInserterGeneric:
    """Tests for generic insert_text method."""
    
    @patch('whossper.input.text_inserter.pyperclip')
    @patch('whossper.input.text_inserter.time.sleep')
    def test_insert_text_paste_method(self, mock_sleep, mock_pyperclip):
        """Test insert_text with paste method."""
        mock_pyperclip.paste.return_value = ""
        
        inserter = TextInserter()
        inserter.keyboard = MagicMock()
        
        result = inserter.insert_text("Test", method="paste")
        
        assert result is True
        mock_pyperclip.copy.assert_called_with("Test")
    
    @patch('whossper.input.text_inserter.time.sleep')
    def test_insert_text_type_method(self, mock_sleep):
        """Test insert_text with type method."""
        inserter = TextInserter()
        inserter.keyboard = MagicMock()
        
        result = inserter.insert_text("Test", method="type")
        
        assert result is True
        assert inserter.keyboard.type.call_count == 4
    
    def test_insert_text_unknown_method(self):
        """Test insert_text with unknown method returns False."""
        inserter = TextInserter()
        
        result = inserter.insert_text("Test", method="unknown")
        
        assert result is False


class TestTextInserterFallback:
    """Tests for fallback insertion."""
    
    @patch('whossper.input.text_inserter.pyperclip')
    @patch('whossper.input.text_inserter.time.sleep')
    def test_fallback_uses_paste_first(self, mock_sleep, mock_pyperclip):
        """Test fallback tries paste first."""
        mock_pyperclip.paste.return_value = ""
        
        inserter = TextInserter()
        inserter.keyboard = MagicMock()
        
        result = inserter.insert_text_with_fallback("Test")
        
        assert result is True
        mock_pyperclip.copy.assert_called_with("Test")
    
    @patch('whossper.input.text_inserter.pyperclip')
    @patch('whossper.input.text_inserter.time.sleep')
    def test_fallback_to_typing_on_paste_failure(self, mock_sleep, mock_pyperclip):
        """Test fallback uses typing when paste fails."""
        mock_pyperclip.copy.side_effect = [Exception("Paste failed"), None]
        mock_pyperclip.paste.return_value = ""
        
        inserter = TextInserter()
        inserter.keyboard = MagicMock()
        
        result = inserter.insert_text_with_fallback("Hi")
        
        # Should have tried typing after paste failed
        assert inserter.keyboard.type.call_count == 2


class TestTextInserterSelectedText:
    """Tests for getting selected text."""
    
    @patch('whossper.input.text_inserter.pyperclip')
    @patch('whossper.input.text_inserter.time.sleep')
    def test_get_selected_text(self, mock_sleep, mock_pyperclip):
        """Test getting selected text."""
        mock_pyperclip.paste.side_effect = ["original", "selected text"]
        
        inserter = TextInserter()
        inserter.keyboard = MagicMock()
        
        result = inserter.get_selected_text()
        
        assert result == "selected text"
    
    @patch('whossper.input.text_inserter.pyperclip')
    @patch('whossper.input.text_inserter.time.sleep')
    def test_get_selected_text_empty(self, mock_sleep, mock_pyperclip):
        """Test getting selected text when nothing selected."""
        mock_pyperclip.paste.side_effect = ["original", ""]
        
        inserter = TextInserter()
        inserter.keyboard = MagicMock()
        
        result = inserter.get_selected_text()
        
        assert result == ""


class TestTextInserterKeys:
    """Tests for key and hotkey sending."""
    
    def test_send_key_enter(self):
        """Test sending enter key."""
        inserter = TextInserter()
        inserter.keyboard = MagicMock()
        
        result = inserter.send_key("enter")
        
        assert result is True
        inserter.keyboard.press.assert_called_with(Key.enter)
        inserter.keyboard.release.assert_called_with(Key.enter)
    
    def test_send_key_escape(self):
        """Test sending escape key."""
        inserter = TextInserter()
        inserter.keyboard = MagicMock()
        
        result = inserter.send_key("esc")
        
        assert result is True
        inserter.keyboard.press.assert_called_with(Key.esc)
    
    def test_send_key_character(self):
        """Test sending single character."""
        inserter = TextInserter()
        inserter.keyboard = MagicMock()
        
        result = inserter.send_key("a")
        
        assert result is True
        inserter.keyboard.press.assert_called_with("a")
    
    def test_send_hotkey(self):
        """Test sending hotkey combination."""
        inserter = TextInserter()
        inserter.keyboard = MagicMock()
        
        result = inserter.send_hotkey("cmd", "c")
        
        assert result is True
        # Should press cmd, then c, then release both
        calls = inserter.keyboard.press.call_args_list
        assert len(calls) == 2
    
    def test_send_hotkey_no_final_key(self):
        """Test hotkey with no final key returns False."""
        inserter = TextInserter()
        inserter.keyboard = MagicMock()
        
        result = inserter.send_hotkey("cmd", "shift")
        
        assert result is False
    
    def test_send_hotkey_multiple_modifiers(self):
        """Test hotkey with multiple modifiers."""
        inserter = TextInserter()
        inserter.keyboard = MagicMock()
        
        result = inserter.send_hotkey("cmd", "shift", "z")
        
        assert result is True


class TestTextInserterClipboard:
    """Tests for clipboard operations."""
    
    @patch('whossper.input.text_inserter.pyperclip')
    def test_get_clipboard_safe_success(self, mock_pyperclip):
        """Test safe clipboard access."""
        mock_pyperclip.paste.return_value = "clipboard content"
        
        inserter = TextInserter()
        result = inserter._get_clipboard_safe()
        
        assert result == "clipboard content"
    
    @patch('whossper.input.text_inserter.pyperclip')
    def test_get_clipboard_safe_error(self, mock_pyperclip):
        """Test safe clipboard handles errors."""
        mock_pyperclip.paste.side_effect = Exception("Access denied")
        
        inserter = TextInserter()
        result = inserter._get_clipboard_safe()
        
        assert result == ""
    
    @patch('whossper.input.text_inserter.pyperclip')
    def test_get_clipboard_safe_none(self, mock_pyperclip):
        """Test safe clipboard handles None."""
        mock_pyperclip.paste.return_value = None
        
        inserter = TextInserter()
        result = inserter._get_clipboard_safe()
        
        assert result == ""


class TestTextInserterReplace:
    """Tests for replacing selected text."""
    
    @patch('whossper.input.text_inserter.pyperclip')
    @patch('whossper.input.text_inserter.time.sleep')
    def test_replace_selected_text(self, mock_sleep, mock_pyperclip):
        """Test replacing selected text."""
        mock_pyperclip.paste.return_value = ""
        
        inserter = TextInserter()
        inserter.keyboard = MagicMock()
        
        result = inserter.replace_selected_text("new text")
        
        assert result is True
        mock_pyperclip.copy.assert_called_with("new text")

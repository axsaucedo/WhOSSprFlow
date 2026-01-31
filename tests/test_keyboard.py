"""Tests for whosspr.keyboard module."""

import pytest
from unittest.mock import patch, MagicMock

from whosspr.keyboard import (
    KeyboardShortcuts, ShortcutMode, 
    parse_shortcut, normalize_key, KEY_MAP
)
from pynput.keyboard import Key, KeyCode


class TestParseShortcut:
    """Tests for parse_shortcut function."""
    
    def test_simple_modifier_key(self):
        """Test parsing ctrl+1."""
        keys = parse_shortcut("ctrl+1")
        assert Key.ctrl in keys
        assert KeyCode.from_char("1") in keys
    
    def test_multiple_modifiers(self):
        """Test parsing ctrl+cmd+1."""
        keys = parse_shortcut("ctrl+cmd+1")
        assert Key.ctrl in keys
        assert Key.cmd in keys
        assert KeyCode.from_char("1") in keys
    
    def test_case_insensitive(self):
        """Test case insensitivity."""
        keys = parse_shortcut("CTRL+CMD+1")
        assert Key.ctrl in keys
        assert Key.cmd in keys
    
    def test_aliases(self):
        """Test key aliases."""
        keys = parse_shortcut("control+command+option")
        assert Key.ctrl in keys
        assert Key.cmd in keys
        assert Key.alt in keys
    
    def test_function_keys(self):
        """Test function keys."""
        keys = parse_shortcut("f1")
        assert Key.f1 in keys


class TestNormalizeKey:
    """Tests for normalize_key function."""
    
    def test_left_ctrl(self):
        """Test left ctrl normalizes to ctrl."""
        assert normalize_key(Key.ctrl_l) == Key.ctrl
    
    def test_right_ctrl(self):
        """Test right ctrl normalizes to ctrl."""
        assert normalize_key(Key.ctrl_r) == Key.ctrl
    
    def test_regular_key(self):
        """Test regular key unchanged."""
        key = KeyCode.from_char("a")
        assert normalize_key(key) == key


class TestKeyboardShortcuts:
    """Tests for KeyboardShortcuts class."""
    
    def test_register_shortcut(self):
        """Test registering a shortcut."""
        ks = KeyboardShortcuts()
        callback = MagicMock()
        
        ks.register("ctrl+1", callback)
        
        assert len(ks._shortcuts) == 1
    
    def test_register_hold_mode(self):
        """Test registering hold mode shortcut."""
        ks = KeyboardShortcuts()
        on_activate = MagicMock()
        on_deactivate = MagicMock()
        
        ks.register("ctrl+1", on_activate, ShortcutMode.HOLD, on_deactivate)
        
        keys = frozenset({Key.ctrl, KeyCode.from_char("1")})
        assert ks._shortcuts[keys]["mode"] == ShortcutMode.HOLD
        assert ks._shortcuts[keys]["on_deactivate"] == on_deactivate
    
    @patch("whosspr.keyboard.keyboard.Listener")
    def test_start_success(self, mock_listener_class):
        """Test successful start."""
        mock_listener = MagicMock()
        mock_listener_class.return_value = mock_listener
        
        ks = KeyboardShortcuts()
        result = ks.start()
        
        assert result is True
        assert ks.is_running is True
        mock_listener.start.assert_called_once()
    
    @patch("whosspr.keyboard.keyboard.Listener")
    def test_start_already_running(self, mock_listener_class):
        """Test start when already running."""
        mock_listener = MagicMock()
        mock_listener_class.return_value = mock_listener
        
        ks = KeyboardShortcuts()
        ks.start()
        result = ks.start()
        
        assert result is False
    
    @patch("whosspr.keyboard.keyboard.Listener")
    def test_stop(self, mock_listener_class):
        """Test stopping."""
        mock_listener = MagicMock()
        mock_listener_class.return_value = mock_listener
        
        ks = KeyboardShortcuts()
        ks.start()
        ks.stop()
        
        assert ks.is_running is False
        mock_listener.stop.assert_called_once()
    
    def test_callback_on_shortcut_press(self):
        """Test callback is called when shortcut pressed."""
        ks = KeyboardShortcuts()
        callback = MagicMock()
        
        ks.register("ctrl+1", callback)
        
        # Simulate key presses
        ks._on_press(Key.ctrl)
        ks._on_press(KeyCode.from_char("1"))
        
        callback.assert_called_once()
    
    def test_hold_mode_deactivate_on_release(self):
        """Test hold mode calls deactivate on release."""
        ks = KeyboardShortcuts()
        on_activate = MagicMock()
        on_deactivate = MagicMock()
        
        ks.register("ctrl+1", on_activate, ShortcutMode.HOLD, on_deactivate)
        
        # Press
        ks._on_press(Key.ctrl)
        ks._on_press(KeyCode.from_char("1"))
        assert on_activate.called
        
        # Release
        ks._on_release(Key.ctrl)
        assert on_deactivate.called

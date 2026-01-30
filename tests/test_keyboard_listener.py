"""Tests for keyboard listener module."""

import pytest
import time
from unittest.mock import MagicMock, patch
from pynput.keyboard import Key, KeyCode

from whossper.input.keyboard_listener import KeyboardListener, ShortcutMode


class TestKeyboardListenerInit:
    """Tests for KeyboardListener initialization."""
    
    def test_default_initialization(self):
        """Test listener initializes correctly."""
        listener = KeyboardListener()
        
        assert listener.is_running is False
        assert listener._shortcuts == {}
        assert listener._pressed_keys == set()
    
    def test_no_shortcuts_initially(self):
        """Test no shortcuts registered initially."""
        listener = KeyboardListener()
        assert len(listener._shortcuts) == 0


class TestShortcutParsing:
    """Tests for shortcut string parsing."""
    
    def test_parse_single_modifier(self):
        """Test parsing single modifier."""
        keys = KeyboardListener.parse_shortcut("ctrl")
        
        assert Key.ctrl in keys
        assert len(keys) == 1
    
    def test_parse_multiple_modifiers(self):
        """Test parsing multiple modifiers."""
        keys = KeyboardListener.parse_shortcut("ctrl+shift")
        
        assert Key.ctrl in keys
        assert Key.shift in keys
        assert len(keys) == 2
    
    def test_parse_modifier_with_key(self):
        """Test parsing modifier with character key."""
        keys = KeyboardListener.parse_shortcut("cmd+d")
        
        assert Key.cmd in keys
        # Character key should be KeyCode
        char_keys = [k for k in keys if isinstance(k, KeyCode)]
        assert len(char_keys) == 1
    
    def test_parse_cmd_alias(self):
        """Test 'command' is alias for 'cmd'."""
        keys = KeyboardListener.parse_shortcut("command+c")
        assert Key.cmd in keys
    
    def test_parse_alt_alias(self):
        """Test 'option' is alias for 'alt'."""
        keys = KeyboardListener.parse_shortcut("option+a")
        assert Key.alt in keys
    
    def test_parse_control_alias(self):
        """Test 'control' is alias for 'ctrl'."""
        keys = KeyboardListener.parse_shortcut("control+x")
        assert Key.ctrl in keys
    
    def test_parse_with_spaces(self):
        """Test parsing handles spaces."""
        keys = KeyboardListener.parse_shortcut("ctrl + shift + a")
        
        assert Key.ctrl in keys
        assert Key.shift in keys
        assert len(keys) == 3
    
    def test_parse_function_key(self):
        """Test parsing function key."""
        keys = KeyboardListener.parse_shortcut("f1")
        assert Key.f1 in keys
    
    def test_parse_special_keys(self):
        """Test parsing special keys."""
        assert Key.space in KeyboardListener.parse_shortcut("space")
        assert Key.enter in KeyboardListener.parse_shortcut("enter")
        assert Key.esc in KeyboardListener.parse_shortcut("escape")
        assert Key.tab in KeyboardListener.parse_shortcut("tab")


class TestShortcutRegistration:
    """Tests for shortcut registration."""
    
    def test_register_toggle_shortcut(self):
        """Test registering a toggle shortcut."""
        listener = KeyboardListener()
        callback = MagicMock()
        
        listener.register_shortcut(
            "ctrl+d",
            callback,
            mode=ShortcutMode.TOGGLE
        )
        
        assert len(listener._shortcuts) == 1
        assert len(listener._toggle_states) == 1
    
    def test_register_hold_shortcut(self):
        """Test registering a hold shortcut."""
        listener = KeyboardListener()
        callback = MagicMock()
        on_release = MagicMock()
        
        listener.register_shortcut(
            "ctrl+shift",
            callback,
            mode=ShortcutMode.HOLD,
            on_release=on_release
        )
        
        assert len(listener._shortcuts) == 1
        # Hold shortcuts don't have toggle state
        assert len(listener._toggle_states) == 0
    
    def test_register_multiple_shortcuts(self):
        """Test registering multiple shortcuts."""
        listener = KeyboardListener()
        
        listener.register_shortcut("ctrl+a", MagicMock())
        listener.register_shortcut("ctrl+b", MagicMock())
        listener.register_shortcut("cmd+d", MagicMock())
        
        assert len(listener._shortcuts) == 3
    
    def test_unregister_shortcut(self):
        """Test unregistering a shortcut."""
        listener = KeyboardListener()
        callback = MagicMock()
        
        listener.register_shortcut("ctrl+d", callback)
        assert len(listener._shortcuts) == 1
        
        result = listener.unregister_shortcut("ctrl+d")
        
        assert result is True
        assert len(listener._shortcuts) == 0
    
    def test_unregister_nonexistent_shortcut(self):
        """Test unregistering nonexistent shortcut returns False."""
        listener = KeyboardListener()
        
        result = listener.unregister_shortcut("ctrl+x")
        
        assert result is False


class TestToggleState:
    """Tests for toggle state management."""
    
    def test_initial_toggle_state_false(self):
        """Test initial toggle state is False."""
        listener = KeyboardListener()
        listener.register_shortcut("ctrl+d", MagicMock())
        
        state = listener.get_toggle_state("ctrl+d")
        
        assert state is False
    
    def test_set_toggle_state(self):
        """Test setting toggle state."""
        listener = KeyboardListener()
        listener.register_shortcut("ctrl+d", MagicMock())
        
        listener.set_toggle_state("ctrl+d", True)
        
        assert listener.get_toggle_state("ctrl+d") is True
    
    def test_get_toggle_state_nonexistent(self):
        """Test getting toggle state for nonexistent shortcut."""
        listener = KeyboardListener()
        
        state = listener.get_toggle_state("ctrl+x")
        
        assert state is False


class TestKeyNormalization:
    """Tests for key normalization."""
    
    def test_normalize_ctrl_l(self):
        """Test normalizing left ctrl."""
        listener = KeyboardListener()
        normalized = listener._normalize_key(Key.ctrl_l)
        
        assert normalized == Key.ctrl
    
    def test_normalize_ctrl_r(self):
        """Test normalizing right ctrl."""
        listener = KeyboardListener()
        normalized = listener._normalize_key(Key.ctrl_r)
        
        assert normalized == Key.ctrl
    
    def test_normalize_shift(self):
        """Test normalizing shift keys."""
        listener = KeyboardListener()
        
        assert listener._normalize_key(Key.shift_l) == Key.shift
        assert listener._normalize_key(Key.shift_r) == Key.shift
    
    def test_normalize_regular_key(self):
        """Test regular keys are not modified."""
        listener = KeyboardListener()
        
        assert listener._normalize_key(Key.space) == Key.space
        assert listener._normalize_key(Key.enter) == Key.enter


class TestKeyPressHandling:
    """Tests for key press event handling."""
    
    def test_toggle_callback_on_press(self):
        """Test toggle callback is called on press."""
        listener = KeyboardListener()
        callback = MagicMock()
        
        listener.register_shortcut("ctrl+d", callback, mode=ShortcutMode.TOGGLE)
        
        # Simulate pressing ctrl
        listener._on_press(Key.ctrl)
        callback.assert_not_called()
        
        # Simulate pressing d while ctrl is held
        listener._on_press(KeyCode.from_char('d'))
        callback.assert_called_once()
    
    def test_hold_callback_on_press(self):
        """Test hold callback is called on press."""
        listener = KeyboardListener()
        callback = MagicMock()
        
        listener.register_shortcut("ctrl+shift", callback, mode=ShortcutMode.HOLD)
        
        # Simulate pressing ctrl
        listener._on_press(Key.ctrl)
        callback.assert_not_called()
        
        # Simulate pressing shift while ctrl is held
        listener._on_press(Key.shift)
        callback.assert_called_once()
    
    def test_hold_release_callback(self):
        """Test hold release callback is called."""
        listener = KeyboardListener()
        callback = MagicMock()
        on_release = MagicMock()
        
        listener.register_shortcut(
            "ctrl+shift",
            callback,
            mode=ShortcutMode.HOLD,
            on_release=on_release
        )
        
        # Press both keys
        listener._on_press(Key.ctrl)
        listener._on_press(Key.shift)
        
        # Release one key
        listener._on_release(Key.shift)
        
        on_release.assert_called_once()
    
    def test_toggle_state_changes(self):
        """Test toggle state changes on each activation."""
        listener = KeyboardListener()
        callback = MagicMock()
        
        listener.register_shortcut("ctrl+d", callback, mode=ShortcutMode.TOGGLE)
        
        assert listener.get_toggle_state("ctrl+d") is False
        
        # First activation
        listener._on_press(Key.ctrl)
        listener._on_press(KeyCode.from_char('d'))
        
        assert listener.get_toggle_state("ctrl+d") is True
        
        # Release keys
        listener._on_release(KeyCode.from_char('d'))
        listener._on_release(Key.ctrl)
        
        # Second activation
        listener._on_press(Key.ctrl)
        listener._on_press(KeyCode.from_char('d'))
        
        assert listener.get_toggle_state("ctrl+d") is False


class TestListenerLifecycle:
    """Tests for listener start/stop."""
    
    @patch('whossper.input.keyboard_listener.keyboard.Listener')
    def test_start_listener(self, mock_listener_class):
        """Test starting the listener."""
        mock_listener = MagicMock()
        mock_listener_class.return_value = mock_listener
        
        listener = KeyboardListener()
        result = listener.start()
        
        assert result is True
        assert listener.is_running is True
        mock_listener.start.assert_called_once()
    
    @patch('whossper.input.keyboard_listener.keyboard.Listener')
    def test_start_already_running(self, mock_listener_class):
        """Test starting when already running returns False."""
        mock_listener = MagicMock()
        mock_listener_class.return_value = mock_listener
        
        listener = KeyboardListener()
        listener.start()
        
        result = listener.start()
        
        assert result is False
    
    @patch('whossper.input.keyboard_listener.keyboard.Listener')
    def test_stop_listener(self, mock_listener_class):
        """Test stopping the listener."""
        mock_listener = MagicMock()
        mock_listener_class.return_value = mock_listener
        
        listener = KeyboardListener()
        listener.start()
        listener.stop()
        
        assert listener.is_running is False
        mock_listener.stop.assert_called_once()
    
    @patch('whossper.input.keyboard_listener.keyboard.Listener')
    def test_context_manager(self, mock_listener_class):
        """Test using listener as context manager."""
        mock_listener = MagicMock()
        mock_listener_class.return_value = mock_listener
        
        with KeyboardListener() as listener:
            assert listener.is_running is True
        
        mock_listener.stop.assert_called_once()


class TestShortcutMode:
    """Tests for ShortcutMode enum."""
    
    def test_hold_mode_value(self):
        """Test HOLD mode value."""
        assert ShortcutMode.HOLD.value == "hold"
    
    def test_toggle_mode_value(self):
        """Test TOGGLE mode value."""
        assert ShortcutMode.TOGGLE.value == "toggle"


class TestCallbackErrorHandling:
    """Tests for callback error handling."""
    
    def test_callback_error_does_not_crash(self):
        """Test callback error doesn't crash listener."""
        listener = KeyboardListener()
        callback = MagicMock(side_effect=Exception("Callback error"))
        
        listener.register_shortcut("ctrl+d", callback, mode=ShortcutMode.TOGGLE)
        
        # This should not raise
        listener._on_press(Key.ctrl)
        listener._on_press(KeyCode.from_char('d'))
        
        callback.assert_called_once()
    
    def test_release_callback_error_does_not_crash(self):
        """Test release callback error doesn't crash listener."""
        listener = KeyboardListener()
        on_release = MagicMock(side_effect=Exception("Release error"))
        
        listener.register_shortcut(
            "ctrl+shift",
            MagicMock(),
            mode=ShortcutMode.HOLD,
            on_release=on_release
        )
        
        listener._on_press(Key.ctrl)
        listener._on_press(Key.shift)
        
        # This should not raise
        listener._on_release(Key.shift)
        
        on_release.assert_called_once()

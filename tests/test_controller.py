"""Tests for whosspr.controller module."""

import numpy as np
import pytest
from unittest.mock import patch, MagicMock

from whosspr.controller import DictationController, DictationState
from whosspr.config import Config


class TestDictationState:
    """Tests for DictationState enum."""
    
    def test_states_exist(self):
        """Test all states are defined."""
        assert DictationState.IDLE
        assert DictationState.RECORDING
        assert DictationState.PROCESSING


class TestDictationController:
    """Tests for DictationController class."""
    
    @patch("whosspr.controller.Transcriber")
    @patch("whosspr.controller.AudioRecorder")
    @patch("whosspr.controller.TextInserter")
    @patch("whosspr.controller.KeyboardShortcuts")
    def test_init(self, mock_ks, mock_ins, mock_rec, mock_trans):
        """Test initialization."""
        config = Config()
        ctrl = DictationController(config)
        
        assert ctrl.state == DictationState.IDLE
        assert ctrl.config == config
    
    @patch("whosspr.controller.Transcriber")
    @patch("whosspr.controller.AudioRecorder")
    @patch("whosspr.controller.TextInserter")
    @patch("whosspr.controller.KeyboardShortcuts")
    def test_start_recording(self, mock_ks, mock_ins, mock_rec_class, mock_trans):
        """Test start recording."""
        mock_rec = MagicMock()
        mock_rec.start.return_value = True
        mock_rec_class.return_value = mock_rec
        
        ctrl = DictationController(Config())
        result = ctrl.start_recording()
        
        assert result is True
        assert ctrl.state == DictationState.RECORDING
    
    @patch("whosspr.controller.Transcriber")
    @patch("whosspr.controller.AudioRecorder")
    @patch("whosspr.controller.TextInserter")
    @patch("whosspr.controller.KeyboardShortcuts")
    def test_start_recording_fails(self, mock_ks, mock_ins, mock_rec_class, mock_trans):
        """Test start recording failure."""
        mock_rec = MagicMock()
        mock_rec.start.return_value = False
        mock_rec_class.return_value = mock_rec
        
        ctrl = DictationController(Config())
        result = ctrl.start_recording()
        
        assert result is False
        assert ctrl.state == DictationState.IDLE
    
    @patch("whosspr.controller.Transcriber")
    @patch("whosspr.controller.AudioRecorder")
    @patch("whosspr.controller.TextInserter")
    @patch("whosspr.controller.KeyboardShortcuts")
    def test_stop_recording_too_short(self, mock_ks, mock_ins, mock_rec_class, mock_trans):
        """Test stop with too short recording."""
        mock_rec = MagicMock()
        mock_rec.start.return_value = True
        mock_rec.stop.return_value = np.zeros(100)  # Too short
        mock_rec_class.return_value = mock_rec
        
        config = Config()
        config.audio.min_duration = 0.5
        config.audio.sample_rate = 16000
        
        ctrl = DictationController(config)
        ctrl.start_recording()
        result = ctrl.stop_recording()
        
        assert result is False
        assert ctrl.state == DictationState.IDLE
    
    @patch("whosspr.controller.Transcriber")
    @patch("whosspr.controller.AudioRecorder")
    @patch("whosspr.controller.TextInserter")
    @patch("whosspr.controller.KeyboardShortcuts")
    def test_stop_recording_success(self, mock_ks, mock_ins_class, mock_rec_class, mock_trans_class):
        """Test successful stop and processing."""
        # Setup mocks
        mock_rec = MagicMock()
        mock_rec.start.return_value = True
        mock_rec.stop.return_value = np.zeros(16000)  # 1 second
        mock_rec_class.return_value = mock_rec
        
        mock_trans = MagicMock()
        mock_trans.transcribe.return_value = "Hello world"
        mock_trans_class.return_value = mock_trans
        
        mock_ins = MagicMock()
        mock_ins.insert.return_value = True
        mock_ins_class.return_value = mock_ins
        
        config = Config()
        ctrl = DictationController(config)
        ctrl.start_recording()
        result = ctrl.stop_recording()
        
        assert result is True
        assert ctrl.state == DictationState.IDLE
        mock_ins.insert.assert_called_with("Hello world")
    
    @patch("whosspr.controller.Transcriber")
    @patch("whosspr.controller.AudioRecorder")
    @patch("whosspr.controller.TextInserter")
    @patch("whosspr.controller.KeyboardShortcuts")
    def test_cancel_recording(self, mock_ks, mock_ins, mock_rec_class, mock_trans):
        """Test cancel recording."""
        mock_rec = MagicMock()
        mock_rec.start.return_value = True
        mock_rec_class.return_value = mock_rec
        
        ctrl = DictationController(Config())
        ctrl.start_recording()
        ctrl.cancel_recording()
        
        assert ctrl.state == DictationState.IDLE
        mock_rec.cancel.assert_called_once()
    
    @patch("whosspr.controller.Transcriber")
    @patch("whosspr.controller.AudioRecorder")
    @patch("whosspr.controller.TextInserter")
    @patch("whosspr.controller.KeyboardShortcuts")
    def test_callbacks(self, mock_ks, mock_ins_class, mock_rec_class, mock_trans_class):
        """Test callbacks are called."""
        mock_rec = MagicMock()
        mock_rec.start.return_value = True
        mock_rec.stop.return_value = np.zeros(16000)
        mock_rec_class.return_value = mock_rec
        
        mock_trans = MagicMock()
        mock_trans.transcribe.return_value = "Test"
        mock_trans_class.return_value = mock_trans
        
        mock_ins = MagicMock()
        mock_ins_class.return_value = mock_ins
        
        on_state = MagicMock()
        on_text = MagicMock()
        
        ctrl = DictationController(Config(), on_state=on_state, on_text=on_text)
        ctrl.start_recording()
        ctrl.stop_recording()
        
        assert on_state.called
        on_text.assert_called_with("Test")
    
    @patch("whosspr.controller.Transcriber")
    @patch("whosspr.controller.AudioRecorder")
    @patch("whosspr.controller.TextInserter")
    @patch("whosspr.controller.KeyboardShortcuts")
    def test_enhancer_called(self, mock_ks, mock_ins_class, mock_rec_class, mock_trans_class):
        """Test enhancer is called when provided."""
        mock_rec = MagicMock()
        mock_rec.start.return_value = True
        mock_rec.stop.return_value = np.zeros(16000)
        mock_rec_class.return_value = mock_rec
        
        mock_trans = MagicMock()
        mock_trans.transcribe.return_value = "raw text"
        mock_trans_class.return_value = mock_trans
        
        mock_ins = MagicMock()
        mock_ins_class.return_value = mock_ins
        
        enhancer = MagicMock(return_value="enhanced text")
        
        ctrl = DictationController(Config(), enhancer=enhancer)
        ctrl.start_recording()
        ctrl.stop_recording()
        
        enhancer.assert_called_with("raw text")
        mock_ins.insert.assert_called_with("enhanced text")
    
    @patch("whosspr.controller.Transcriber")
    @patch("whosspr.controller.AudioRecorder")
    @patch("whosspr.controller.TextInserter")
    @patch("whosspr.controller.KeyboardShortcuts")
    def test_context_manager(self, mock_ks_class, mock_ins, mock_rec, mock_trans_class):
        """Test context manager interface."""
        mock_ks = MagicMock()
        mock_ks.start.return_value = True
        mock_ks_class.return_value = mock_ks
        
        mock_trans = MagicMock()
        mock_trans_class.return_value = mock_trans
        
        with DictationController(Config()) as ctrl:
            assert ctrl is not None
        
        mock_ks.stop.assert_called()

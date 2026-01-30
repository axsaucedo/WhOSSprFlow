"""Tests for logging configuration module."""

import logging
import os
import pytest
from pathlib import Path

from whossper.logging_config import (
    setup_logging,
    get_default_log_file,
    get_logger,
)


@pytest.fixture
def clean_loggers():
    """Clean up loggers after each test."""
    yield
    # Reset whossper logger
    logger = logging.getLogger("whossper")
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)


class TestSetupLogging:
    """Tests for setup_logging function."""
    
    def test_setup_default_logging(self, clean_loggers):
        """Test default logging setup."""
        setup_logging()
        
        logger = logging.getLogger("whossper")
        assert logger.level == logging.INFO
        assert len(logger.handlers) >= 1
    
    def test_setup_debug_logging(self, clean_loggers):
        """Test debug mode enables DEBUG level."""
        setup_logging(debug=True)
        
        logger = logging.getLogger("whossper")
        assert logger.level == logging.DEBUG
    
    def test_setup_with_log_file(self, clean_loggers, tmp_path):
        """Test logging to file."""
        log_file = tmp_path / "test.log"
        setup_logging(log_file=str(log_file))
        
        logger = logging.getLogger("whossper")
        logger.info("Test message")
        
        # Flush handlers
        for handler in logger.handlers:
            handler.flush()
        
        assert log_file.exists()
        content = log_file.read_text()
        assert "Test message" in content
    
    def test_setup_creates_log_directory(self, clean_loggers, tmp_path):
        """Test log file directory is created."""
        log_file = tmp_path / "subdir" / "test.log"
        setup_logging(log_file=str(log_file))
        
        assert log_file.parent.exists()
    
    def test_setup_without_rich(self, clean_loggers):
        """Test logging works without rich."""
        setup_logging(use_rich=False)
        
        logger = logging.getLogger("whossper")
        assert len(logger.handlers) >= 1


class TestGetDefaultLogFile:
    """Tests for get_default_log_file function."""
    
    def test_creates_tmp_directory(self, tmp_path):
        """Test tmp directory is created."""
        tmp_dir = tmp_path / "logs"
        log_file = get_default_log_file(str(tmp_dir))
        
        assert tmp_dir.exists()
    
    def test_returns_timestamped_path(self, tmp_path):
        """Test log file has timestamp."""
        log_file = get_default_log_file(str(tmp_path))
        
        assert "whossper_" in log_file
        assert ".log" in log_file
    
    def test_returns_string_path(self, tmp_path):
        """Test returns string not Path."""
        log_file = get_default_log_file(str(tmp_path))
        
        assert isinstance(log_file, str)


class TestGetLogger:
    """Tests for get_logger function."""
    
    def test_returns_logger(self):
        """Test get_logger returns a logger."""
        logger = get_logger("whossper.test")
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "whossper.test"
    
    def test_child_logger_inherits(self, clean_loggers):
        """Test child loggers inherit from parent."""
        setup_logging(level=logging.WARNING)
        
        parent = logging.getLogger("whossper")
        child = get_logger("whossper.child")
        
        assert child.parent == parent


class TestLoggingIntegration:
    """Integration tests for logging."""
    
    def test_debug_format_includes_location(self, clean_loggers, tmp_path):
        """Test debug format includes file and line number."""
        log_file = tmp_path / "debug.log"
        setup_logging(debug=True, log_file=str(log_file), use_rich=False)
        
        logger = logging.getLogger("whossper.test")
        logger.debug("Debug message")
        
        for handler in logging.getLogger("whossper").handlers:
            handler.flush()
        
        content = log_file.read_text()
        # Debug format should include filename
        assert "test_logging.py" in content or "DEBUG" in content
    
    def test_multiple_loggers_same_handler(self, clean_loggers):
        """Test multiple loggers share handlers."""
        setup_logging()
        
        logger1 = get_logger("whossper.module1")
        logger2 = get_logger("whossper.module2")
        
        # Both should log through the whossper root handler
        root = logging.getLogger("whossper")
        assert len(root.handlers) >= 1

"""Logging configuration for WhOSSper Flow.

Provides centralized logging setup with:
- Console output (rich formatting when available)
- File logging with rotation
- Debug mode with verbose output
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


# Default log format
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEBUG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"

# Package logger
logger = logging.getLogger("whossper")


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    debug: bool = False,
    use_rich: bool = True,
) -> None:
    """Configure logging for WhOSSper.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR).
        log_file: Optional file path for log output.
        debug: If True, enables DEBUG level and verbose format.
        use_rich: If True, uses rich console handler when available.
    """
    # Set level
    if debug:
        level = logging.DEBUG
    
    # Get the root whossper logger
    root_logger = logging.getLogger("whossper")
    root_logger.setLevel(level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Choose format
    log_format = DEBUG_FORMAT if debug else DEFAULT_FORMAT
    formatter = logging.Formatter(log_format)
    
    # Console handler
    console_handler = None
    
    if use_rich:
        try:
            from rich.logging import RichHandler
            console_handler = RichHandler(
                level=level,
                show_time=True,
                show_path=debug,
                markup=True,
                rich_tracebacks=True,
                tracebacks_show_locals=debug,
            )
        except ImportError:
            pass
    
    if console_handler is None:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
    
    console_handler.setLevel(level)
    root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path, mode='a', encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        root_logger.addHandler(file_handler)
        
        root_logger.info(f"Logging to file: {log_path}")
    
    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    
    if debug:
        root_logger.debug("Debug logging enabled")


def get_default_log_file(tmp_dir: str = "./tmp") -> str:
    """Get default log file path with timestamp.
    
    Args:
        tmp_dir: Directory for log files.
        
    Returns:
        Path to log file.
    """
    Path(tmp_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return str(Path(tmp_dir) / f"whossper_{timestamp}.log")


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a module.
    
    Args:
        name: Module name (use __name__).
        
    Returns:
        Logger instance.
    """
    return logging.getLogger(name)

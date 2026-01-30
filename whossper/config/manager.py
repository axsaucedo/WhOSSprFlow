"""Configuration manager for loading and saving configuration."""

import json
import logging
from pathlib import Path
from typing import Optional

from .schema import WhossperConfig


logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages WhOSSper configuration loading and saving."""
    
    DEFAULT_CONFIG_PATHS = [
        Path("whossper.json"),
        Path("config.json"),
        Path.home() / ".config" / "whossper" / "config.json",
    ]
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize config manager.
        
        Args:
            config_path: Optional explicit path to config file.
        """
        self.config_path: Optional[Path] = Path(config_path) if config_path else None
        self._config: Optional[WhossperConfig] = None
    
    def _find_config_file(self) -> Optional[Path]:
        """Find the first existing config file from default paths."""
        if self.config_path and self.config_path.exists():
            return self.config_path
        
        for path in self.DEFAULT_CONFIG_PATHS:
            if path.exists():
                return path
        
        return None
    
    def load(self) -> WhossperConfig:
        """Load configuration from file or return defaults.
        
        Returns:
            WhossperConfig instance.
        """
        config_file = self._find_config_file()
        
        if config_file:
            logger.info(f"Loading config from {config_file}")
            try:
                with open(config_file, "r") as f:
                    data = json.load(f)
                self._config = WhossperConfig.model_validate(data)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to load config from {config_file}: {e}")
                logger.info("Using default configuration")
                self._config = WhossperConfig()
        else:
            logger.info("No config file found, using defaults")
            self._config = WhossperConfig()
        
        return self._config
    
    def save(self, config: WhossperConfig, path: Optional[Path] = None) -> Path:
        """Save configuration to file.
        
        Args:
            config: Configuration to save.
            path: Optional path to save to. Uses config_path or default if not provided.
            
        Returns:
            Path where config was saved.
        """
        save_path = path or self.config_path or Path("whossper.json")
        
        # Ensure parent directory exists
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, "w") as f:
            json.dump(config.model_dump(), f, indent=2)
        
        logger.info(f"Saved config to {save_path}")
        return save_path
    
    def get_config(self) -> WhossperConfig:
        """Get current config, loading if necessary.
        
        Returns:
            Current WhossperConfig instance.
        """
        if self._config is None:
            self.load()
        return self._config  # type: ignore
    
    @staticmethod
    def create_default_config_file(path: Path) -> Path:
        """Create a default config file.
        
        Args:
            path: Path to create config file at.
            
        Returns:
            Path to created config file.
        """
        config = WhossperConfig()
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w") as f:
            json.dump(config.model_dump(), f, indent=2)
        
        return path

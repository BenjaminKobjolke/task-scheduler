import os
import configparser
from typing import Optional

class Config:
    """Handle configuration settings for the task scheduler."""
    
    _instance = None
    
    def __new__(cls):
        """Ensure singleton pattern for configuration."""
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize configuration if not already initialized."""
        if self._initialized:
            return
            
        self.config = configparser.ConfigParser()
        self.config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'config.ini'
        )
        
        # Load or create default configuration
        if os.path.exists(self.config_path):
            self.config.read(self.config_path)
        else:
            self._create_default_config()
        
        self._initialized = True
    
    def _create_default_config(self):
        """Create default configuration file."""
        self.config['Logging'] = {
            'level': 'INFO',
            'detailed_args_logging': 'false'
        }
        
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)
    
    def get_logging_level(self) -> str:
        """Get the current logging level."""
        return self.config.get('Logging', 'level', fallback='INFO')
    
    def set_logging_level(self, level: str):
        """
        Set the logging level.
        
        Args:
            level: One of DEBUG, INFO, WARNING, ERROR
        """
        if level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
            raise ValueError("Invalid logging level")
        
        self.config['Logging']['level'] = level
        self._save_config()
    
    def is_detailed_logging_enabled(self) -> bool:
        """Check if detailed argument logging is enabled."""
        return self.config.getboolean('Logging', 'detailed_args_logging', fallback=False)
    
    def set_detailed_logging(self, enabled: bool):
        """
        Enable or disable detailed argument logging.
        
        Args:
            enabled: True to enable detailed logging, False to disable
        """
        self.config['Logging']['detailed_args_logging'] = str(enabled).lower()
        self._save_config()
    
    def _save_config(self):
        """Save current configuration to file."""
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)

import logging
import os
from datetime import datetime
from .config import Config

class Logger:
    """Custom logger for the task scheduler."""
    
    def __init__(self, name: str = "TaskScheduler"):
        """Initialize logger with specified name."""
        self.logger = logging.getLogger(name)
        self.config = Config()
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup logger with current configuration."""
        # Get log level from config
        level_str = self.config.get_logging_level()
        level = getattr(logging, level_str.upper())
        self.logger.setLevel(level)
        
        # Remove any existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # File handler
        log_file = f"logs/scheduler_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def update_config(self):
        """Update logger configuration."""
        self._setup_logger()
    
    def is_detailed_logging_enabled(self) -> bool:
        """Check if detailed argument logging is enabled."""
        return self.config.is_detailed_logging_enabled()
    
    def info(self, message: str):
        """Log info level message."""
        self.logger.info(message)
    
    def error(self, message: str):
        """Log error level message."""
        self.logger.error(message)
    
    def warning(self, message: str):
        """Log warning level message."""
        self.logger.warning(message)
    
    def debug(self, message: str):
        """Log debug level message."""
        self.logger.debug(message)

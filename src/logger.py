import logging
import os
from datetime import datetime

class Logger:
    """Custom logger for the task scheduler."""
    
    def __init__(self, name: str = "TaskScheduler"):
        """Initialize logger with specified name."""
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # File handler
        log_file = f"logs/scheduler_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
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

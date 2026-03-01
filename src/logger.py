import logging
import os
from datetime import datetime
from typing import List, Optional
from .config import Config
from .constants import Paths


def _configure_root_logger(config: Config) -> None:
    """Configure the root logger to control third-party library console output.

    Removes existing handlers from the root logger and sets up appropriate
    handlers based on the console_logging config setting. This prevents
    libraries like APScheduler from outputting to console when disabled.

    Args:
        config: Config instance to read settings from.
    """
    root = logging.getLogger()
    level_str = config.get_logging_level()
    level = getattr(logging, level_str.upper())
    root.setLevel(level)

    # Remove existing handlers (except pytest's LogCaptureHandler)
    for handler in root.handlers[:]:
        if type(handler) is logging.StreamHandler:
            root.removeHandler(handler)

    if config.is_console_logging_enabled():
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        root.addHandler(console_handler)
    else:
        root.addHandler(logging.NullHandler())


class Logger:
    """Custom logger for the task scheduler."""

    _root_logger_configured: bool = False

    def __init__(self, name: str = "TaskScheduler", log_file_prefix: str = ""):
        """Initialize logger with specified name.

        Args:
            name: Logger name for identification in log entries.
            log_file_prefix: File prefix for the log file. Defaults to scheduler prefix.
        """
        self.logger = logging.getLogger(name)
        self.config = Config()
        self._log_file_prefix = log_file_prefix or Paths.LOG_FILE_PREFIX_SCHEDULER
        if not Logger._root_logger_configured:
            _configure_root_logger(self.config)
            Logger._root_logger_configured = True
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
        os.makedirs(Paths.LOGS_DIR, exist_ok=True)

        # File handler
        log_file = f"{Paths.LOGS_DIR}/{self._log_file_prefix}_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)

        # Formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)

        # Add handlers
        self.logger.addHandler(file_handler)

        # Console handler (only when enabled in config)
        if self.config.is_console_logging_enabled():
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
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

    def log_arguments(
        self, arguments: Optional[List[str]], header: Optional[str] = None
    ):
        """Log arguments in a consistent format.

        Args:
            arguments: List of arguments to log, or None
            header: Optional header text for the log block
        """
        if header:
            self.debug(f"=== {header} ===")
        self.debug("Arguments (as stored):")
        if arguments:
            for i, arg in enumerate(arguments):
                self.debug(f"  {i + 1}. [{arg}]")
        else:
            self.debug("  No arguments")
        if header:
            self.debug("=" * (len(header) + 8))

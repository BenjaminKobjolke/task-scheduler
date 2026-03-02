"""CLI output that always writes to both console and log file."""

import logging
import os
from datetime import datetime

from .constants import Paths

_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class CliOutput:
    """Logger for CLI commands that always outputs to console and file.

    Unlike :class:`Logger`, the console handler is present regardless of the
    ``console_logging`` config setting. This ensures one-shot CLI commands
    (``--list``, ``--history``, etc.) always show output in the terminal.
    """

    def __init__(self, logs_dir: str = Paths.LOGS_DIR) -> None:
        self.logger = logging.getLogger("CliOutput")
        self.logger.setLevel(logging.DEBUG)

        # Remove any pre-existing handlers (e.g. from a previous instantiation)
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        formatter = logging.Formatter(_LOG_FORMAT)

        # File handler — always present
        os.makedirs(logs_dir, exist_ok=True)
        log_file = (
            f"{logs_dir}/{Paths.LOG_FILE_PREFIX_SCHEDULER}"
            f"_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Console handler — always present (the whole point of this class)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # Prevent propagation to root logger (avoids duplicate output)
        self.logger.propagate = False

    def info(self, message: str) -> None:
        """Log info level message."""
        self.logger.info(message)

    def error(self, message: str, *, exc_info: bool = False) -> None:
        """Log error level message."""
        self.logger.error(message, exc_info=exc_info)

    def warning(self, message: str) -> None:
        """Log warning level message."""
        self.logger.warning(message)

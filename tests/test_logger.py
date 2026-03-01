"""Tests for logger module."""

import logging
import tempfile

import pytest
from unittest.mock import MagicMock, patch

import src.config as config_module
from src.logger import Logger


@pytest.fixture(autouse=True)
def reset_config_singleton():
    """Reset the Config singleton before each test."""
    config_module.Config._instance = None
    yield
    config_module.Config._instance = None


@pytest.fixture
def temp_logs_dir():
    """Create a temporary directory for log files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir
        # Close all logging handlers to release file locks on Windows
        for name in list(logging.Logger.manager.loggerDict):
            log = logging.getLogger(name)
            for handler in log.handlers[:]:
                handler.close()
                log.removeHandler(handler)


class TestConsoleHandler:
    """Tests for conditional console handler."""

    def test_no_console_handler_when_disabled(self, temp_logs_dir):
        """Console handler should NOT be added when console_logging is false."""
        mock_config = MagicMock(spec=config_module.Config)
        mock_config.get_logging_level.return_value = "INFO"
        mock_config.is_console_logging_enabled.return_value = False

        with patch("src.logger.Config", return_value=mock_config), \
             patch("src.logger.Paths") as mock_paths:
            mock_paths.LOGS_DIR = temp_logs_dir
            mock_paths.LOG_FILE_PREFIX_SCHEDULER = "scheduler"

            logger = Logger("TestLogger")

        handler_types = [type(h) for h in logger.logger.handlers]
        assert logging.StreamHandler not in handler_types
        assert logging.FileHandler in handler_types

    def test_console_handler_when_enabled(self, temp_logs_dir):
        """Console handler SHOULD be added when console_logging is true."""
        mock_config = MagicMock(spec=config_module.Config)
        mock_config.get_logging_level.return_value = "INFO"
        mock_config.is_console_logging_enabled.return_value = True

        with patch("src.logger.Config", return_value=mock_config), \
             patch("src.logger.Paths") as mock_paths:
            mock_paths.LOGS_DIR = temp_logs_dir
            mock_paths.LOG_FILE_PREFIX_SCHEDULER = "scheduler"

            logger = Logger("TestLogger")

        handler_types = [type(h) for h in logger.logger.handlers]
        assert logging.StreamHandler in handler_types
        assert logging.FileHandler in handler_types


class TestBotLogFile:
    """Tests for bot-specific log file."""

    def test_bot_logger_writes_to_bot_file(self, temp_logs_dir):
        """Bot logger should write to logs/bot_YYYYMMDD.log."""
        mock_config = MagicMock(spec=config_module.Config)
        mock_config.get_logging_level.return_value = "INFO"
        mock_config.is_console_logging_enabled.return_value = False

        with patch("src.logger.Config", return_value=mock_config), \
             patch("src.logger.Paths") as mock_paths:
            mock_paths.LOGS_DIR = temp_logs_dir
            mock_paths.LOG_FILE_PREFIX_BOT = "bot"

            logger = Logger("Bot", log_file_prefix="bot")

        # Check that file handler points to bot_ prefixed file
        file_handlers = [
            h for h in logger.logger.handlers
            if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) == 1
        assert "bot_" in file_handlers[0].baseFilename

    def test_default_logger_writes_to_scheduler_file(self, temp_logs_dir):
        """Default logger should write to logs/scheduler_YYYYMMDD.log."""
        mock_config = MagicMock(spec=config_module.Config)
        mock_config.get_logging_level.return_value = "INFO"
        mock_config.is_console_logging_enabled.return_value = False

        with patch("src.logger.Config", return_value=mock_config), \
             patch("src.logger.Paths") as mock_paths:
            mock_paths.LOGS_DIR = temp_logs_dir
            mock_paths.LOG_FILE_PREFIX_SCHEDULER = "scheduler"

            logger = Logger("TestLogger")

        file_handlers = [
            h for h in logger.logger.handlers
            if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) == 1
        assert "scheduler_" in file_handlers[0].baseFilename

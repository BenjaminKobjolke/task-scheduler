"""Tests for logger module."""

import logging
from logging.handlers import RotatingFileHandler

import pytest
from unittest.mock import MagicMock, patch

import src.config as config_module
from src.logger import (
    Logger,
    _SafeRotatingFileHandler,
    _SafeStreamHandler,
)



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

        console_handlers = [
            h for h in logger.logger.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
        ]
        assert len(console_handlers) == 0
        assert any(isinstance(h, RotatingFileHandler) for h in logger.logger.handlers)

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

        console_handlers = [
            h for h in logger.logger.handlers
            if isinstance(h, _SafeStreamHandler)
        ]
        assert len(console_handlers) == 1
        assert any(isinstance(h, RotatingFileHandler) for h in logger.logger.handlers)


class TestRootLoggerSuppression:
    """Tests for root logger third-party console output suppression."""

    @pytest.fixture(autouse=True)
    def reset_root_logger_configured(self):
        """Reset the root logger configured flag before each test."""
        Logger._root_logger_configured = False
        yield
        Logger._root_logger_configured = False
        # Clean up root logger handlers (console handlers only, preserve pytest's)
        root = logging.getLogger()
        for handler in root.handlers[:]:
            if isinstance(handler, logging.StreamHandler) and not isinstance(
                handler, logging.FileHandler
            ):
                handler.close()
                root.removeHandler(handler)

    def test_root_logger_no_stream_handler_when_console_disabled(self, temp_logs_dir):
        """Root logger should have no StreamHandler when console_logging is false."""
        mock_config = MagicMock(spec=config_module.Config)
        mock_config.get_logging_level.return_value = "INFO"
        mock_config.is_console_logging_enabled.return_value = False

        with patch("src.logger.Config", return_value=mock_config), \
             patch("src.logger.Paths") as mock_paths:
            mock_paths.LOGS_DIR = temp_logs_dir
            mock_paths.LOG_FILE_PREFIX_SCHEDULER = "scheduler"

            Logger("TestRootSuppress")

        root = logging.getLogger()
        console_handlers = [
            h for h in root.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
        ]
        assert len(console_handlers) == 0

    def test_root_logger_has_stream_handler_when_console_enabled(self, temp_logs_dir):
        """Root logger should have a StreamHandler when console_logging is true."""
        mock_config = MagicMock(spec=config_module.Config)
        mock_config.get_logging_level.return_value = "INFO"
        mock_config.is_console_logging_enabled.return_value = True

        with patch("src.logger.Config", return_value=mock_config), \
             patch("src.logger.Paths") as mock_paths:
            mock_paths.LOGS_DIR = temp_logs_dir
            mock_paths.LOG_FILE_PREFIX_SCHEDULER = "scheduler"

            Logger("TestRootConsole")

        root = logging.getLogger()
        console_handlers = [
            h for h in root.handlers
            if isinstance(h, _SafeStreamHandler)
        ]
        assert len(console_handlers) >= 1


class TestSafeRotatingFileHandler:
    """Tests for _SafeRotatingFileHandler Windows rotation safety."""

    def test_rotate_swallows_permission_error(self, temp_logs_dir):
        """PermissionError during rotation should be silently caught."""
        import os

        log_file = os.path.join(temp_logs_dir, "test_perm.log")
        handler = _SafeRotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=1, encoding="utf-8"
        )
        with patch.object(
            RotatingFileHandler,
            "rotate",
            side_effect=PermissionError("[WinError 32] file in use"),
        ):
            # Should not raise
            handler.rotate("source.log", "dest.log")
        handler.close()

    def test_rotate_propagates_other_errors(self, temp_logs_dir):
        """Non-PermissionError exceptions should still propagate."""
        import os

        log_file = os.path.join(temp_logs_dir, "test_other.log")
        handler = _SafeRotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=1, encoding="utf-8"
        )
        with patch.object(
            RotatingFileHandler,
            "rotate",
            side_effect=OSError("disk full"),
        ):
            with pytest.raises(OSError, match="disk full"):
                handler.rotate("source.log", "dest.log")
        handler.close()

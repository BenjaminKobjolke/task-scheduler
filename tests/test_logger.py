"""Tests for logger module."""

import logging
import tempfile

import pytest
from unittest.mock import MagicMock, patch

import src.config as config_module
from src.logger import Logger, setup_bot_library_logging


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


class TestRootLoggerSuppression:
    """Tests for root logger third-party console output suppression."""

    @pytest.fixture(autouse=True)
    def reset_root_logger_configured(self):
        """Reset the root logger configured flag before each test."""
        Logger._root_logger_configured = False
        yield
        Logger._root_logger_configured = False
        # Clean up root logger handlers
        root = logging.getLogger()
        for handler in root.handlers[:]:
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
        stream_handlers = [
            h for h in root.handlers
            if type(h) is logging.StreamHandler
        ]
        assert len(stream_handlers) == 0

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
        stream_handlers = [
            h for h in root.handlers
            if type(h) is logging.StreamHandler
        ]
        assert len(stream_handlers) >= 1


class TestErrorExcInfo:
    """Tests for exc_info support in Logger.error()."""

    def test_error_passes_exc_info_when_true(self, temp_logs_dir):
        """Logger.error(msg, exc_info=True) should forward exc_info to underlying logger."""
        mock_config = MagicMock(spec=config_module.Config)
        mock_config.get_logging_level.return_value = "INFO"
        mock_config.is_console_logging_enabled.return_value = False

        with patch("src.logger.Config", return_value=mock_config), \
             patch("src.logger.Paths") as mock_paths:
            mock_paths.LOGS_DIR = temp_logs_dir
            mock_paths.LOG_FILE_PREFIX_SCHEDULER = "scheduler"

            logger = Logger("TestExcInfo")

        with patch.object(logger.logger, "error") as mock_error:
            logger.error("something broke", exc_info=True)
            mock_error.assert_called_once_with("something broke", exc_info=True)

    def test_error_no_exc_info_by_default(self, temp_logs_dir):
        """Logger.error(msg) should default exc_info=False."""
        mock_config = MagicMock(spec=config_module.Config)
        mock_config.get_logging_level.return_value = "INFO"
        mock_config.is_console_logging_enabled.return_value = False

        with patch("src.logger.Config", return_value=mock_config), \
             patch("src.logger.Paths") as mock_paths:
            mock_paths.LOGS_DIR = temp_logs_dir
            mock_paths.LOG_FILE_PREFIX_SCHEDULER = "scheduler"

            logger = Logger("TestExcInfoDefault")

        with patch.object(logger.logger, "error") as mock_error:
            logger.error("simple error")
            mock_error.assert_called_once_with("simple error", exc_info=False)


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


class TestSetupBotLibraryLogging:
    """Tests for setup_bot_library_logging() routing library loggers to bot log file."""

    @pytest.fixture(autouse=True)
    def cleanup_library_loggers(self):
        """Remove handlers added to library loggers after each test."""
        yield
        for name in ("bot_commander", "xmpp_bot"):
            lib_logger = logging.getLogger(name)
            for handler in lib_logger.handlers[:]:
                handler.close()
                lib_logger.removeHandler(handler)

    def test_attaches_file_handler_to_bot_commander(self, temp_logs_dir):
        """setup_bot_library_logging should attach a FileHandler to bot_commander logger."""
        setup_bot_library_logging(temp_logs_dir)

        lib_logger = logging.getLogger("bot_commander")
        file_handlers = [
            h for h in lib_logger.handlers
            if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) == 1
        assert "bot_" in file_handlers[0].baseFilename

    def test_attaches_file_handler_to_xmpp_bot(self, temp_logs_dir):
        """setup_bot_library_logging should attach a FileHandler to xmpp_bot logger."""
        setup_bot_library_logging(temp_logs_dir)

        lib_logger = logging.getLogger("xmpp_bot")
        file_handlers = [
            h for h in lib_logger.handlers
            if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) == 1
        assert "bot_" in file_handlers[0].baseFilename

    def test_child_loggers_inherit_handler(self, temp_logs_dir):
        """Child loggers like bot_commander.adapter should inherit the file handler."""
        setup_bot_library_logging(temp_logs_dir)

        child_logger = logging.getLogger("bot_commander.adapter")
        # Child loggers propagate to parent, so effective handlers include parent's
        assert child_logger.parent is not None
        parent_file_handlers = [
            h for h in child_logger.parent.handlers
            if isinstance(h, logging.FileHandler)
        ]
        assert len(parent_file_handlers) >= 1

    def test_does_not_duplicate_handlers_on_repeat_call(self, temp_logs_dir):
        """Calling setup_bot_library_logging twice should not add duplicate handlers."""
        setup_bot_library_logging(temp_logs_dir)
        setup_bot_library_logging(temp_logs_dir)

        lib_logger = logging.getLogger("bot_commander")
        file_handlers = [
            h for h in lib_logger.handlers
            if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) == 1

"""Tests for Logger Unicode handling — ensures no encoding crashes on Windows."""

import logging

from unittest.mock import patch

import pytest

from src.logger import Logger


@pytest.fixture(autouse=True)
def _reset_root_logger_flag():
    """Reset the root logger configured flag before each test."""
    original = Logger._root_logger_configured
    Logger._root_logger_configured = False
    yield
    Logger._root_logger_configured = original


class TestLoggerUnicode:
    """Logger must not crash on Unicode text (box-drawing, emoji, CJK, etc.)."""

    def test_info_with_box_drawing_characters(self, tmp_path):
        """Logger.info() with Unicode box-drawing chars does not raise."""
        with patch("src.logger.Paths") as mock_paths:
            mock_paths.LOGS_DIR = str(tmp_path)
            mock_paths.LOG_FILE_PREFIX_SCHEDULER = "sched"
            logger = Logger("test_unicode_box")

        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    def test_info_with_emoji_characters(self, tmp_path):
        """Logger.info() with emoji does not raise."""
        with patch("src.logger.Paths") as mock_paths:
            mock_paths.LOGS_DIR = str(tmp_path)
            mock_paths.LOG_FILE_PREFIX_SCHEDULER = "sched"
            logger = Logger("test_unicode_emoji")

        logger.info("Task completed successfully ✅ 🚀")

    def test_info_with_cjk_characters(self, tmp_path):
        """Logger.info() with CJK characters does not raise."""
        with patch("src.logger.Paths") as mock_paths:
            mock_paths.LOGS_DIR = str(tmp_path)
            mock_paths.LOG_FILE_PREFIX_SCHEDULER = "sched"
            logger = Logger("test_unicode_cjk")

        logger.info("任务已完成")


class TestLoggerFileHandlerEncoding:
    """FileHandlers must use UTF-8 encoding."""

    def test_file_handler_uses_utf8(self, tmp_path):
        """The Logger's FileHandler should have encoding='utf-8'."""
        with patch("src.logger.Paths") as mock_paths:
            mock_paths.LOGS_DIR = str(tmp_path)
            mock_paths.LOG_FILE_PREFIX_SCHEDULER = "sched"
            logger = Logger("test_encoding")

        file_handlers = [
            h for h in logger.logger.handlers if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) > 0
        for fh in file_handlers:
            assert fh.encoding == "utf-8"

    def test_file_handler_writes_unicode(self, tmp_path):
        """Unicode text written to log file is preserved correctly."""
        with patch("src.logger.Paths") as mock_paths:
            mock_paths.LOGS_DIR = str(tmp_path)
            mock_paths.LOG_FILE_PREFIX_SCHEDULER = "sched"
            logger = Logger("test_file_unicode")

        msg = "━━━ Results ━━━ ✅"
        logger.info(msg)

        # Flush handlers
        for h in logger.logger.handlers:
            h.flush()

        log_files = list(tmp_path.glob("sched_*.log"))
        assert len(log_files) == 1
        content = log_files[0].read_text(encoding="utf-8")
        assert msg in content

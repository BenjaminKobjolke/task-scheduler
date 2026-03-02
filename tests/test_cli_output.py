"""Tests for the CliOutput class."""

import contextlib
import logging
from typing import Generator

from src.cli_output import CliOutput


@contextlib.contextmanager
def unittest_log_capture(
    target_logger: logging.Logger,
) -> Generator[list[logging.LogRecord], None, None]:
    """Capture log records emitted to *target_logger*."""
    records: list[logging.LogRecord] = []

    class _Handler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = _Handler()
    handler.setLevel(logging.DEBUG)
    target_logger.addHandler(handler)
    try:
        yield records
    finally:
        target_logger.removeHandler(handler)


class TestCliOutputHandlers:
    """Verify CliOutput always has both StreamHandler and FileHandler."""

    def test_stream_handler_always_present(self, tmp_path: object) -> None:
        cli = CliOutput(logs_dir=str(tmp_path))
        handler_types = [type(h) for h in cli.logger.handlers]
        assert logging.StreamHandler in handler_types or any(
            type(h) is logging.StreamHandler for h in cli.logger.handlers
        )

    def test_file_handler_always_present(self, tmp_path: object) -> None:
        cli = CliOutput(logs_dir=str(tmp_path))
        handler_types = [type(h) for h in cli.logger.handlers]
        assert logging.FileHandler in handler_types

    def test_exactly_two_handlers(self, tmp_path: object) -> None:
        cli = CliOutput(logs_dir=str(tmp_path))
        assert len(cli.logger.handlers) == 2


class TestCliOutputMethods:
    """Verify info/error/warning delegate to correct log levels."""

    def test_info_logs_at_info_level(self, tmp_path: object) -> None:
        cli = CliOutput(logs_dir=str(tmp_path))
        with unittest_log_capture(cli.logger) as records:
            cli.info("hello")
        assert len(records) == 1
        assert records[0].levelno == logging.INFO
        assert records[0].getMessage() == "hello"

    def test_error_logs_at_error_level(self, tmp_path: object) -> None:
        cli = CliOutput(logs_dir=str(tmp_path))
        with unittest_log_capture(cli.logger) as records:
            cli.error("boom")
        assert len(records) == 1
        assert records[0].levelno == logging.ERROR
        assert records[0].getMessage() == "boom"

    def test_warning_logs_at_warning_level(self, tmp_path: object) -> None:
        cli = CliOutput(logs_dir=str(tmp_path))
        with unittest_log_capture(cli.logger) as records:
            cli.warning("careful")
        assert len(records) == 1
        assert records[0].levelno == logging.WARNING
        assert records[0].getMessage() == "careful"

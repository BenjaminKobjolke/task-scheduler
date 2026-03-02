"""Tests for bot health monitoring module."""

import threading

import pytest
from unittest.mock import MagicMock

from bot_commander import BotManager

from src.bot_health import BotHealthMonitor
from src.constants import Bot
from src.logger import Logger


@pytest.fixture
def mock_bot_manager() -> MagicMock:
    """Create a mock BotManager with an adapter that has a thread."""
    manager = MagicMock(spec=BotManager)
    manager._adapter = MagicMock()
    manager._adapter._thread = MagicMock(spec=threading.Thread)
    manager._adapter._thread.is_alive.return_value = True
    manager.start.return_value = True
    return manager


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock Logger."""
    return MagicMock(spec=Logger)


@pytest.fixture
def monitor(mock_bot_manager: MagicMock, mock_logger: MagicMock) -> BotHealthMonitor:
    """Create a BotHealthMonitor with mocked dependencies."""
    return BotHealthMonitor(mock_bot_manager, mock_logger)


class TestIsAlive:
    """Tests for BotHealthMonitor.is_alive()."""

    def test_returns_true_when_thread_alive(
        self, monitor: BotHealthMonitor, mock_bot_manager: MagicMock
    ) -> None:
        """is_alive() should return True when the bot thread is alive."""
        mock_bot_manager._adapter._thread.is_alive.return_value = True
        assert monitor.is_alive() is True

    def test_returns_false_when_thread_dead(
        self, monitor: BotHealthMonitor, mock_bot_manager: MagicMock
    ) -> None:
        """is_alive() should return False when the bot thread is dead."""
        mock_bot_manager._adapter._thread.is_alive.return_value = False
        assert monitor.is_alive() is False

    def test_returns_false_when_no_adapter(
        self, monitor: BotHealthMonitor, mock_bot_manager: MagicMock
    ) -> None:
        """is_alive() should return False when adapter is None."""
        mock_bot_manager._adapter = None
        assert monitor.is_alive() is False

    def test_returns_false_when_no_thread(
        self, monitor: BotHealthMonitor, mock_bot_manager: MagicMock
    ) -> None:
        """is_alive() should return False when thread attribute is missing."""
        mock_bot_manager._adapter._thread = None
        assert monitor.is_alive() is False


class TestReconnect:
    """Tests for BotHealthMonitor.reconnect()."""

    def test_calls_shutdown_then_start(
        self, monitor: BotHealthMonitor, mock_bot_manager: MagicMock
    ) -> None:
        """reconnect() should call shutdown() then start()."""
        result = monitor.reconnect()

        mock_bot_manager.shutdown.assert_called_once()
        mock_bot_manager.start.assert_called_once()
        assert result is True

    def test_returns_false_on_start_failure(
        self, monitor: BotHealthMonitor, mock_bot_manager: MagicMock
    ) -> None:
        """reconnect() should return False when start() returns False."""
        mock_bot_manager.start.return_value = False

        result = monitor.reconnect()

        assert result is False

    def test_returns_false_on_exception(
        self,
        monitor: BotHealthMonitor,
        mock_bot_manager: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """reconnect() should return False and log error on exception."""
        mock_bot_manager.shutdown.side_effect = RuntimeError("shutdown failed")

        result = monitor.reconnect()

        assert result is False
        mock_logger.error.assert_called()
        # Verify exc_info=True was passed
        _, kwargs = mock_logger.error.call_args
        assert kwargs.get("exc_info") is True

    def test_increments_attempt_counter(
        self, monitor: BotHealthMonitor, mock_bot_manager: MagicMock
    ) -> None:
        """reconnect() should increment the attempt counter on failure."""
        mock_bot_manager.start.return_value = False
        assert monitor.reconnect_attempts == 0
        monitor.reconnect()
        assert monitor.reconnect_attempts == 1

    def test_resets_attempts_on_success(
        self, monitor: BotHealthMonitor, mock_bot_manager: MagicMock
    ) -> None:
        """reconnect() should reset attempt counter on success."""
        monitor.reconnect_attempts = 3
        mock_bot_manager.start.return_value = True

        monitor.reconnect()

        assert monitor.reconnect_attempts == 0


class TestCheckHealth:
    """Tests for BotHealthMonitor.check_health()."""

    def test_no_action_when_alive(
        self,
        monitor: BotHealthMonitor,
        mock_bot_manager: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """check_health() should do nothing when bot is alive."""
        mock_bot_manager._adapter._thread.is_alive.return_value = True

        monitor.check_health()

        mock_bot_manager.shutdown.assert_not_called()
        mock_bot_manager.start.assert_not_called()

    def test_reconnects_when_dead(
        self,
        monitor: BotHealthMonitor,
        mock_bot_manager: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """check_health() should attempt reconnect when bot is dead."""
        mock_bot_manager._adapter._thread.is_alive.return_value = False

        monitor.check_health()

        mock_logger.warning.assert_called()
        mock_bot_manager.shutdown.assert_called_once()
        mock_bot_manager.start.assert_called_once()

    def test_stops_after_max_attempts(
        self,
        monitor: BotHealthMonitor,
        mock_bot_manager: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """check_health() should stop reconnecting after max attempts."""
        monitor.reconnect_attempts = Bot.MAX_RECONNECT_ATTEMPTS
        mock_bot_manager._adapter._thread.is_alive.return_value = False

        monitor.check_health()

        mock_bot_manager.shutdown.assert_not_called()
        mock_bot_manager.start.assert_not_called()
        mock_logger.error.assert_called()

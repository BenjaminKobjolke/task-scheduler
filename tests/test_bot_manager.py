"""Tests for BotManager lifecycle manager."""
from unittest.mock import MagicMock, patch

import pytest

from src.bot.bot_manager import BotManager
from src.bot.types import BotConfig, BotMessage, BotResponse
from src.config import Config
from src.constants import Bot as BotConstants
from src.scheduler import TaskScheduler


@pytest.fixture()
def mock_scheduler() -> MagicMock:
    """Create a mock TaskScheduler."""
    return MagicMock(spec=TaskScheduler)


@pytest.fixture()
def mock_config() -> MagicMock:
    """Create a mock Config."""
    return MagicMock(spec=Config)


@pytest.fixture()
def bot_config_none() -> BotConfig:
    """BotConfig with type=none."""
    return BotConfig(
        bot_type="none",
        allow_add=True,
        allow_edit=True,
        allow_delete=True,
    )


@pytest.fixture()
def bot_config_telegram() -> BotConfig:
    """BotConfig with type=telegram."""
    return BotConfig(
        bot_type="telegram",
        allow_add=True,
        allow_edit=True,
        allow_delete=True,
    )


@pytest.fixture()
def bot_config_xmpp() -> BotConfig:
    """BotConfig with type=xmpp."""
    return BotConfig(
        bot_type="xmpp",
        allow_add=True,
        allow_edit=True,
        allow_delete=True,
    )


class TestBotManagerStart:
    """Tests for BotManager.start()."""

    def test_start_returns_false_when_type_none(
        self,
        mock_scheduler: MagicMock,
        mock_config: MagicMock,
        bot_config_none: BotConfig,
    ) -> None:
        """When bot type is 'none', start should return False and not create adapter."""
        mock_config.get_bot_type.return_value = BotConstants.TYPE_NONE
        mock_config.get_bot_config.return_value = bot_config_none

        manager = BotManager(mock_scheduler, mock_config)
        result = manager.start()

        assert result is False
        assert manager._adapter is None
        assert manager._processor is None

    @patch("src.bot.adapters.telegram_adapter.TelegramAdapter")
    def test_start_returns_true_when_telegram(
        self,
        mock_telegram_cls: MagicMock,
        mock_scheduler: MagicMock,
        mock_config: MagicMock,
        bot_config_telegram: BotConfig,
    ) -> None:
        """When bot type is 'telegram', start should create TelegramAdapter and return True."""
        mock_config.get_bot_type.return_value = BotConstants.TYPE_TELEGRAM
        mock_config.get_bot_config.return_value = bot_config_telegram

        mock_adapter_instance = MagicMock()
        mock_telegram_cls.return_value = mock_adapter_instance

        manager = BotManager(mock_scheduler, mock_config)
        result = manager.start()

        assert result is True
        assert manager._adapter is mock_adapter_instance
        assert manager._processor is not None
        mock_adapter_instance.set_on_message.assert_called_once()
        mock_adapter_instance.initialize.assert_called_once_with(mock_config)

    @patch("src.bot.adapters.xmpp_adapter.XmppAdapter")
    def test_start_returns_true_when_xmpp(
        self,
        mock_xmpp_cls: MagicMock,
        mock_scheduler: MagicMock,
        mock_config: MagicMock,
        bot_config_xmpp: BotConfig,
    ) -> None:
        """When bot type is 'xmpp', start should create XmppAdapter and return True."""
        mock_config.get_bot_type.return_value = BotConstants.TYPE_XMPP
        mock_config.get_bot_config.return_value = bot_config_xmpp

        mock_adapter_instance = MagicMock()
        mock_xmpp_cls.return_value = mock_adapter_instance

        manager = BotManager(mock_scheduler, mock_config)
        result = manager.start()

        assert result is True
        assert manager._adapter is mock_adapter_instance
        assert manager._processor is not None
        mock_adapter_instance.set_on_message.assert_called_once()
        mock_adapter_instance.initialize.assert_called_once_with(mock_config)

    def test_start_returns_false_for_unknown_type(
        self,
        mock_scheduler: MagicMock,
        mock_config: MagicMock,
    ) -> None:
        """When bot type is unknown, start should return False."""
        mock_config.get_bot_type.return_value = "unknown_type"
        mock_config.get_bot_config.return_value = BotConfig(
            bot_type="none",
            allow_add=True,
            allow_edit=True,
            allow_delete=True,
        )

        manager = BotManager(mock_scheduler, mock_config)
        result = manager.start()

        assert result is False


class TestBotManagerOnMessage:
    """Tests for BotManager._on_message()."""

    @patch("src.bot.adapters.telegram_adapter.TelegramAdapter")
    def test_on_message_processes_and_replies(
        self,
        mock_telegram_cls: MagicMock,
        mock_scheduler: MagicMock,
        mock_config: MagicMock,
        bot_config_telegram: BotConfig,
    ) -> None:
        """When a message arrives, it should be processed and a reply sent."""
        mock_config.get_bot_type.return_value = BotConstants.TYPE_TELEGRAM
        mock_config.get_bot_config.return_value = bot_config_telegram

        mock_adapter_instance = MagicMock()
        mock_telegram_cls.return_value = mock_adapter_instance

        manager = BotManager(mock_scheduler, mock_config)
        manager.start()

        # Mock the processor
        mock_processor = MagicMock()
        mock_processor.process.return_value = BotResponse(text="reply text")
        manager._processor = mock_processor

        message = BotMessage(user_id="user123", text="/help")
        manager._on_message(message)

        mock_processor.process.assert_called_once_with(message)
        mock_adapter_instance.reply.assert_called_once_with("user123", "reply text")

    @patch("src.bot.adapters.telegram_adapter.TelegramAdapter")
    def test_on_message_handles_exception(
        self,
        mock_telegram_cls: MagicMock,
        mock_scheduler: MagicMock,
        mock_config: MagicMock,
        bot_config_telegram: BotConfig,
    ) -> None:
        """When processing raises an exception, it should be caught and logged."""
        mock_config.get_bot_type.return_value = BotConstants.TYPE_TELEGRAM
        mock_config.get_bot_config.return_value = bot_config_telegram

        mock_adapter_instance = MagicMock()
        mock_telegram_cls.return_value = mock_adapter_instance

        manager = BotManager(mock_scheduler, mock_config)
        manager.start()

        # Mock the processor to raise an exception
        mock_processor = MagicMock()
        mock_processor.process.side_effect = RuntimeError("processing failed")
        manager._processor = mock_processor

        message = BotMessage(user_id="user123", text="/help")

        # Should not raise - exception is caught internally
        manager._on_message(message)

        # Reply should NOT be called since the exception occurred
        mock_adapter_instance.reply.assert_not_called()


class TestBotManagerShutdown:
    """Tests for BotManager.shutdown()."""

    @patch("src.bot.adapters.telegram_adapter.TelegramAdapter")
    def test_shutdown_calls_adapter_shutdown(
        self,
        mock_telegram_cls: MagicMock,
        mock_scheduler: MagicMock,
        mock_config: MagicMock,
        bot_config_telegram: BotConfig,
    ) -> None:
        """When adapter exists, shutdown should call adapter.shutdown()."""
        mock_config.get_bot_type.return_value = BotConstants.TYPE_TELEGRAM
        mock_config.get_bot_config.return_value = bot_config_telegram

        mock_adapter_instance = MagicMock()
        mock_telegram_cls.return_value = mock_adapter_instance

        manager = BotManager(mock_scheduler, mock_config)
        manager.start()
        manager.shutdown()

        mock_adapter_instance.shutdown.assert_called_once()

    def test_shutdown_handles_no_adapter(
        self,
        mock_scheduler: MagicMock,
        mock_config: MagicMock,
    ) -> None:
        """When no adapter exists, shutdown should not raise."""
        manager = BotManager(mock_scheduler, mock_config)

        # Should not raise
        manager.shutdown()

    @patch("src.bot.adapters.telegram_adapter.TelegramAdapter")
    def test_shutdown_handles_exception(
        self,
        mock_telegram_cls: MagicMock,
        mock_scheduler: MagicMock,
        mock_config: MagicMock,
        bot_config_telegram: BotConfig,
    ) -> None:
        """When adapter.shutdown() raises, exception should be caught."""
        mock_config.get_bot_type.return_value = BotConstants.TYPE_TELEGRAM
        mock_config.get_bot_config.return_value = bot_config_telegram

        mock_adapter_instance = MagicMock()
        mock_adapter_instance.shutdown.side_effect = RuntimeError("shutdown failed")
        mock_telegram_cls.return_value = mock_adapter_instance

        manager = BotManager(mock_scheduler, mock_config)
        manager.start()

        # Should not raise
        manager.shutdown()

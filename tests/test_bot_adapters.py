"""Tests for bot adapter implementations."""
import asyncio
from abc import ABC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot.types import BotMessage


class TestBotAdapterBase:
    """Tests for BotAdapter abstract base class."""

    def test_cannot_instantiate_directly(self) -> None:
        from src.bot.adapters.base import BotAdapter

        with pytest.raises(TypeError):
            BotAdapter()  # type: ignore[abstract]

    def test_is_abstract_base_class(self) -> None:
        from src.bot.adapters.base import BotAdapter

        assert issubclass(BotAdapter, ABC)

    def test_set_on_message_stores_callback(self) -> None:
        from src.bot.adapters.base import BotAdapter

        class ConcreteAdapter(BotAdapter):
            def initialize(self, config: object) -> None:
                pass

            def reply(self, user_id: str, text: str) -> None:
                pass

            def shutdown(self) -> None:
                pass

        adapter = ConcreteAdapter()
        assert adapter._on_message is None

        callback = MagicMock()
        adapter.set_on_message(callback)
        assert adapter._on_message is callback

    def test_concrete_subclass_can_be_instantiated(self) -> None:
        from src.bot.adapters.base import BotAdapter

        class ConcreteAdapter(BotAdapter):
            def initialize(self, config: object) -> None:
                pass

            def reply(self, user_id: str, text: str) -> None:
                pass

            def shutdown(self) -> None:
                pass

        adapter = ConcreteAdapter()
        assert adapter is not None


class TestTelegramAdapter:
    """Tests for TelegramAdapter."""

    @pytest.fixture(autouse=True)
    def reset_config_singleton(self) -> None:
        """Reset the Config singleton before each test."""
        import src.config as config_module
        config_module.Config._instance = None
        yield  # type: ignore[misc]
        config_module.Config._instance = None

    def test_initialize_raises_when_not_installed(self) -> None:
        """When telegram-bot is not installed, initialize raises ImportError."""
        with patch(
            "src.bot.adapters.telegram_adapter.TELEGRAM_AVAILABLE", False
        ):
            from src.bot.adapters.telegram_adapter import TelegramAdapter

            adapter = TelegramAdapter()
            mock_config = MagicMock()
            with pytest.raises(ImportError, match="telegram-bot package not installed"):
                adapter.initialize(mock_config)

    def test_initialize_calls_bot_methods(self) -> None:
        """initialize() should configure and start the Telegram bot."""
        mock_bot_instance = MagicMock()
        mock_bot_cls = MagicMock()
        mock_bot_cls.get_instance.return_value = mock_bot_instance
        mock_settings_cls = MagicMock()

        with (
            patch(
                "src.bot.adapters.telegram_adapter.TELEGRAM_AVAILABLE", True
            ),
            patch(
                "src.bot.adapters.telegram_adapter.TelegramBot",
                mock_bot_cls,
                create=True,
            ),
            patch(
                "src.bot.adapters.telegram_adapter.TelegramSettings",
                mock_settings_cls,
                create=True,
            ),
        ):
            from src.bot.adapters.telegram_adapter import TelegramAdapter

            adapter = TelegramAdapter()

            mock_config = MagicMock()
            mock_config.get_bot_setting.side_effect = lambda key, **kw: {
                "bot_token": "test-token",
                "channel_id": "chan-123",
                "allowed_user_ids": "111,222",
            }.get(key, "")

            adapter.initialize(mock_config)

            mock_bot_cls.get_instance.assert_called_once()
            mock_settings_cls.assert_called_once_with(
                bot_token="test-token",
                channel_id="chan-123",
                allowed_user_ids={111, 222},
            )
            mock_bot_instance.initialize.assert_called_once()
            mock_bot_instance.add_message_handler.assert_called_once_with(
                adapter._handle_update
            )
            mock_bot_instance.start_receiving.assert_called_once()

    def test_initialize_with_no_allowed_ids(self) -> None:
        """When allowed_user_ids is empty, pass None to settings."""
        mock_bot_instance = MagicMock()
        mock_bot_cls = MagicMock()
        mock_bot_cls.get_instance.return_value = mock_bot_instance
        mock_settings_cls = MagicMock()

        with (
            patch(
                "src.bot.adapters.telegram_adapter.TELEGRAM_AVAILABLE", True
            ),
            patch(
                "src.bot.adapters.telegram_adapter.TelegramBot",
                mock_bot_cls,
                create=True,
            ),
            patch(
                "src.bot.adapters.telegram_adapter.TelegramSettings",
                mock_settings_cls,
                create=True,
            ),
        ):
            from src.bot.adapters.telegram_adapter import TelegramAdapter

            adapter = TelegramAdapter()

            mock_config = MagicMock()
            mock_config.get_bot_setting.side_effect = lambda key, **kw: {
                "bot_token": "test-token",
                "channel_id": "chan-123",
                "allowed_user_ids": "",
            }.get(key, "")

            adapter.initialize(mock_config)

            mock_settings_cls.assert_called_once_with(
                bot_token="test-token",
                channel_id="chan-123",
                allowed_user_ids=None,
            )

    def test_handle_update_creates_bot_message(self) -> None:
        """_handle_update converts Telegram update to BotMessage and calls callback."""
        with patch(
            "src.bot.adapters.telegram_adapter.TELEGRAM_AVAILABLE", True
        ):
            from src.bot.adapters.telegram_adapter import TelegramAdapter

            adapter = TelegramAdapter()
            callback = MagicMock()
            adapter.set_on_message(callback)

            # Create mock update
            mock_update = MagicMock()
            mock_update.message.text = "/list"
            mock_update.message.chat_id = 12345

            adapter._handle_update(mock_update)

            callback.assert_called_once()
            msg = callback.call_args[0][0]
            assert isinstance(msg, BotMessage)
            assert msg.user_id == "12345"
            assert msg.text == "/list"

    def test_handle_update_ignores_empty_message(self) -> None:
        """_handle_update should ignore updates without text."""
        with patch(
            "src.bot.adapters.telegram_adapter.TELEGRAM_AVAILABLE", True
        ):
            from src.bot.adapters.telegram_adapter import TelegramAdapter

            adapter = TelegramAdapter()
            callback = MagicMock()
            adapter.set_on_message(callback)

            mock_update = MagicMock()
            mock_update.message.text = None

            adapter._handle_update(mock_update)
            callback.assert_not_called()

    def test_handle_update_ignores_no_message(self) -> None:
        """_handle_update should ignore updates without message."""
        with patch(
            "src.bot.adapters.telegram_adapter.TELEGRAM_AVAILABLE", True
        ):
            from src.bot.adapters.telegram_adapter import TelegramAdapter

            adapter = TelegramAdapter()
            callback = MagicMock()
            adapter.set_on_message(callback)

            mock_update = MagicMock()
            mock_update.message = None

            adapter._handle_update(mock_update)
            callback.assert_not_called()

    def test_handle_update_no_callback_set(self) -> None:
        """_handle_update should not crash when no callback is set."""
        with patch(
            "src.bot.adapters.telegram_adapter.TELEGRAM_AVAILABLE", True
        ):
            from src.bot.adapters.telegram_adapter import TelegramAdapter

            adapter = TelegramAdapter()
            # No callback set

            mock_update = MagicMock()
            mock_update.message.text = "/list"
            mock_update.message.chat_id = 12345

            # Should not raise
            adapter._handle_update(mock_update)

    def test_reply_calls_bot_reply(self) -> None:
        """reply() should call TelegramBot.reply_to_user."""
        mock_bot_instance = MagicMock()
        mock_bot_cls = MagicMock()
        mock_bot_cls.get_instance.return_value = mock_bot_instance

        with (
            patch(
                "src.bot.adapters.telegram_adapter.TELEGRAM_AVAILABLE", True
            ),
            patch(
                "src.bot.adapters.telegram_adapter.TelegramBot",
                mock_bot_cls,
                create=True,
            ),
        ):
            from src.bot.adapters.telegram_adapter import TelegramAdapter

            adapter = TelegramAdapter()
            adapter.reply("12345", "Hello!")

            mock_bot_instance.reply_to_user.assert_called_once_with(
                "Hello!", 12345
            )

    def test_reply_does_nothing_when_not_available(self) -> None:
        """reply() should do nothing when telegram is not available."""
        with patch(
            "src.bot.adapters.telegram_adapter.TELEGRAM_AVAILABLE", False
        ):
            from src.bot.adapters.telegram_adapter import TelegramAdapter

            adapter = TelegramAdapter()
            # Should not raise
            adapter.reply("12345", "Hello!")

    def test_shutdown_calls_bot_shutdown(self) -> None:
        """shutdown() should call flush and shutdown on TelegramBot."""
        mock_bot_instance = MagicMock()
        mock_bot_cls = MagicMock()
        mock_bot_cls.get_instance.return_value = mock_bot_instance

        with (
            patch(
                "src.bot.adapters.telegram_adapter.TELEGRAM_AVAILABLE", True
            ),
            patch(
                "src.bot.adapters.telegram_adapter.TelegramBot",
                mock_bot_cls,
                create=True,
            ),
        ):
            from src.bot.adapters.telegram_adapter import TelegramAdapter

            adapter = TelegramAdapter()
            adapter.shutdown()

            mock_bot_instance.flush.assert_called_once()
            mock_bot_instance.shutdown.assert_called_once()

    def test_shutdown_handles_exception(self) -> None:
        """shutdown() should catch exceptions and log them."""
        mock_bot_instance = MagicMock()
        mock_bot_instance.flush.side_effect = RuntimeError("shutdown fail")
        mock_bot_cls = MagicMock()
        mock_bot_cls.get_instance.return_value = mock_bot_instance

        with (
            patch(
                "src.bot.adapters.telegram_adapter.TELEGRAM_AVAILABLE", True
            ),
            patch(
                "src.bot.adapters.telegram_adapter.TelegramBot",
                mock_bot_cls,
                create=True,
            ),
        ):
            from src.bot.adapters.telegram_adapter import TelegramAdapter

            adapter = TelegramAdapter()
            # Should not raise
            adapter.shutdown()

    def test_shutdown_does_nothing_when_not_available(self) -> None:
        """shutdown() should do nothing when telegram is not available."""
        with patch(
            "src.bot.adapters.telegram_adapter.TELEGRAM_AVAILABLE", False
        ):
            from src.bot.adapters.telegram_adapter import TelegramAdapter

            adapter = TelegramAdapter()
            # Should not raise
            adapter.shutdown()


class TestXmppAdapter:
    """Tests for XmppAdapter."""

    @pytest.fixture(autouse=True)
    def reset_config_singleton(self) -> None:
        """Reset the Config singleton before each test."""
        import src.config as config_module
        config_module.Config._instance = None
        yield  # type: ignore[misc]
        config_module.Config._instance = None

    def test_initialize_raises_when_not_installed(self) -> None:
        """When xmpp-bot is not installed, initialize raises ImportError."""
        with patch("src.bot.adapters.xmpp_adapter.XMPP_AVAILABLE", False):
            from src.bot.adapters.xmpp_adapter import XmppAdapter

            adapter = XmppAdapter()
            mock_config = MagicMock()
            with pytest.raises(ImportError, match="xmpp-bot package not installed"):
                adapter.initialize(mock_config)

    def test_initialize_calls_bot_methods(self) -> None:
        """initialize() should start event loop, configure, and start XMPP bot."""
        mock_bot_instance = MagicMock()
        mock_bot_instance.initialize = AsyncMock()
        mock_bot_cls = MagicMock()
        mock_bot_cls.get_instance.return_value = mock_bot_instance
        mock_settings_cls = MagicMock()

        with (
            patch("src.bot.adapters.xmpp_adapter.XMPP_AVAILABLE", True),
            patch(
                "src.bot.adapters.xmpp_adapter.XmppBot",
                mock_bot_cls,
                create=True,
            ),
            patch(
                "src.bot.adapters.xmpp_adapter.XmppSettings",
                mock_settings_cls,
                create=True,
            ),
        ):
            from src.bot.adapters.xmpp_adapter import XmppAdapter

            adapter = XmppAdapter()

            mock_config = MagicMock()
            mock_config.get_bot_setting.side_effect = lambda key, **kw: {
                "jid": "bot@example.com",
                "password": "secret",
                "default_receiver": "user@example.com",
                "allowed_jids": "user@example.com,admin@example.com",
            }.get(key, "")

            adapter.initialize(mock_config)

            mock_bot_cls.get_instance.assert_called()
            mock_settings_cls.assert_called_once_with(
                jid="bot@example.com",
                password="secret",
                default_receiver="user@example.com",
                allowed_jids=frozenset(
                    {"user@example.com", "admin@example.com"}
                ),
            )
            mock_bot_instance.initialize.assert_awaited_once()
            mock_bot_instance.add_message_handler.assert_called_once_with(
                "task_scheduler", adapter._handle_message
            )

            # Cleanup
            adapter.shutdown()

    def test_initialize_with_no_allowed_jids(self) -> None:
        """When allowed_jids is empty, pass empty frozenset."""
        mock_bot_instance = MagicMock()
        mock_bot_instance.initialize = AsyncMock()
        mock_bot_cls = MagicMock()
        mock_bot_cls.get_instance.return_value = mock_bot_instance
        mock_settings_cls = MagicMock()

        with (
            patch("src.bot.adapters.xmpp_adapter.XMPP_AVAILABLE", True),
            patch(
                "src.bot.adapters.xmpp_adapter.XmppBot",
                mock_bot_cls,
                create=True,
            ),
            patch(
                "src.bot.adapters.xmpp_adapter.XmppSettings",
                mock_settings_cls,
                create=True,
            ),
        ):
            from src.bot.adapters.xmpp_adapter import XmppAdapter

            adapter = XmppAdapter()

            mock_config = MagicMock()
            mock_config.get_bot_setting.side_effect = lambda key, **kw: {
                "jid": "bot@example.com",
                "password": "secret",
                "default_receiver": "user@example.com",
                "allowed_jids": "",
            }.get(key, "")

            adapter.initialize(mock_config)

            mock_settings_cls.assert_called_once_with(
                jid="bot@example.com",
                password="secret",
                default_receiver="user@example.com",
                allowed_jids=frozenset(),
            )

            # Cleanup
            adapter.shutdown()

    def test_handle_message_creates_bot_message(self) -> None:
        """_handle_message converts XMPP message to BotMessage and calls callback."""
        with patch("src.bot.adapters.xmpp_adapter.XMPP_AVAILABLE", True):
            from src.bot.adapters.xmpp_adapter import XmppAdapter

            adapter = XmppAdapter()
            callback = MagicMock()
            adapter.set_on_message(callback)

            # Run the async handler
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(
                    adapter._handle_message(
                        "user@example.com/resource", "/list", MagicMock()
                    )
                )
            finally:
                loop.close()

            callback.assert_called_once()
            msg = callback.call_args[0][0]
            assert isinstance(msg, BotMessage)
            assert msg.user_id == "user@example.com"
            assert msg.text == "/list"

    def test_handle_message_strips_resource(self) -> None:
        """_handle_message should strip XMPP resource from JID."""
        with patch("src.bot.adapters.xmpp_adapter.XMPP_AVAILABLE", True):
            from src.bot.adapters.xmpp_adapter import XmppAdapter

            adapter = XmppAdapter()
            callback = MagicMock()
            adapter.set_on_message(callback)

            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(
                    adapter._handle_message(
                        "user@server.org/mobile", "hello", MagicMock()
                    )
                )
            finally:
                loop.close()

            msg = callback.call_args[0][0]
            assert msg.user_id == "user@server.org"

    def test_handle_message_no_callback_set(self) -> None:
        """_handle_message should not crash when no callback is set."""
        with patch("src.bot.adapters.xmpp_adapter.XMPP_AVAILABLE", True):
            from src.bot.adapters.xmpp_adapter import XmppAdapter

            adapter = XmppAdapter()
            # No callback set

            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(
                    adapter._handle_message(
                        "user@example.com", "/list", MagicMock()
                    )
                )
            finally:
                loop.close()

    def test_reply_calls_bot_reply(self) -> None:
        """reply() should schedule reply_to_user coroutine on the event loop."""
        mock_bot_instance = MagicMock()
        mock_bot_instance.reply_to_user = AsyncMock()
        mock_bot_cls = MagicMock()
        mock_bot_cls.get_instance.return_value = mock_bot_instance

        with (
            patch("src.bot.adapters.xmpp_adapter.XMPP_AVAILABLE", True),
            patch(
                "src.bot.adapters.xmpp_adapter.XmppBot",
                mock_bot_cls,
                create=True,
            ),
        ):
            from src.bot.adapters.xmpp_adapter import XmppAdapter

            adapter = XmppAdapter()
            # Create a real event loop for the adapter
            adapter._loop = asyncio.new_event_loop()

            try:
                adapter.reply("user@example.com", "Hello!")

                # Run pending tasks on the loop to let the coroutine execute
                adapter._loop.run_until_complete(asyncio.sleep(0.05))
            finally:
                adapter._loop.call_soon_threadsafe(adapter._loop.stop)
                adapter._loop.close()

    def test_reply_does_nothing_when_not_available(self) -> None:
        """reply() should do nothing when xmpp is not available."""
        with patch("src.bot.adapters.xmpp_adapter.XMPP_AVAILABLE", False):
            from src.bot.adapters.xmpp_adapter import XmppAdapter

            adapter = XmppAdapter()
            # Should not raise
            adapter.reply("user@example.com", "Hello!")

    def test_reply_does_nothing_when_no_loop(self) -> None:
        """reply() should do nothing when no event loop is set."""
        with patch("src.bot.adapters.xmpp_adapter.XMPP_AVAILABLE", True):
            from src.bot.adapters.xmpp_adapter import XmppAdapter

            adapter = XmppAdapter()
            adapter._loop = None
            # Should not raise
            adapter.reply("user@example.com", "Hello!")

    def test_shutdown_calls_bot_disconnect(self) -> None:
        """shutdown() should disconnect XMPP bot and stop event loop."""
        mock_bot_instance = MagicMock()
        mock_bot_instance.disconnect = AsyncMock()
        mock_bot_cls = MagicMock()
        mock_bot_cls.get_instance.return_value = mock_bot_instance

        with (
            patch("src.bot.adapters.xmpp_adapter.XMPP_AVAILABLE", True),
            patch(
                "src.bot.adapters.xmpp_adapter.XmppBot",
                mock_bot_cls,
                create=True,
            ),
        ):
            from src.bot.adapters.xmpp_adapter import XmppAdapter

            adapter = XmppAdapter()
            adapter._loop = asyncio.new_event_loop()

            adapter.shutdown()

            # The loop should have been stopped
            assert adapter._loop.is_closed() or not adapter._loop.is_running()

    def test_shutdown_handles_exception(self) -> None:
        """shutdown() should catch exceptions and log them."""
        mock_bot_cls = MagicMock()
        mock_bot_cls.get_instance.side_effect = RuntimeError("disconnect fail")

        with (
            patch("src.bot.adapters.xmpp_adapter.XMPP_AVAILABLE", True),
            patch(
                "src.bot.adapters.xmpp_adapter.XmppBot",
                mock_bot_cls,
                create=True,
            ),
        ):
            from src.bot.adapters.xmpp_adapter import XmppAdapter

            adapter = XmppAdapter()
            adapter._loop = asyncio.new_event_loop()

            # Should not raise
            adapter.shutdown()
            adapter._loop.close()

    def test_shutdown_does_nothing_when_not_available(self) -> None:
        """shutdown() should do nothing when xmpp is not available."""
        with patch("src.bot.adapters.xmpp_adapter.XMPP_AVAILABLE", False):
            from src.bot.adapters.xmpp_adapter import XmppAdapter

            adapter = XmppAdapter()
            # Should not raise
            adapter.shutdown()


class TestCallbackIntegration:
    """Tests for set_on_message callback across both adapters."""

    @pytest.fixture(autouse=True)
    def reset_config_singleton(self) -> None:
        """Reset the Config singleton before each test."""
        import src.config as config_module
        config_module.Config._instance = None
        yield  # type: ignore[misc]
        config_module.Config._instance = None

    def test_telegram_callback_called_on_message(self) -> None:
        """TelegramAdapter should invoke callback when message arrives."""
        with patch(
            "src.bot.adapters.telegram_adapter.TELEGRAM_AVAILABLE", True
        ):
            from src.bot.adapters.telegram_adapter import TelegramAdapter

            adapter = TelegramAdapter()
            received_messages: list[BotMessage] = []

            def on_message(msg: BotMessage) -> None:
                received_messages.append(msg)

            adapter.set_on_message(on_message)

            mock_update = MagicMock()
            mock_update.message.text = "test message"
            mock_update.message.chat_id = 999

            adapter._handle_update(mock_update)

            assert len(received_messages) == 1
            assert received_messages[0].user_id == "999"
            assert received_messages[0].text == "test message"

    def test_xmpp_callback_called_on_message(self) -> None:
        """XmppAdapter should invoke callback when message arrives."""
        with patch("src.bot.adapters.xmpp_adapter.XMPP_AVAILABLE", True):
            from src.bot.adapters.xmpp_adapter import XmppAdapter

            adapter = XmppAdapter()
            received_messages: list[BotMessage] = []

            def on_message(msg: BotMessage) -> None:
                received_messages.append(msg)

            adapter.set_on_message(on_message)

            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(
                    adapter._handle_message(
                        "sender@example.com/res", "xmpp msg", MagicMock()
                    )
                )
            finally:
                loop.close()

            assert len(received_messages) == 1
            assert received_messages[0].user_id == "sender@example.com"
            assert received_messages[0].text == "xmpp msg"

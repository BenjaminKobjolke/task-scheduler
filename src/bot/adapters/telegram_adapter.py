"""Telegram bot adapter."""
from ..types import BotMessage
from .base import BotAdapter

try:
    from telegram_bot import TelegramBot
    from telegram_bot import Settings as TelegramSettings

    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

from src.constants import Bot as BotConstants
from src.logger import Logger


class TelegramAdapter(BotAdapter):
    """Adapter for telegram-bot library."""

    def __init__(self) -> None:
        super().__init__()
        self._logger = Logger("TelegramAdapter")

    def initialize(self, config: object) -> None:
        """Initialize the Telegram bot connection.

        Args:
            config: Config instance with get_bot_setting method.

        Raises:
            ImportError: If telegram-bot package is not installed.
        """
        if not TELEGRAM_AVAILABLE:
            raise ImportError(
                "telegram-bot package not installed. "
                "Run tools/install_telegram_bot.bat"
            )

        bot = TelegramBot.get_instance()

        token = config.get_bot_setting(BotConstants.KEY_BOT_TOKEN)  # type: ignore[union-attr]
        channel_id = config.get_bot_setting(BotConstants.KEY_CHANNEL_ID)  # type: ignore[union-attr]
        allowed_ids_str = config.get_bot_setting(BotConstants.KEY_ALLOWED_USER_IDS)  # type: ignore[union-attr]

        allowed_user_ids = None
        if allowed_ids_str:
            allowed_user_ids = {
                int(uid.strip()) for uid in allowed_ids_str.split(",")
            }

        settings = TelegramSettings(
            bot_token=token,
            channel_id=channel_id,
            allowed_user_ids=allowed_user_ids,
        )
        bot.initialize(settings=settings)
        bot.add_message_handler(self._handle_update)
        bot.start_receiving()
        self._logger.info("Telegram bot initialized")

    def _handle_update(self, update: object) -> None:
        """Handle incoming Telegram update.

        Args:
            update: Telegram update object with message attribute.
        """
        if not getattr(update, "message", None):
            return
        message = update.message  # type: ignore[union-attr]
        if not getattr(message, "text", None):
            return

        msg = BotMessage(
            user_id=str(message.chat_id),
            text=message.text,
        )
        if self._on_message:
            self._on_message(msg)

    def reply(self, user_id: str, text: str) -> None:
        """Send a reply to a Telegram user.

        Args:
            user_id: The chat ID as string.
            text: The message text to send.
        """
        if TELEGRAM_AVAILABLE:
            TelegramBot.get_instance().reply_to_user(text, int(user_id))

    def shutdown(self) -> None:
        """Shutdown the Telegram bot connection."""
        if TELEGRAM_AVAILABLE:
            try:
                bot = TelegramBot.get_instance()
                bot.flush()
                bot.shutdown()
            except Exception as e:
                self._logger.error(f"Error shutting down Telegram bot: {e}")

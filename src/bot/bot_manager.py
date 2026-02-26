"""Bot lifecycle manager - factory and coordinator."""
from typing import Optional

from src.config import Config
from src.constants import Bot as BotConstants
from src.logger import Logger
from src.scheduler import TaskScheduler

from .adapters.base import BotAdapter
from .command_processor import CommandProcessor
from .types import BotMessage


class BotManager:
    """Factory and lifecycle manager for bot integration."""

    def __init__(self, scheduler: TaskScheduler, config: Config) -> None:
        self._scheduler = scheduler
        self._config = config
        self._adapter: Optional[BotAdapter] = None
        self._processor: Optional[CommandProcessor] = None
        self._logger = Logger("BotManager")

    def start(self) -> bool:
        """Initialize and start the bot if configured.

        Returns True if bot was started, False if bot type is 'none'.
        """
        bot_type = self._config.get_bot_type()
        if bot_type == BotConstants.TYPE_NONE:
            self._logger.info("Bot integration disabled (type=none)")
            return False

        bot_config = self._config.get_bot_config()
        self._processor = CommandProcessor(self._scheduler, bot_config)

        if bot_type == BotConstants.TYPE_TELEGRAM:
            from .adapters.telegram_adapter import TelegramAdapter

            self._adapter = TelegramAdapter()
        elif bot_type == BotConstants.TYPE_XMPP:
            from .adapters.xmpp_adapter import XmppAdapter

            self._adapter = XmppAdapter()
        else:
            self._logger.error(f"Unknown bot type: {bot_type}")
            return False

        self._adapter.set_on_message(self._on_message)
        self._adapter.initialize(self._config)
        self._logger.info(f"Bot integration started (type={bot_type})")
        return True

    def _on_message(self, message: BotMessage) -> None:
        """Handle incoming message: process and reply."""
        try:
            if self._processor and self._adapter:
                response = self._processor.process(message)
                if response.text:
                    self._adapter.reply(message.user_id, response.text)
        except Exception as e:
            self._logger.error(f"Error processing bot message: {e}")

    def shutdown(self) -> None:
        """Shutdown the bot if running."""
        if self._adapter:
            try:
                self._adapter.shutdown()
                self._logger.info("Bot integration stopped")
            except Exception as e:
                self._logger.error(f"Error shutting down bot: {e}")

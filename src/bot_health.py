"""Bot health monitoring and auto-reconnection."""

from bot_commander import BotManager

from .constants import Bot
from .logger import Logger

try:
    from xmpp_bot import XmppBot
except ImportError:
    XmppBot = None  # type: ignore[assignment, misc]


class BotHealthMonitor:
    """Monitors bot thread health and attempts reconnection when the bot dies.

    Attributes:
        reconnect_attempts: Number of consecutive reconnect attempts made.
    """

    def __init__(self, bot_manager: BotManager, logger: Logger) -> None:
        self._bot_manager = bot_manager
        self._logger = logger
        self.reconnect_attempts: int = 0

    def is_alive(self) -> bool:
        """Check whether the bot adapter thread is still running.

        Returns:
            True if the adapter thread exists and is alive, False otherwise.
        """
        adapter = getattr(self._bot_manager, "_adapter", None)
        if adapter is None:
            return False
        thread = getattr(adapter, "_thread", None)
        if thread is None:
            return False
        return thread.is_alive()

    def is_connected(self) -> bool:
        """Check whether the bot is actually connected to the server.

        Returns:
            True if the XmppBot singleton reports connected, False otherwise.
            Returns False when xmpp-bot is not installed (e.g. telegram-only).
        """
        try:
            return XmppBot.get_instance().is_connected  # type: ignore[union-attr]
        except Exception:
            return False

    def reconnect(self) -> bool:
        """Shut down and restart the bot.

        Increments ``reconnect_attempts`` before the attempt.  On success the
        counter is reset to zero.

        Returns:
            True if the bot restarted successfully, False otherwise.
        """
        self.reconnect_attempts += 1
        try:
            self._bot_manager.shutdown()
            started = self._bot_manager.start()
            if started:
                self._logger.info(
                    f"Bot reconnected successfully (attempt {self.reconnect_attempts})"
                )
                self.reconnect_attempts = 0
                return True
            self._logger.warning("Bot start() returned False during reconnect")
            return False
        except Exception as exc:
            self._logger.error(f"Bot reconnect failed: {exc}", exc_info=True)
            return False

    def check_health(self) -> None:
        """Run a single health check cycle.

        Checks both thread liveness AND connection state. A thread that is
        alive but disconnected also triggers reconnection.
        """
        if self.is_alive() and self.is_connected():
            if self.reconnect_attempts > 0:
                self.reconnect_attempts = 0
            return

        if self.reconnect_attempts >= Bot.MAX_RECONNECT_ATTEMPTS:
            self._logger.error(
                f"Bot reconnect attempts exhausted ({Bot.MAX_RECONNECT_ATTEMPTS}). "
                "Bot will remain offline until scheduler restart."
            )
            return

        if not self.is_alive():
            self._logger.warning("Bot thread is no longer alive — attempting reconnect")
        else:
            self._logger.warning(
                "Bot thread alive but disconnected — attempting reconnect"
            )
        self.reconnect()

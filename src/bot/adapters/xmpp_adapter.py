"""XMPP bot adapter."""
import asyncio
import threading

from ..types import BotMessage
from .base import BotAdapter

try:
    from xmpp_bot import XmppBot
    from xmpp_bot import Settings as XmppSettings

    XMPP_AVAILABLE = True
except ImportError:
    XMPP_AVAILABLE = False

from src.constants import Bot as BotConstants
from src.logger import Logger


class XmppAdapter(BotAdapter):
    """Adapter for xmpp-bot library."""

    def __init__(self) -> None:
        super().__init__()
        self._logger = Logger("XmppAdapter")
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    def initialize(self, config: object) -> None:
        """Initialize the XMPP bot connection.

        Args:
            config: Config instance with get_bot_setting method.

        Raises:
            ImportError: If xmpp-bot package is not installed.
        """
        if not XMPP_AVAILABLE:
            raise ImportError(
                "xmpp-bot package not installed. "
                "Run tools/install_xmpp_bot.bat"
            )

        # Start async event loop in background thread
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        # Schedule async init on the event loop
        future = asyncio.run_coroutine_threadsafe(
            self._async_init(config), self._loop
        )
        future.result(timeout=30)
        self._logger.info("XMPP bot initialized")

    def _run_loop(self) -> None:
        """Run the async event loop in a background thread."""
        asyncio.set_event_loop(self._loop)
        if self._loop:
            self._loop.run_forever()

    async def _async_init(self, config: object) -> None:
        """Async initialization of the XMPP bot.

        Args:
            config: Config instance with get_bot_setting method.
        """
        bot = XmppBot.get_instance()

        jid = config.get_bot_setting(BotConstants.KEY_JID)  # type: ignore[union-attr]
        password = config.get_bot_setting(BotConstants.KEY_PASSWORD)  # type: ignore[union-attr]
        default_receiver = config.get_bot_setting(BotConstants.KEY_DEFAULT_RECEIVER)  # type: ignore[union-attr]
        allowed_jids_str = config.get_bot_setting(BotConstants.KEY_ALLOWED_JIDS)  # type: ignore[union-attr]

        allowed_jids: frozenset[str] = frozenset()
        if allowed_jids_str:
            allowed_jids = frozenset(
                j.strip() for j in allowed_jids_str.split(",")
            )

        settings = XmppSettings(
            jid=jid,
            password=password,
            default_receiver=default_receiver,
            allowed_jids=allowed_jids,
        )
        await bot.initialize(settings=settings)
        bot.add_message_handler("task_scheduler", self._handle_message)

    async def _handle_message(
        self, sender: str, message: str, stanza: object
    ) -> None:
        """Handle incoming XMPP message.

        Args:
            sender: Full JID of the sender (user@server/resource).
            message: The message text.
            stanza: The raw XMPP stanza object.
        """
        bare_jid = sender.split("/")[0]
        msg = BotMessage(user_id=bare_jid, text=message)
        if self._on_message:
            self._on_message(msg)

    def reply(self, user_id: str, text: str) -> None:
        """Send a reply to an XMPP user.

        Args:
            user_id: The bare JID of the recipient.
            text: The message text to send.
        """
        if XMPP_AVAILABLE and self._loop:
            asyncio.run_coroutine_threadsafe(
                XmppBot.get_instance().reply_to_user(text, user_id),
                self._loop,
            )

    def shutdown(self) -> None:
        """Shutdown the XMPP bot connection and event loop."""
        if XMPP_AVAILABLE:
            try:
                if self._loop:
                    asyncio.run_coroutine_threadsafe(
                        XmppBot.get_instance().disconnect(), self._loop
                    )
                    self._loop.call_soon_threadsafe(self._loop.stop)
            except Exception as e:
                self._logger.error(f"Error shutting down XMPP bot: {e}")

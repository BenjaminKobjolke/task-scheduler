"""Abstract base class for bot adapters."""
from abc import ABC, abstractmethod
from typing import Callable, Optional

from ..types import BotMessage


class BotAdapter(ABC):
    """Abstract adapter normalizing bot APIs."""

    def __init__(self) -> None:
        self._on_message: Optional[Callable[[BotMessage], None]] = None

    def set_on_message(self, callback: Callable[[BotMessage], None]) -> None:
        """Set the callback for incoming messages."""
        self._on_message = callback

    @abstractmethod
    def initialize(self, config: object) -> None:
        """Initialize the bot connection using config.ini settings."""

    @abstractmethod
    def reply(self, user_id: str, text: str) -> None:
        """Send a reply to a user."""

    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown the bot connection."""

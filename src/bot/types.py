"""Data transfer objects for bot integration."""
from dataclasses import dataclass


@dataclass(frozen=True)
class BotMessage:
    """Normalized incoming message from any bot."""
    user_id: str
    text: str


@dataclass(frozen=True)
class BotResponse:
    """Response to send back to user."""
    text: str


@dataclass(frozen=True)
class BotConfig:
    """Bot configuration settings."""
    bot_type: str
    allow_add: bool
    allow_edit: bool
    allow_delete: bool

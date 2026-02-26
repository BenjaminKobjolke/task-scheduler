"""Tests for bot types module."""
import dataclasses

import pytest

from src.bot.types import BotConfig, BotMessage, BotResponse


class TestBotMessage:
    """Tests for BotMessage dataclass."""

    def test_create_bot_message(self) -> None:
        msg = BotMessage(user_id="123", text="hello")
        assert msg.user_id == "123"
        assert msg.text == "hello"

    def test_bot_message_is_frozen(self) -> None:
        msg = BotMessage(user_id="123", text="hello")
        with pytest.raises(dataclasses.FrozenInstanceError):
            msg.text = "new"  # type: ignore[misc]

    def test_bot_message_fields(self) -> None:
        fields = {f.name: f.type for f in dataclasses.fields(BotMessage)}
        assert fields == {"user_id": str, "text": str}

    def test_bot_message_equality(self) -> None:
        msg1 = BotMessage(user_id="123", text="hello")
        msg2 = BotMessage(user_id="123", text="hello")
        assert msg1 == msg2

    def test_bot_message_inequality(self) -> None:
        msg1 = BotMessage(user_id="123", text="hello")
        msg2 = BotMessage(user_id="456", text="hello")
        assert msg1 != msg2


class TestBotResponse:
    """Tests for BotResponse dataclass."""

    def test_create_bot_response(self) -> None:
        resp = BotResponse(text="OK")
        assert resp.text == "OK"

    def test_bot_response_is_frozen(self) -> None:
        resp = BotResponse(text="OK")
        with pytest.raises(dataclasses.FrozenInstanceError):
            resp.text = "new"  # type: ignore[misc]

    def test_bot_response_fields(self) -> None:
        fields = {f.name: f.type for f in dataclasses.fields(BotResponse)}
        assert fields == {"text": str}

    def test_bot_response_equality(self) -> None:
        r1 = BotResponse(text="OK")
        r2 = BotResponse(text="OK")
        assert r1 == r2


class TestBotConfig:
    """Tests for BotConfig dataclass."""

    def test_create_bot_config(self) -> None:
        cfg = BotConfig(
            bot_type="telegram",
            allow_add=True,
            allow_edit=False,
            allow_delete=True,
        )
        assert cfg.bot_type == "telegram"
        assert cfg.allow_add is True
        assert cfg.allow_edit is False
        assert cfg.allow_delete is True

    def test_bot_config_is_frozen(self) -> None:
        cfg = BotConfig(
            bot_type="none",
            allow_add=True,
            allow_edit=True,
            allow_delete=True,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            cfg.bot_type = "xmpp"  # type: ignore[misc]

    def test_bot_config_fields(self) -> None:
        from src.bot.types import BotType
        fields = {f.name: f.type for f in dataclasses.fields(BotConfig)}
        assert fields == {
            "bot_type": BotType,
            "allow_add": bool,
            "allow_edit": bool,
            "allow_delete": bool,
        }

    def test_bot_config_equality(self) -> None:
        cfg1 = BotConfig(
            bot_type="none",
            allow_add=True,
            allow_edit=True,
            allow_delete=True,
        )
        cfg2 = BotConfig(
            bot_type="none",
            allow_add=True,
            allow_edit=True,
            allow_delete=True,
        )
        assert cfg1 == cfg2

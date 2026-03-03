"""Tests for BotInteractionHandler — threading, timeout, default values."""

import threading

import pytest

from src.bot.interaction_handler import BotInteractionHandler
from src.interaction import InteractionRequest, InteractionType


@pytest.fixture
def notifier():
    """Track messages sent by the handler."""
    messages: list[tuple[str, str]] = []

    def send(user_id: str, text: str) -> None:
        messages.append((user_id, text))

    send.messages = messages  # type: ignore[attr-defined]
    return send


class TestBotInteractionHandlerConfirm:
    """Tests for confirm prompts via bot."""

    def test_confirm_yes_reply(self, notifier):
        handler = BotInteractionHandler(
            user_id="u1", notifier=notifier, timeout=5
        )
        req = InteractionRequest(
            type=InteractionType.CONFIRM, id="q1", message="Deploy?"
        )

        # Simulate user replying "yes" in another thread
        def reply():
            handler._pending_event.wait(0.1)  # Wait for event to be created
            handler.resolve("yes")

        t = threading.Thread(target=reply, daemon=True)
        t.start()

        resp = handler.handle_prompt(req)
        t.join(timeout=2)

        assert resp.id == "q1"
        assert resp.value is True
        assert len(notifier.messages) == 1

    def test_confirm_no_reply(self, notifier):
        handler = BotInteractionHandler(
            user_id="u1", notifier=notifier, timeout=5
        )
        req = InteractionRequest(
            type=InteractionType.CONFIRM, id="q1", message="Deploy?"
        )

        def reply():
            handler._pending_event.wait(0.1)
            handler.resolve("no")

        t = threading.Thread(target=reply, daemon=True)
        t.start()

        resp = handler.handle_prompt(req)
        t.join(timeout=2)

        assert resp.value is False


class TestBotInteractionHandlerInput:
    """Tests for input prompts via bot."""

    def test_input_reply(self, notifier):
        handler = BotInteractionHandler(
            user_id="u1", notifier=notifier, timeout=5
        )
        req = InteractionRequest(
            type=InteractionType.INPUT, id="q2", message="Version:"
        )

        def reply():
            handler._pending_event.wait(0.1)
            handler.resolve("2.0.0")

        t = threading.Thread(target=reply, daemon=True)
        t.start()

        resp = handler.handle_prompt(req)
        t.join(timeout=2)

        assert resp.value == "2.0.0"


class TestBotInteractionHandlerChoice:
    """Tests for choice prompts via bot."""

    def test_choice_reply_by_number(self, notifier):
        handler = BotInteractionHandler(
            user_id="u1", notifier=notifier, timeout=5
        )
        req = InteractionRequest(
            type=InteractionType.CHOICE,
            id="q3",
            message="Select env:",
            options=["staging", "production"],
        )

        def reply():
            handler._pending_event.wait(0.1)
            handler.resolve("2")

        t = threading.Thread(target=reply, daemon=True)
        t.start()

        resp = handler.handle_prompt(req)
        t.join(timeout=2)

        assert resp.value == 1  # 0-based index


class TestBotInteractionHandlerTimeout:
    """Tests for timeout behavior."""

    def test_timeout_with_default(self, notifier):
        handler = BotInteractionHandler(
            user_id="u1", notifier=notifier, timeout=0.1
        )
        req = InteractionRequest(
            type=InteractionType.CONFIRM,
            id="q1",
            message="Deploy?",
            default=True,
        )

        resp = handler.handle_prompt(req)

        assert resp.id == "q1"
        assert resp.value is True
        assert resp.timed_out is True

    def test_timeout_without_default(self, notifier):
        handler = BotInteractionHandler(
            user_id="u1", notifier=notifier, timeout=0.1
        )
        req = InteractionRequest(
            type=InteractionType.CONFIRM, id="q1", message="Deploy?"
        )

        resp = handler.handle_prompt(req)

        assert resp.id == "q1"
        assert resp.value is None
        assert resp.error is not None
        assert "Timeout" in resp.error

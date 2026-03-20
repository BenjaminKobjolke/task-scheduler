"""Tests for BotInteractionHandler and BotScriptOutput."""

import threading

import pytest
from bot_commander import BufferedNotifier

from src.bot.interaction_handler import BotInteractionHandler, BotScriptOutput
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


class TestBotInteractionHandlerCancel:
    """Tests for cancel behavior."""

    def test_cancel_unblocks_handle_prompt_with_error(self, notifier):
        """cancel() immediately unblocks a waiting handle_prompt with error."""
        handler = BotInteractionHandler(
            user_id="u1", notifier=notifier, timeout=10
        )
        req = InteractionRequest(
            type=InteractionType.CONFIRM, id="q1", message="Deploy?"
        )

        def cancel_after_brief_wait():
            import time
            time.sleep(0.1)
            handler.cancel()

        t = threading.Thread(target=cancel_after_brief_wait, daemon=True)
        t.start()

        resp = handler.handle_prompt(req)
        t.join(timeout=2)

        assert resp.id == "q1"
        assert resp.value is None
        assert resp.error is not None
        assert "Cancelled" in resp.error

    def test_subsequent_prompt_after_cancel_returns_error_immediately(self, notifier):
        """After cancel(), any further handle_prompt calls return error immediately."""
        handler = BotInteractionHandler(
            user_id="u1", notifier=notifier, timeout=10
        )
        handler.cancel()

        req = InteractionRequest(
            type=InteractionType.INPUT, id="q2", message="Version:"
        )
        resp = handler.handle_prompt(req)

        assert resp.id == "q2"
        assert resp.value is None
        assert resp.error is not None
        assert "Cancelled" in resp.error


class TestBotScriptOutput:
    """Tests for BotScriptOutput — sends lines via BufferedNotifier."""

    def test_write_line_sends_via_buffered_notifier(self, notifier):
        """write_line() sends the line through the BufferedNotifier."""
        buffered = BufferedNotifier(send_fn=notifier, interval=10.0)
        output = BotScriptOutput(user_id="u1", buffered_notifier=buffered)
        output.write_line("Processing item 5 of 10")

        # First message is sent immediately by BufferedNotifier
        assert len(notifier.messages) == 1
        assert notifier.messages[0] == ("u1", "Processing item 5 of 10")

    def test_rapid_writes_are_batched(self, notifier):
        """Rapid write_line() calls are batched by BufferedNotifier."""
        buffered = BufferedNotifier(send_fn=notifier, interval=10.0)
        output = BotScriptOutput(user_id="u1", buffered_notifier=buffered)
        output.write_line("Line 1")
        output.write_line("Line 2")
        output.write_line("Line 3")

        # First line sent immediately; lines 2-3 buffered
        assert len(notifier.messages) == 1
        assert notifier.messages[0] == ("u1", "Line 1")

        # Flush sends the rest as a single combined message
        output.close()
        assert len(notifier.messages) == 2
        assert notifier.messages[1] == ("u1", "Line 2\nLine 3")

    def test_close_flushes_remaining(self, notifier):
        """close() flushes buffered output for this user."""
        buffered = BufferedNotifier(send_fn=notifier, interval=10.0)
        output = BotScriptOutput(user_id="u1", buffered_notifier=buffered)
        output.write_line("First")
        output.write_line("Buffered")
        output.close()

        assert len(notifier.messages) == 2
        assert notifier.messages[1] == ("u1", "Buffered")

    def test_write_line_preserves_user_id(self, notifier):
        """Each BotScriptOutput instance uses its own user_id."""
        buffered = BufferedNotifier(send_fn=notifier, interval=10.0)
        output_a = BotScriptOutput(user_id="alice", buffered_notifier=buffered)
        output_b = BotScriptOutput(user_id="bob", buffered_notifier=buffered)

        output_a.write_line("Hello from Alice")
        output_b.write_line("Hello from Bob")

        assert notifier.messages[0] == ("alice", "Hello from Alice")
        assert notifier.messages[1] == ("bob", "Hello from Bob")

"""Focused tests for bot command processor behavior."""

from bot_commander import BotMessage
from src.bot.command_processor import TaskCommandProcessor
from src.bot.constants import Messages
from unittest.mock import MagicMock
import time


class TestCancelCommand:
    """Tests for the /cancel command."""

    def test_cancel_with_no_conversation(self, processor: TaskCommandProcessor) -> None:
        """Without active conversation, /cancel is treated as unknown command."""
        msg = BotMessage(user_id="user1", text="/cancel")
        response = processor.handle(msg)
        assert response.text == Messages.UNKNOWN_COMMAND

    def test_cancel_clears_active_conversation(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        # Start an add wizard
        processor.handle(BotMessage(user_id="user1", text="/add"))
        # Cancel it
        response = processor.handle(BotMessage(user_id="user1", text="/cancel"))
        assert response.text == Messages.OPERATION_CANCELLED

        # Next message should not continue the wizard
        response = processor.handle(BotMessage(user_id="user1", text="backup.py"))
        assert response.text == Messages.UNKNOWN_COMMAND



class TestUnknownCommand:
    """Tests for unknown commands."""

    def test_unknown_command(self, processor: TaskCommandProcessor) -> None:
        msg = BotMessage(user_id="user1", text="/invalid")
        response = processor.handle(msg)
        assert response.text == Messages.UNKNOWN_COMMAND

    def test_plain_text_is_unknown(self, processor: TaskCommandProcessor) -> None:
        msg = BotMessage(user_id="user1", text="hello world")
        response = processor.handle(msg)
        assert response.text == Messages.UNKNOWN_COMMAND

    def test_empty_text_is_unknown(self, processor: TaskCommandProcessor) -> None:
        msg = BotMessage(user_id="user1", text="")
        response = processor.handle(msg)
        assert response.text == Messages.UNKNOWN_COMMAND



class TestConversationExpiry:
    """Tests for conversation expiration."""

    def test_expired_conversation_is_cleaned_up(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """An expired conversation notifies user and clears state."""
        # Start an add wizard
        processor.handle(BotMessage(user_id="user1", text="/add"))

        # Manually expire the conversation
        processor._conversations["user1"].expires_at = time.time() - 1

        # Next message should report expiry and clear conversation
        response = processor.handle(BotMessage(user_id="user1", text="backup.py"))
        assert response.text == Messages.CONVERSATION_EXPIRED
        assert "user1" not in processor._conversations

    def test_non_expired_conversation_continues(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """A fresh conversation should continue normally."""
        processor.handle(BotMessage(user_id="user1", text="/add"))

        # Continue wizard (conversation should still be active)
        response = processor.handle(
            BotMessage(user_id="user1", text="C:/scripts/backup.py")
        )
        assert response.text == Messages.WIZARD_ADD_NAME



class TestMultipleUsers:
    """Tests for separate conversation state per user."""

    def test_separate_conversations_per_user(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """Different users have independent conversation states."""
        scheduler_mock.add_task.return_value = 1

        # User1 starts add wizard
        processor.handle(BotMessage(user_id="user1", text="/add"))

        # User2 also starts add wizard
        processor.handle(BotMessage(user_id="user2", text="/add"))

        # User1 continues - should be in their own wizard
        response1 = processor.handle(BotMessage(user_id="user1", text="script1.py"))
        assert response1.text == Messages.WIZARD_ADD_NAME

        # User2 continues independently
        response2 = processor.handle(BotMessage(user_id="user2", text="script2.py"))
        assert response2.text == Messages.WIZARD_ADD_NAME

    def test_user1_cancel_does_not_affect_user2(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """Cancelling one user's conversation doesn't affect another's."""
        # Both users start wizards
        processor.handle(BotMessage(user_id="user1", text="/add"))
        processor.handle(BotMessage(user_id="user2", text="/add"))

        # User1 cancels
        processor.handle(BotMessage(user_id="user1", text="/cancel"))

        # User2 should still be in wizard
        response = processor.handle(BotMessage(user_id="user2", text="script.py"))
        assert response.text == Messages.WIZARD_ADD_NAME

    def test_user_without_conversation_gets_command_handling(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """A user without active conversation gets normal command handling."""
        scheduler_mock.list_tasks.return_value = []

        # User1 starts a wizard
        processor.handle(BotMessage(user_id="user1", text="/add"))

        # User2 (no conversation) does a /list
        response = processor.handle(BotMessage(user_id="user2", text="/list"))
        assert response.text == Messages.NO_TASKS


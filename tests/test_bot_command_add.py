"""Focused tests for bot command processor behavior."""

from bot_commander import BotMessage
from tests.bot_command_support import _advance_add_wizard_to_confirmation
from src.bot.command_processor import TaskCommandProcessor
from src.bot.constants import Messages
from unittest.mock import MagicMock


class TestAddCommand:
    """Tests for the /add command and add wizard flow."""

    def test_shared_add_setup_reaches_confirmation(
        self, processor: TaskCommandProcessor
    ) -> None:
        _advance_add_wizard_to_confirmation(processor)

        assert processor._conversations["user1"].step == 7

    def test_add_starts_wizard(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        msg = BotMessage(user_id="user1", text="/add")
        response = processor.handle(msg)
        assert response.text == Messages.WIZARD_ADD_START

    def test_add_full_wizard_flow(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """Complete add wizard: script_path -> name -> interval -> start_time -> args -> confirm."""
        scheduler_mock.add_task.return_value = 42

        # Step 0: Start
        response = processor.handle(BotMessage(user_id="user1", text="/add"))
        assert response.text == Messages.WIZARD_ADD_START

        # Step 1: Script path (non-uv, skips to name)
        response = processor.handle(
            BotMessage(user_id="user1", text="C:/scripts/backup.py")
        )
        assert response.text == Messages.WIZARD_ADD_NAME

        # Step 2: Name
        response = processor.handle(BotMessage(user_id="user1", text="My Backup"))
        assert response.text == Messages.WIZARD_ADD_INTERVAL

        # Step 3: Interval
        response = processor.handle(BotMessage(user_id="user1", text="60"))
        assert response.text == Messages.WIZARD_ADD_START_TIME

        # Step 4: Start time (skip -> goes to arguments at step 6)
        response = processor.handle(BotMessage(user_id="user1", text="skip"))
        assert response.text == Messages.WIZARD_ADD_ARGUMENTS

        # Step 6: Arguments
        response = processor.handle(BotMessage(user_id="user1", text="skip"))
        assert "confirm" in response.text.lower() or "yes" in response.text.lower()

        # Step 7: Confirm
        response = processor.handle(BotMessage(user_id="user1", text="yes"))
        assert "My Backup" in response.text
        assert "42" in response.text

        scheduler_mock.add_task.assert_called_once_with(
            name="My Backup",
            script_path="C:/scripts/backup.py",
            interval=60,
            arguments=None,
            task_type="script",
            command=None,
            start_time=None,
            launch_new_process=False,
        )

    def test_add_wizard_cancel_at_confirm(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """Cancel during add wizard confirmation."""
        _advance_add_wizard_to_confirmation(processor)

        # Say "no" at confirm
        response = processor.handle(BotMessage(user_id="user1", text="no"))
        assert response.text == Messages.OPERATION_CANCELLED
        scheduler_mock.add_task.assert_not_called()

    def test_add_wizard_cancel_command_mid_wizard(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """Use /cancel command during wizard."""
        processor.handle(BotMessage(user_id="user1", text="/add"))
        processor.handle(BotMessage(user_id="user1", text="backup.py"))

        response = processor.handle(BotMessage(user_id="user1", text="/cancel"))
        assert response.text == Messages.OPERATION_CANCELLED

        # Conversation should be cleared
        scheduler_mock.add_task.assert_not_called()

    def test_add_task_error_returns_error_message(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """When scheduler.add_task raises, return an error message."""
        scheduler_mock.add_task.side_effect = RuntimeError("DB error")

        _advance_add_wizard_to_confirmation(processor)
        response = processor.handle(BotMessage(user_id="user1", text="yes"))
        assert "error" in response.text.lower() or "Error" in response.text


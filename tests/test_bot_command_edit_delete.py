"""Focused tests for bot command processor behavior."""

from bot_commander import BotMessage
from tests.bot_command_support import _make_task
from src.bot.command_processor import TaskCommandProcessor
from src.bot.constants import Commands
from src.bot.constants import Messages
from unittest.mock import MagicMock


class TestEditCommand:
    """Tests for the /edit command and edit wizard flow."""

    def test_edit_starts_wizard(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        task = _make_task(task_id=1, name="Backup")
        scheduler_mock.list_tasks.return_value = [task]
        msg = BotMessage(user_id="user1", text="/edit 1")
        response = processor.handle(msg)
        assert "Backup" in response.text
        assert "1" in response.text

    def test_edit_invalid_id(self, processor: TaskCommandProcessor) -> None:
        msg = BotMessage(user_id="user1", text="/edit abc")
        response = processor.handle(msg)
        assert response.text == Messages.INVALID_TASK_ID.format(Commands.EDIT)

    def test_edit_missing_id(self, processor: TaskCommandProcessor) -> None:
        msg = BotMessage(user_id="user1", text="/edit")
        response = processor.handle(msg)
        assert response.text == Messages.INVALID_TASK_ID.format(Commands.EDIT)

    def test_edit_nonexistent_task(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        scheduler_mock.list_tasks.return_value = []
        msg = BotMessage(user_id="user1", text="/edit 99")
        response = processor.handle(msg)
        assert response.text == Messages.TASK_NOT_FOUND.format(99)

    def test_edit_full_wizard_flow(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """Complete edit wizard: change name, keep everything else."""
        task = _make_task(
            task_id=1, name="Backup", script_path="backup.py", interval=60
        )
        scheduler_mock.list_tasks.return_value = [task]

        # Start edit
        processor.handle(BotMessage(user_id="user1", text="/edit 1"))

        # Skip script_path
        processor.handle(BotMessage(user_id="user1", text="skip"))
        # Change name
        processor.handle(BotMessage(user_id="user1", text="New Backup Name"))
        # Skip interval
        processor.handle(BotMessage(user_id="user1", text="skip"))
        # Skip start_time
        processor.handle(BotMessage(user_id="user1", text="skip"))
        # Skip arguments
        processor.handle(BotMessage(user_id="user1", text="skip"))
        # Confirm
        response = processor.handle(BotMessage(user_id="user1", text="yes"))

        assert "New Backup Name" in response.text or "updated" in response.text.lower()
        scheduler_mock.edit_task.assert_called_once()

    def test_edit_wizard_cancel(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        task = _make_task(task_id=1, name="Backup")
        scheduler_mock.list_tasks.return_value = [task]

        processor.handle(BotMessage(user_id="user1", text="/edit 1"))
        response = processor.handle(BotMessage(user_id="user1", text="/cancel"))
        assert response.text == Messages.OPERATION_CANCELLED
        scheduler_mock.edit_task.assert_not_called()

    def test_edit_task_error_returns_error_message(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """When scheduler.edit_task raises, return an error message."""
        task = _make_task(
            task_id=1, name="Backup", script_path="backup.py", interval=60
        )
        scheduler_mock.list_tasks.return_value = [task]
        scheduler_mock.edit_task.side_effect = RuntimeError("DB error")

        processor.handle(BotMessage(user_id="user1", text="/edit 1"))
        processor.handle(BotMessage(user_id="user1", text="skip"))
        processor.handle(BotMessage(user_id="user1", text="New Name"))
        processor.handle(BotMessage(user_id="user1", text="skip"))
        processor.handle(BotMessage(user_id="user1", text="skip"))
        processor.handle(BotMessage(user_id="user1", text="skip"))
        response = processor.handle(BotMessage(user_id="user1", text="yes"))
        assert "error" in response.text.lower() or "Error" in response.text



class TestDeleteCommand:
    """Tests for the /delete command and confirmation flow."""

    def test_delete_asks_confirmation(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        task = _make_task(task_id=1, name="Backup")
        scheduler_mock.list_tasks.return_value = [task]
        msg = BotMessage(user_id="user1", text="/delete 1")
        response = processor.handle(msg)
        assert "Backup" in response.text
        assert "yes" in response.text.lower()

    def test_delete_confirm_yes(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        task = _make_task(task_id=1, name="Backup")
        scheduler_mock.list_tasks.return_value = [task]

        processor.handle(BotMessage(user_id="user1", text="/delete 1"))
        response = processor.handle(BotMessage(user_id="user1", text="yes"))
        assert response.text == Messages.TASK_DELETED.format("Backup", 1)
        scheduler_mock.remove_task.assert_called_once_with(1)

    def test_delete_confirm_no(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        task = _make_task(task_id=1, name="Backup")
        scheduler_mock.list_tasks.return_value = [task]

        processor.handle(BotMessage(user_id="user1", text="/delete 1"))
        response = processor.handle(BotMessage(user_id="user1", text="no"))
        assert response.text == Messages.DELETE_CANCELLED
        scheduler_mock.remove_task.assert_not_called()

    def test_delete_invalid_id(self, processor: TaskCommandProcessor) -> None:
        msg = BotMessage(user_id="user1", text="/delete abc")
        response = processor.handle(msg)
        assert response.text == Messages.INVALID_TASK_ID.format(Commands.DELETE)

    def test_delete_missing_id(self, processor: TaskCommandProcessor) -> None:
        msg = BotMessage(user_id="user1", text="/delete")
        response = processor.handle(msg)
        assert response.text == Messages.INVALID_TASK_ID.format(Commands.DELETE)

    def test_delete_nonexistent_task(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        scheduler_mock.list_tasks.return_value = []
        msg = BotMessage(user_id="user1", text="/delete 99")
        response = processor.handle(msg)
        assert response.text == Messages.TASK_NOT_FOUND.format(99)

    def test_delete_cancel_command(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        task = _make_task(task_id=1, name="Backup")
        scheduler_mock.list_tasks.return_value = [task]

        processor.handle(BotMessage(user_id="user1", text="/delete 1"))
        response = processor.handle(BotMessage(user_id="user1", text="/cancel"))
        assert response.text == Messages.OPERATION_CANCELLED
        scheduler_mock.remove_task.assert_not_called()

    def test_delete_error_returns_error_message(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        task = _make_task(task_id=1, name="Backup")
        scheduler_mock.list_tasks.return_value = [task]
        scheduler_mock.remove_task.side_effect = RuntimeError("DB error")

        processor.handle(BotMessage(user_id="user1", text="/delete 1"))
        response = processor.handle(BotMessage(user_id="user1", text="yes"))
        assert "error" in response.text.lower() or "Error" in response.text


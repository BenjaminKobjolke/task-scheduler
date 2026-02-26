"""Tests for bot command processor."""
import time
from unittest.mock import MagicMock, patch

import pytest

from src.bot.command_processor import CommandProcessor
from src.bot.constants import Commands, Messages
from src.bot.types import BotConfig, BotMessage
from src.database import Database
from src.scheduler import TaskScheduler


# -- Fixtures and helpers --


def _make_config(
    allow_add: bool = True,
    allow_edit: bool = True,
    allow_delete: bool = True,
) -> BotConfig:
    """Create a BotConfig with specified permissions."""
    return BotConfig(
        bot_type="telegram",
        allow_add=allow_add,
        allow_edit=allow_edit,
        allow_delete=allow_delete,
    )


def _make_task(
    task_id: int = 1,
    name: str = "Backup Script",
    script_path: str = "C:/scripts/backup.py",
    interval: int = 60,
    task_type: str = "script",
    command: str | None = None,
    start_time: str | None = "09:00",
    arguments: list | None = None,
    last_run_time: str | None = None,
    last_run_success: bool | None = None,
    next_run_time: str | None = None,
) -> dict:
    """Create a sample task dict matching the real format."""
    return {
        "id": task_id,
        "name": name,
        "script_path": script_path,
        "arguments": arguments if arguments is not None else ["--verbose"],
        "interval": interval,
        "task_type": task_type,
        "command": command,
        "start_time": start_time,
        "last_run_time": last_run_time,
        "last_run_success": last_run_success,
        "next_run_time": next_run_time,
    }


def _make_execution(
    name: str = "Backup Script",
    execution_time: str = "2026-02-26 10:00:00",
    success: bool = True,
) -> dict:
    """Create a sample execution dict matching the real format."""
    return {
        "execution_id": 1,
        "execution_time": execution_time,
        "success": success,
        "task_id": 1,
        "name": name,
        "script_path": "C:/scripts/backup.py",
        "arguments": [],
        "task_type": "script",
        "command": None,
    }


@pytest.fixture()
def scheduler_mock() -> MagicMock:
    """Create a mock TaskScheduler with a mock Database."""
    mock = MagicMock(spec=TaskScheduler)
    mock.db = MagicMock(spec=Database)
    return mock


@pytest.fixture()
def config() -> BotConfig:
    """Create a default BotConfig allowing all commands."""
    return _make_config()


@pytest.fixture()
def processor(scheduler_mock: MagicMock, config: BotConfig) -> CommandProcessor:
    """Create a CommandProcessor with mocked dependencies."""
    with patch("src.bot.command_processor.Logger"):
        return CommandProcessor(scheduler=scheduler_mock, bot_config=config)


# -- Help command tests --


class TestHelpCommand:
    """Tests for the /help command."""

    def test_help_returns_help_text(self, processor: CommandProcessor) -> None:
        msg = BotMessage(user_id="user1", text="/help")
        response = processor.process(msg)
        assert response.text == Messages.HELP

    def test_help_with_extra_args_still_works(self, processor: CommandProcessor) -> None:
        msg = BotMessage(user_id="user1", text="/help something")
        response = processor.process(msg)
        assert response.text == Messages.HELP


# -- List command tests --


class TestListCommand:
    """Tests for the /list command."""

    def test_list_returns_formatted_tasks(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        tasks = [_make_task(task_id=1, name="Backup"), _make_task(task_id=2, name="Cleanup")]
        scheduler_mock.list_tasks.return_value = tasks
        msg = BotMessage(user_id="user1", text="/list")
        response = processor.process(msg)
        assert "Backup" in response.text
        assert "Cleanup" in response.text

    def test_list_empty_returns_no_tasks(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        scheduler_mock.list_tasks.return_value = []
        msg = BotMessage(user_id="user1", text="/list")
        response = processor.process(msg)
        assert response.text == Messages.NO_TASKS

    def test_list_with_filter(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        tasks = [_make_task(task_id=1, name="Backup"), _make_task(task_id=2, name="Cleanup")]
        scheduler_mock.list_tasks.return_value = tasks
        msg = BotMessage(user_id="user1", text="/list backup")
        response = processor.process(msg)
        assert "Backup" in response.text
        assert "Cleanup" not in response.text

    def test_list_filter_case_insensitive(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        tasks = [_make_task(task_id=1, name="Backup"), _make_task(task_id=2, name="Cleanup")]
        scheduler_mock.list_tasks.return_value = tasks
        msg = BotMessage(user_id="user1", text="/list BACKUP")
        response = processor.process(msg)
        assert "Backup" in response.text
        assert "Cleanup" not in response.text

    def test_list_filter_no_match_returns_no_tasks(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        tasks = [_make_task(task_id=1, name="Backup")]
        scheduler_mock.list_tasks.return_value = tasks
        msg = BotMessage(user_id="user1", text="/list nonexistent")
        response = processor.process(msg)
        assert response.text == Messages.NO_TASKS


# -- Run command tests --


class TestRunCommand:
    """Tests for the /run command."""

    def test_run_success(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        task = _make_task(task_id=1, name="Backup")
        scheduler_mock.list_tasks.return_value = [task]
        scheduler_mock.run_task.return_value = True
        msg = BotMessage(user_id="user1", text="/run 1")
        response = processor.process(msg)
        assert response.text == Messages.TASK_EXECUTED_SUCCESS.format("Backup", 1)
        scheduler_mock.run_task.assert_called_once_with(1)

    def test_run_failure(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        task = _make_task(task_id=1, name="Backup")
        scheduler_mock.list_tasks.return_value = [task]
        scheduler_mock.run_task.return_value = False
        msg = BotMessage(user_id="user1", text="/run 1")
        response = processor.process(msg)
        assert response.text == Messages.TASK_EXECUTED_FAILURE.format("Backup", 1)

    def test_run_invalid_id_not_a_number(self, processor: CommandProcessor) -> None:
        msg = BotMessage(user_id="user1", text="/run abc")
        response = processor.process(msg)
        assert response.text == Messages.INVALID_TASK_ID.format(Commands.RUN)

    def test_run_missing_id(self, processor: CommandProcessor) -> None:
        msg = BotMessage(user_id="user1", text="/run")
        response = processor.process(msg)
        assert response.text == Messages.INVALID_TASK_ID.format(Commands.RUN)

    def test_run_nonexistent_task_raises_value_error(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        scheduler_mock.list_tasks.return_value = []
        scheduler_mock.run_task.side_effect = ValueError("Task with ID 99 not found")
        msg = BotMessage(user_id="user1", text="/run 99")
        response = processor.process(msg)
        assert "not found" in response.text.lower() or "99" in response.text

    def test_run_exception_returns_error(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        task = _make_task(task_id=1, name="Backup")
        scheduler_mock.list_tasks.return_value = [task]
        scheduler_mock.run_task.side_effect = RuntimeError("Connection lost")
        msg = BotMessage(user_id="user1", text="/run 1")
        response = processor.process(msg)
        assert "Connection lost" in response.text


# -- History command tests --


class TestHistoryCommand:
    """Tests for the /history command."""

    def test_history_default_limit(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        executions = [_make_execution()]
        scheduler_mock.db.get_recent_executions.return_value = executions
        msg = BotMessage(user_id="user1", text="/history")
        response = processor.process(msg)
        scheduler_mock.db.get_recent_executions.assert_called_once_with(10)
        assert "Backup Script" in response.text

    def test_history_custom_limit(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        scheduler_mock.db.get_recent_executions.return_value = []
        msg = BotMessage(user_id="user1", text="/history 5")
        processor.process(msg)
        scheduler_mock.db.get_recent_executions.assert_called_once_with(5)

    def test_history_invalid_limit_uses_default(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        scheduler_mock.db.get_recent_executions.return_value = []
        msg = BotMessage(user_id="user1", text="/history abc")
        processor.process(msg)
        scheduler_mock.db.get_recent_executions.assert_called_once_with(10)

    def test_history_empty_returns_no_history(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        scheduler_mock.db.get_recent_executions.return_value = []
        msg = BotMessage(user_id="user1", text="/history")
        response = processor.process(msg)
        assert response.text == Messages.NO_HISTORY


# -- Add command tests --


class TestAddCommand:
    """Tests for the /add command and add wizard flow."""

    def test_add_starts_wizard(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        msg = BotMessage(user_id="user1", text="/add")
        response = processor.process(msg)
        assert response.text == Messages.WIZARD_ADD_START

    def test_add_full_wizard_flow(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """Complete add wizard: script_path -> name -> interval -> start_time -> args -> confirm."""
        scheduler_mock.add_task.return_value = 42

        # Step 0: Start
        response = processor.process(BotMessage(user_id="user1", text="/add"))
        assert response.text == Messages.WIZARD_ADD_START

        # Step 1: Script path (non-uv, skips to name)
        response = processor.process(
            BotMessage(user_id="user1", text="C:/scripts/backup.py")
        )
        assert response.text == Messages.WIZARD_ADD_NAME

        # Step 2: Name
        response = processor.process(BotMessage(user_id="user1", text="My Backup"))
        assert response.text == Messages.WIZARD_ADD_INTERVAL

        # Step 3: Interval
        response = processor.process(BotMessage(user_id="user1", text="60"))
        assert response.text == Messages.WIZARD_ADD_START_TIME

        # Step 4: Start time
        response = processor.process(BotMessage(user_id="user1", text="skip"))
        assert response.text == Messages.WIZARD_ADD_ARGUMENTS

        # Step 5: Arguments
        response = processor.process(BotMessage(user_id="user1", text="skip"))
        assert "confirm" in response.text.lower() or "yes" in response.text.lower()

        # Step 6: Confirm
        response = processor.process(BotMessage(user_id="user1", text="yes"))
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
        )

    def test_add_wizard_cancel_at_confirm(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """Cancel during add wizard confirmation."""
        processor.process(BotMessage(user_id="user1", text="/add"))
        processor.process(BotMessage(user_id="user1", text="backup.py"))
        processor.process(BotMessage(user_id="user1", text="Task"))
        processor.process(BotMessage(user_id="user1", text="5"))
        processor.process(BotMessage(user_id="user1", text="skip"))
        processor.process(BotMessage(user_id="user1", text="skip"))

        # Say "no" at confirm
        response = processor.process(BotMessage(user_id="user1", text="no"))
        assert response.text == Messages.OPERATION_CANCELLED
        scheduler_mock.add_task.assert_not_called()

    def test_add_wizard_cancel_command_mid_wizard(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """Use /cancel command during wizard."""
        processor.process(BotMessage(user_id="user1", text="/add"))
        processor.process(BotMessage(user_id="user1", text="backup.py"))

        response = processor.process(BotMessage(user_id="user1", text="/cancel"))
        assert response.text == Messages.OPERATION_CANCELLED

        # Conversation should be cleared
        scheduler_mock.add_task.assert_not_called()

    def test_add_task_error_returns_error_message(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """When scheduler.add_task raises, return an error message."""
        scheduler_mock.add_task.side_effect = RuntimeError("DB error")

        processor.process(BotMessage(user_id="user1", text="/add"))
        processor.process(BotMessage(user_id="user1", text="backup.py"))
        processor.process(BotMessage(user_id="user1", text="Task"))
        processor.process(BotMessage(user_id="user1", text="5"))
        processor.process(BotMessage(user_id="user1", text="skip"))
        processor.process(BotMessage(user_id="user1", text="skip"))
        response = processor.process(BotMessage(user_id="user1", text="yes"))
        assert "error" in response.text.lower() or "Error" in response.text


# -- Edit command tests --


class TestEditCommand:
    """Tests for the /edit command and edit wizard flow."""

    def test_edit_starts_wizard(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        task = _make_task(task_id=1, name="Backup")
        scheduler_mock.list_tasks.return_value = [task]
        msg = BotMessage(user_id="user1", text="/edit 1")
        response = processor.process(msg)
        assert "Backup" in response.text
        assert "1" in response.text

    def test_edit_invalid_id(self, processor: CommandProcessor) -> None:
        msg = BotMessage(user_id="user1", text="/edit abc")
        response = processor.process(msg)
        assert response.text == Messages.INVALID_TASK_ID.format(Commands.EDIT)

    def test_edit_missing_id(self, processor: CommandProcessor) -> None:
        msg = BotMessage(user_id="user1", text="/edit")
        response = processor.process(msg)
        assert response.text == Messages.INVALID_TASK_ID.format(Commands.EDIT)

    def test_edit_nonexistent_task(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        scheduler_mock.list_tasks.return_value = []
        msg = BotMessage(user_id="user1", text="/edit 99")
        response = processor.process(msg)
        assert response.text == Messages.TASK_NOT_FOUND.format(99)

    def test_edit_full_wizard_flow(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """Complete edit wizard: change name, keep everything else."""
        task = _make_task(task_id=1, name="Backup", script_path="backup.py", interval=60)
        scheduler_mock.list_tasks.return_value = [task]

        # Start edit
        processor.process(BotMessage(user_id="user1", text="/edit 1"))

        # Skip script_path
        processor.process(BotMessage(user_id="user1", text="skip"))
        # Change name
        processor.process(BotMessage(user_id="user1", text="New Backup Name"))
        # Skip interval
        processor.process(BotMessage(user_id="user1", text="skip"))
        # Skip start_time
        processor.process(BotMessage(user_id="user1", text="skip"))
        # Skip arguments
        processor.process(BotMessage(user_id="user1", text="skip"))
        # Confirm
        response = processor.process(BotMessage(user_id="user1", text="yes"))

        assert "New Backup Name" in response.text or "updated" in response.text.lower()
        scheduler_mock.edit_task.assert_called_once()

    def test_edit_wizard_cancel(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        task = _make_task(task_id=1, name="Backup")
        scheduler_mock.list_tasks.return_value = [task]

        processor.process(BotMessage(user_id="user1", text="/edit 1"))
        response = processor.process(BotMessage(user_id="user1", text="/cancel"))
        assert response.text == Messages.OPERATION_CANCELLED
        scheduler_mock.edit_task.assert_not_called()

    def test_edit_task_error_returns_error_message(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """When scheduler.edit_task raises, return an error message."""
        task = _make_task(task_id=1, name="Backup", script_path="backup.py", interval=60)
        scheduler_mock.list_tasks.return_value = [task]
        scheduler_mock.edit_task.side_effect = RuntimeError("DB error")

        processor.process(BotMessage(user_id="user1", text="/edit 1"))
        processor.process(BotMessage(user_id="user1", text="skip"))
        processor.process(BotMessage(user_id="user1", text="New Name"))
        processor.process(BotMessage(user_id="user1", text="skip"))
        processor.process(BotMessage(user_id="user1", text="skip"))
        processor.process(BotMessage(user_id="user1", text="skip"))
        response = processor.process(BotMessage(user_id="user1", text="yes"))
        assert "error" in response.text.lower() or "Error" in response.text


# -- Delete command tests --


class TestDeleteCommand:
    """Tests for the /delete command and confirmation flow."""

    def test_delete_asks_confirmation(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        task = _make_task(task_id=1, name="Backup")
        scheduler_mock.list_tasks.return_value = [task]
        msg = BotMessage(user_id="user1", text="/delete 1")
        response = processor.process(msg)
        assert "Backup" in response.text
        assert "yes" in response.text.lower()

    def test_delete_confirm_yes(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        task = _make_task(task_id=1, name="Backup")
        scheduler_mock.list_tasks.return_value = [task]

        processor.process(BotMessage(user_id="user1", text="/delete 1"))
        response = processor.process(BotMessage(user_id="user1", text="yes"))
        assert response.text == Messages.TASK_DELETED.format("Backup", 1)
        scheduler_mock.remove_task.assert_called_once_with(1)

    def test_delete_confirm_no(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        task = _make_task(task_id=1, name="Backup")
        scheduler_mock.list_tasks.return_value = [task]

        processor.process(BotMessage(user_id="user1", text="/delete 1"))
        response = processor.process(BotMessage(user_id="user1", text="no"))
        assert response.text == Messages.DELETE_CANCELLED
        scheduler_mock.remove_task.assert_not_called()

    def test_delete_invalid_id(self, processor: CommandProcessor) -> None:
        msg = BotMessage(user_id="user1", text="/delete abc")
        response = processor.process(msg)
        assert response.text == Messages.INVALID_TASK_ID.format(Commands.DELETE)

    def test_delete_missing_id(self, processor: CommandProcessor) -> None:
        msg = BotMessage(user_id="user1", text="/delete")
        response = processor.process(msg)
        assert response.text == Messages.INVALID_TASK_ID.format(Commands.DELETE)

    def test_delete_nonexistent_task(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        scheduler_mock.list_tasks.return_value = []
        msg = BotMessage(user_id="user1", text="/delete 99")
        response = processor.process(msg)
        assert response.text == Messages.TASK_NOT_FOUND.format(99)

    def test_delete_cancel_command(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        task = _make_task(task_id=1, name="Backup")
        scheduler_mock.list_tasks.return_value = [task]

        processor.process(BotMessage(user_id="user1", text="/delete 1"))
        response = processor.process(BotMessage(user_id="user1", text="/cancel"))
        assert response.text == Messages.OPERATION_CANCELLED
        scheduler_mock.remove_task.assert_not_called()

    def test_delete_error_returns_error_message(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        task = _make_task(task_id=1, name="Backup")
        scheduler_mock.list_tasks.return_value = [task]
        scheduler_mock.remove_task.side_effect = RuntimeError("DB error")

        processor.process(BotMessage(user_id="user1", text="/delete 1"))
        response = processor.process(BotMessage(user_id="user1", text="yes"))
        assert "error" in response.text.lower() or "Error" in response.text


# -- Cancel command tests --


class TestCancelCommand:
    """Tests for the /cancel command."""

    def test_cancel_with_no_conversation(self, processor: CommandProcessor) -> None:
        msg = BotMessage(user_id="user1", text="/cancel")
        response = processor.process(msg)
        assert response.text == Messages.OPERATION_CANCELLED

    def test_cancel_clears_active_conversation(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        # Start an add wizard
        processor.process(BotMessage(user_id="user1", text="/add"))
        # Cancel it
        response = processor.process(BotMessage(user_id="user1", text="/cancel"))
        assert response.text == Messages.OPERATION_CANCELLED

        # Next message should not continue the wizard
        response = processor.process(BotMessage(user_id="user1", text="backup.py"))
        assert response.text == Messages.UNKNOWN_COMMAND


# -- Unknown command tests --


class TestUnknownCommand:
    """Tests for unknown commands."""

    def test_unknown_command(self, processor: CommandProcessor) -> None:
        msg = BotMessage(user_id="user1", text="/invalid")
        response = processor.process(msg)
        assert response.text == Messages.UNKNOWN_COMMAND

    def test_plain_text_is_unknown(self, processor: CommandProcessor) -> None:
        msg = BotMessage(user_id="user1", text="hello world")
        response = processor.process(msg)
        assert response.text == Messages.UNKNOWN_COMMAND

    def test_empty_text_is_unknown(self, processor: CommandProcessor) -> None:
        msg = BotMessage(user_id="user1", text="")
        response = processor.process(msg)
        assert response.text == Messages.UNKNOWN_COMMAND


# -- Disabled commands tests --


class TestDisabledCommands:
    """Tests for commands disabled by configuration."""

    def test_add_disabled(self, scheduler_mock: MagicMock) -> None:
        config = _make_config(allow_add=False)
        with patch("src.bot.command_processor.Logger"):
            proc = CommandProcessor(scheduler=scheduler_mock, bot_config=config)
        msg = BotMessage(user_id="user1", text="/add")
        response = proc.process(msg)
        assert response.text == Messages.COMMAND_DISABLED.format(Commands.ADD)

    def test_edit_disabled(self, scheduler_mock: MagicMock) -> None:
        config = _make_config(allow_edit=False)
        with patch("src.bot.command_processor.Logger"):
            proc = CommandProcessor(scheduler=scheduler_mock, bot_config=config)
        msg = BotMessage(user_id="user1", text="/edit 1")
        response = proc.process(msg)
        assert response.text == Messages.COMMAND_DISABLED.format(Commands.EDIT)

    def test_delete_disabled(self, scheduler_mock: MagicMock) -> None:
        config = _make_config(allow_delete=False)
        with patch("src.bot.command_processor.Logger"):
            proc = CommandProcessor(scheduler=scheduler_mock, bot_config=config)
        msg = BotMessage(user_id="user1", text="/delete 1")
        response = proc.process(msg)
        assert response.text == Messages.COMMAND_DISABLED.format(Commands.DELETE)

    def test_list_always_allowed(self, scheduler_mock: MagicMock) -> None:
        config = _make_config(allow_add=False, allow_edit=False, allow_delete=False)
        scheduler_mock.list_tasks.return_value = []
        with patch("src.bot.command_processor.Logger"):
            proc = CommandProcessor(scheduler=scheduler_mock, bot_config=config)
        msg = BotMessage(user_id="user1", text="/list")
        response = proc.process(msg)
        assert response.text == Messages.NO_TASKS

    def test_help_always_allowed(self, scheduler_mock: MagicMock) -> None:
        config = _make_config(allow_add=False, allow_edit=False, allow_delete=False)
        with patch("src.bot.command_processor.Logger"):
            proc = CommandProcessor(scheduler=scheduler_mock, bot_config=config)
        msg = BotMessage(user_id="user1", text="/help")
        response = proc.process(msg)
        assert response.text == Messages.HELP

    def test_run_always_allowed(self, scheduler_mock: MagicMock) -> None:
        config = _make_config(allow_add=False, allow_edit=False, allow_delete=False)
        scheduler_mock.list_tasks.return_value = [_make_task(task_id=1, name="Backup")]
        scheduler_mock.run_task.return_value = True
        with patch("src.bot.command_processor.Logger"):
            proc = CommandProcessor(scheduler=scheduler_mock, bot_config=config)
        msg = BotMessage(user_id="user1", text="/run 1")
        response = proc.process(msg)
        assert "Backup" in response.text

    def test_history_always_allowed(self, scheduler_mock: MagicMock) -> None:
        config = _make_config(allow_add=False, allow_edit=False, allow_delete=False)
        scheduler_mock.db.get_recent_executions.return_value = []
        with patch("src.bot.command_processor.Logger"):
            proc = CommandProcessor(scheduler=scheduler_mock, bot_config=config)
        msg = BotMessage(user_id="user1", text="/history")
        response = proc.process(msg)
        assert response.text == Messages.NO_HISTORY


# -- Conversation expiry tests --


class TestConversationExpiry:
    """Tests for conversation expiration."""

    def test_expired_conversation_is_cleaned_up(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """An expired conversation is cleaned up, so next command is treated fresh."""
        # Start an add wizard
        processor.process(BotMessage(user_id="user1", text="/add"))

        # Manually expire the conversation
        processor._conversations["user1"].expires_at = time.time() - 1

        # Next message should NOT continue the wizard
        response = processor.process(BotMessage(user_id="user1", text="backup.py"))
        assert response.text == Messages.UNKNOWN_COMMAND

    def test_non_expired_conversation_continues(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """A fresh conversation should continue normally."""
        processor.process(BotMessage(user_id="user1", text="/add"))

        # Continue wizard (conversation should still be active)
        response = processor.process(
            BotMessage(user_id="user1", text="C:/scripts/backup.py")
        )
        assert response.text == Messages.WIZARD_ADD_NAME


# -- Multiple users tests --


class TestMultipleUsers:
    """Tests for separate conversation state per user."""

    def test_separate_conversations_per_user(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """Different users have independent conversation states."""
        scheduler_mock.add_task.return_value = 1

        # User1 starts add wizard
        processor.process(BotMessage(user_id="user1", text="/add"))

        # User2 also starts add wizard
        processor.process(BotMessage(user_id="user2", text="/add"))

        # User1 continues - should be in their own wizard
        response1 = processor.process(
            BotMessage(user_id="user1", text="script1.py")
        )
        assert response1.text == Messages.WIZARD_ADD_NAME

        # User2 continues independently
        response2 = processor.process(
            BotMessage(user_id="user2", text="script2.py")
        )
        assert response2.text == Messages.WIZARD_ADD_NAME

    def test_user1_cancel_does_not_affect_user2(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """Cancelling one user's conversation doesn't affect another's."""
        # Both users start wizards
        processor.process(BotMessage(user_id="user1", text="/add"))
        processor.process(BotMessage(user_id="user2", text="/add"))

        # User1 cancels
        processor.process(BotMessage(user_id="user1", text="/cancel"))

        # User2 should still be in wizard
        response = processor.process(
            BotMessage(user_id="user2", text="script.py")
        )
        assert response.text == Messages.WIZARD_ADD_NAME

    def test_user_without_conversation_gets_command_handling(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """A user without active conversation gets normal command handling."""
        scheduler_mock.list_tasks.return_value = []

        # User1 starts a wizard
        processor.process(BotMessage(user_id="user1", text="/add"))

        # User2 (no conversation) does a /list
        response = processor.process(BotMessage(user_id="user2", text="/list"))
        assert response.text == Messages.NO_TASKS


# -- Command parsing edge cases --


class TestCommandParsing:
    """Tests for command parsing edge cases."""

    def test_command_case_insensitive(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        msg = BotMessage(user_id="user1", text="/HELP")
        response = processor.process(msg)
        assert response.text == Messages.HELP

    def test_command_with_leading_whitespace(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        msg = BotMessage(user_id="user1", text="  /help")
        response = processor.process(msg)
        assert response.text == Messages.HELP

    def test_command_with_trailing_whitespace(
        self, processor: CommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        msg = BotMessage(user_id="user1", text="/help  ")
        response = processor.process(msg)
        assert response.text == Messages.HELP

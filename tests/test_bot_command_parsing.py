"""Focused tests for bot command processor behavior."""

from bot_commander import BotMessage
from tests.bot_command_support import _make_task
from src.bot.command_processor import TaskCommandProcessor
from src.bot.constants import Messages
from src.bot.interaction_handler import BotInteractionHandler
from unittest.mock import MagicMock


class TestCommandParsing:
    """Tests for command parsing edge cases."""

    def test_command_case_insensitive(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        msg = BotMessage(user_id="user1", text="/HELP")
        response = processor.handle(msg)
        assert response.text == Messages.HELP

    def test_command_with_leading_whitespace(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        msg = BotMessage(user_id="user1", text="  /help")
        response = processor.handle(msg)
        assert response.text == Messages.HELP

    def test_command_with_trailing_whitespace(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        msg = BotMessage(user_id="user1", text="/help  ")
        response = processor.handle(msg)
        assert response.text == Messages.HELP



class TestCommandAliases:
    """Tests for command aliases and slash-optional input."""

    def test_list_alias_l(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """Short alias 'l' triggers list command."""
        scheduler_mock.list_tasks.return_value = []
        msg = BotMessage(user_id="user1", text="l")
        response = processor.handle(msg)
        assert response.text == Messages.NO_TASKS

    def test_list_alias_slash_l(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """Short alias '/l' triggers list command."""
        scheduler_mock.list_tasks.return_value = []
        msg = BotMessage(user_id="user1", text="/l")
        response = processor.handle(msg)
        assert response.text == Messages.NO_TASKS

    def test_help_alias_h(self, processor: TaskCommandProcessor) -> None:
        """Short alias 'h' triggers help command."""
        msg = BotMessage(user_id="user1", text="h")
        response = processor.handle(msg)
        assert response.text == Messages.HELP

    def test_history_alias_hi(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """Short alias 'hi' triggers history command."""
        scheduler_mock.db.get_recent_executions.return_value = []
        msg = BotMessage(user_id="user1", text="hi")
        response = processor.handle(msg)
        assert response.text == Messages.NO_HISTORY

    def test_run_alias_r_with_args(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """Short alias 'r 1' triggers run command with arguments."""
        task = _make_task(task_id=1, name="Backup")
        scheduler_mock.list_tasks.return_value = [task]
        scheduler_mock.run_task.return_value = True
        msg = BotMessage(user_id="user1", text="r 1")
        response = processor.handle(msg)
        assert response.text == Messages.TASK_RUNNING.format("Backup", 1)

    def test_add_alias_a(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """Short alias 'a' triggers add wizard."""
        msg = BotMessage(user_id="user1", text="a")
        response = processor.handle(msg)
        assert response.text == Messages.WIZARD_ADD_START

    def test_edit_alias_e(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """Short alias 'e 1' triggers edit wizard."""
        task = _make_task(task_id=1, name="Backup")
        scheduler_mock.list_tasks.return_value = [task]
        msg = BotMessage(user_id="user1", text="e 1")
        response = processor.handle(msg)
        assert "Backup" in response.text

    def test_delete_alias_d(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """Short alias 'd 1' triggers delete confirmation."""
        task = _make_task(task_id=1, name="Backup")
        scheduler_mock.list_tasks.return_value = [task]
        msg = BotMessage(user_id="user1", text="d 1")
        response = processor.handle(msg)
        assert "Backup" in response.text
        assert "yes" in response.text.lower()

    def test_cancel_alias_c(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """Short alias 'c' cancels active conversation."""
        # Start a wizard first
        processor.handle(BotMessage(user_id="user1", text="/add"))
        # Cancel with alias
        response = processor.handle(BotMessage(user_id="user1", text="c"))
        assert response.text == Messages.OPERATION_CANCELLED

    def test_command_without_slash(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """Full command name without slash prefix works."""
        scheduler_mock.list_tasks.return_value = []
        msg = BotMessage(user_id="user1", text="list")
        response = processor.handle(msg)
        assert response.text == Messages.NO_TASKS

    def test_alias_case_insensitive(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """Aliases are case insensitive."""
        scheduler_mock.list_tasks.return_value = []
        msg = BotMessage(user_id="user1", text="L")
        response = processor.handle(msg)
        assert response.text == Messages.NO_TASKS

    def test_command_without_slash_with_args(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """Full command without slash preserves arguments."""
        scheduler_mock.db.get_recent_executions.return_value = []
        msg = BotMessage(user_id="user1", text="history 5")
        processor.handle(msg)
        scheduler_mock.db.get_recent_executions.assert_called_once_with(5)



class TestCancelDuringInteractiveHandler:
    """Tests for /cancel and exit during an active interactive script prompt."""

    def test_cancel_during_active_handler_returns_message(
        self, processor: TaskCommandProcessor
    ) -> None:
        """Sending /cancel while an interactive handler is active returns cancel message."""
        notifier = MagicMock()
        processor.set_notifier(notifier)
        handler = BotInteractionHandler(
            user_id="user1", notifier=notifier, timeout=30
        )
        processor._active_handlers["user1"] = handler

        response = processor.handle(BotMessage(user_id="user1", text="/cancel"))
        assert response.text == Messages.INTERACTION_CANCELLED

    def test_cancel_during_active_handler_removes_handler(
        self, processor: TaskCommandProcessor
    ) -> None:
        """After /cancel, the active handler is removed."""
        notifier = MagicMock()
        processor.set_notifier(notifier)
        handler = BotInteractionHandler(
            user_id="user1", notifier=notifier, timeout=30
        )
        processor._active_handlers["user1"] = handler

        processor.handle(BotMessage(user_id="user1", text="/cancel"))
        assert "user1" not in processor._active_handlers

    def test_cancel_during_active_handler_calls_cancel(
        self, processor: TaskCommandProcessor
    ) -> None:
        """Sending /cancel calls handler.cancel() to unblock the waiting prompt."""
        notifier = MagicMock()
        processor.set_notifier(notifier)
        handler = BotInteractionHandler(
            user_id="user1", notifier=notifier, timeout=30
        )
        processor._active_handlers["user1"] = handler

        processor.handle(BotMessage(user_id="user1", text="/cancel"))
        # After cancel, the handler's cancelled flag should be set
        assert handler._cancelled is True

    def test_exit_during_active_handler_cancels(
        self, processor: TaskCommandProcessor
    ) -> None:
        """Typing 'exit' during an active interactive handler triggers cancellation."""
        notifier = MagicMock()
        processor.set_notifier(notifier)
        handler = BotInteractionHandler(
            user_id="user1", notifier=notifier, timeout=30
        )
        processor._active_handlers["user1"] = handler

        response = processor.handle(BotMessage(user_id="user1", text="exit"))
        assert response.text == Messages.INTERACTION_CANCELLED
        assert "user1" not in processor._active_handlers

    def test_cancel_alias_c_during_active_handler(
        self, processor: TaskCommandProcessor
    ) -> None:
        """Short alias 'c' cancels during active interactive handler."""
        notifier = MagicMock()
        processor.set_notifier(notifier)
        handler = BotInteractionHandler(
            user_id="user1", notifier=notifier, timeout=30
        )
        processor._active_handlers["user1"] = handler

        response = processor.handle(BotMessage(user_id="user1", text="c"))
        assert response.text == Messages.INTERACTION_CANCELLED


"""Focused tests for bot command processor behavior."""

from bot_commander import BotMessage
from tests.bot_command_support import _make_execution, _make_task
from src.bot.command_processor import TaskCommandProcessor
from src.bot.constants import Messages
from unittest.mock import MagicMock


class TestHelpCommand:
    """Tests for the /help command."""

    def test_help_returns_help_text(self, processor: TaskCommandProcessor) -> None:
        msg = BotMessage(user_id="user1", text="/help")
        response = processor.handle(msg)
        assert response.text == Messages.HELP

    def test_help_with_extra_args_still_works(
        self, processor: TaskCommandProcessor
    ) -> None:
        msg = BotMessage(user_id="user1", text="/help something")
        response = processor.handle(msg)
        assert response.text == Messages.HELP



class TestListCommand:
    """Tests for the /list command."""

    def test_list_returns_formatted_tasks(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        tasks = [
            _make_task(task_id=1, name="Backup"),
            _make_task(task_id=2, name="Cleanup"),
        ]
        scheduler_mock.list_tasks.return_value = tasks
        msg = BotMessage(user_id="user1", text="/list")
        response = processor.handle(msg)
        assert "Backup" in response.text
        assert "Cleanup" in response.text

    def test_list_empty_returns_no_tasks(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        scheduler_mock.list_tasks.return_value = []
        msg = BotMessage(user_id="user1", text="/list")
        response = processor.handle(msg)
        assert response.text == Messages.NO_TASKS

    def test_list_with_filter(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        tasks = [
            _make_task(task_id=1, name="Backup"),
            _make_task(task_id=2, name="Cleanup"),
        ]
        scheduler_mock.list_tasks.return_value = tasks
        msg = BotMessage(user_id="user1", text="/list backup")
        response = processor.handle(msg)
        assert "Backup" in response.text
        assert "Cleanup" not in response.text

    def test_list_filter_case_insensitive(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        tasks = [
            _make_task(task_id=1, name="Backup"),
            _make_task(task_id=2, name="Cleanup"),
        ]
        scheduler_mock.list_tasks.return_value = tasks
        msg = BotMessage(user_id="user1", text="/list BACKUP")
        response = processor.handle(msg)
        assert "Backup" in response.text
        assert "Cleanup" not in response.text

    def test_list_filter_no_match_returns_no_tasks(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        tasks = [_make_task(task_id=1, name="Backup")]
        scheduler_mock.list_tasks.return_value = tasks
        msg = BotMessage(user_id="user1", text="/list nonexistent")
        response = processor.handle(msg)
        assert response.text == Messages.NO_TASKS



class TestHistoryCommand:
    """Tests for the /history command."""

    def test_history_default_limit(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        executions = [_make_execution()]
        scheduler_mock.db.get_recent_executions.return_value = executions
        msg = BotMessage(user_id="user1", text="/history")
        response = processor.handle(msg)
        scheduler_mock.db.get_recent_executions.assert_called_once_with(10)
        assert "Backup Script" in response.text

    def test_history_custom_limit(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        scheduler_mock.db.get_recent_executions.return_value = []
        msg = BotMessage(user_id="user1", text="/history 5")
        processor.handle(msg)
        scheduler_mock.db.get_recent_executions.assert_called_once_with(5)

    def test_history_invalid_limit_uses_default(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        scheduler_mock.db.get_recent_executions.return_value = []
        msg = BotMessage(user_id="user1", text="/history abc")
        processor.handle(msg)
        scheduler_mock.db.get_recent_executions.assert_called_once_with(10)

    def test_history_empty_returns_no_history(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        scheduler_mock.db.get_recent_executions.return_value = []
        msg = BotMessage(user_id="user1", text="/history")
        response = processor.handle(msg)
        assert response.text == Messages.NO_HISTORY


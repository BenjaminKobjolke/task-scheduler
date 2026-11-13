"""Focused tests for bot command processor behavior."""

from bot_commander import BotMessage
from tests.bot_command_support import _make_config, _make_task
from src.bot.command_processor import TaskCommandProcessor
from src.bot.constants import Commands
from src.bot.constants import Messages
from unittest.mock import MagicMock
from unittest.mock import patch


class TestDisabledCommands:
    """Tests for commands disabled by configuration."""

    def test_add_disabled(self, scheduler_mock: MagicMock) -> None:
        config = _make_config(allow_add=False)
        with patch("src.bot.command_processor.Logger"):
            proc = TaskCommandProcessor(scheduler=scheduler_mock, bot_config=config)
        msg = BotMessage(user_id="user1", text="/add")
        response = proc.handle(msg)
        assert response.text == Messages.COMMAND_DISABLED.format(Commands.ADD)

    def test_edit_disabled(self, scheduler_mock: MagicMock) -> None:
        config = _make_config(allow_edit=False)
        with patch("src.bot.command_processor.Logger"):
            proc = TaskCommandProcessor(scheduler=scheduler_mock, bot_config=config)
        msg = BotMessage(user_id="user1", text="/edit 1")
        response = proc.handle(msg)
        assert response.text == Messages.COMMAND_DISABLED.format(Commands.EDIT)

    def test_delete_disabled(self, scheduler_mock: MagicMock) -> None:
        config = _make_config(allow_delete=False)
        with patch("src.bot.command_processor.Logger"):
            proc = TaskCommandProcessor(scheduler=scheduler_mock, bot_config=config)
        msg = BotMessage(user_id="user1", text="/delete 1")
        response = proc.handle(msg)
        assert response.text == Messages.COMMAND_DISABLED.format(Commands.DELETE)

    def test_list_always_allowed(self, scheduler_mock: MagicMock) -> None:
        config = _make_config(allow_add=False, allow_edit=False, allow_delete=False)
        scheduler_mock.list_tasks.return_value = []
        with patch("src.bot.command_processor.Logger"):
            proc = TaskCommandProcessor(scheduler=scheduler_mock, bot_config=config)
        msg = BotMessage(user_id="user1", text="/list")
        response = proc.handle(msg)
        assert response.text == Messages.NO_TASKS

    def test_help_always_allowed(self, scheduler_mock: MagicMock) -> None:
        config = _make_config(allow_add=False, allow_edit=False, allow_delete=False)
        with patch("src.bot.command_processor.Logger"):
            proc = TaskCommandProcessor(scheduler=scheduler_mock, bot_config=config)
        msg = BotMessage(user_id="user1", text="/help")
        response = proc.handle(msg)
        assert response.text == Messages.HELP

    def test_run_always_allowed(self, scheduler_mock: MagicMock) -> None:
        config = _make_config(allow_add=False, allow_edit=False, allow_delete=False)
        scheduler_mock.list_tasks.return_value = [_make_task(task_id=1, name="Backup")]
        scheduler_mock.run_task.return_value = True
        with patch("src.bot.command_processor.Logger"):
            proc = TaskCommandProcessor(scheduler=scheduler_mock, bot_config=config)
        msg = BotMessage(user_id="user1", text="/run 1")
        response = proc.handle(msg)
        assert response.text == Messages.TASK_RUNNING.format("Backup", 1)

    def test_history_always_allowed(self, scheduler_mock: MagicMock) -> None:
        config = _make_config(allow_add=False, allow_edit=False, allow_delete=False)
        scheduler_mock.db.get_recent_executions.return_value = []
        with patch("src.bot.command_processor.Logger"):
            proc = TaskCommandProcessor(scheduler=scheduler_mock, bot_config=config)
        msg = BotMessage(user_id="user1", text="/history")
        response = proc.handle(msg)
        assert response.text == Messages.NO_HISTORY


"""Focused tests for bot command processor behavior."""

from bot_commander import BotMessage
from tests.bot_command_support import _make_task
from src.bot.command_processor import TaskCommandProcessor
from src.bot.constants import Commands
from src.bot.constants import Messages
from src.bot.interaction_handler import BotScriptOutput
from unittest.mock import MagicMock
import threading
import time


class TestRunCommand:
    """Tests for the /run command (async behavior)."""

    def test_run_returns_immediate_ack(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """Run command returns immediate 'Running task...' acknowledgment."""
        task = _make_task(task_id=1, name="Backup")
        scheduler_mock.list_tasks.return_value = [task]
        # Block run_task so the thread doesn't finish before we assert
        scheduler_mock.run_task.side_effect = lambda *a, **kw: time.sleep(0.5)
        msg = BotMessage(user_id="user1", text="/run 1")
        response = processor.handle(msg)
        assert response.text == Messages.TASK_RUNNING.format("Backup", 1)

    def test_run_spawns_background_thread(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """Run command spawns a daemon thread for task execution."""
        task = _make_task(task_id=1, name="Backup")
        scheduler_mock.list_tasks.return_value = [task]
        done = threading.Event()
        scheduler_mock.run_task.side_effect = lambda *a, **kw: done.set() or True
        processor.handle(BotMessage(user_id="user1", text="/run 1"))
        assert done.wait(timeout=2), "Background thread did not run"

    def test_run_async_success_notifies(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """After successful execution, notifier is called with success message."""
        notifier = MagicMock()
        processor.set_notifier(notifier)
        task = _make_task(task_id=1, name="Backup")
        scheduler_mock.list_tasks.return_value = [task]
        scheduler_mock.run_task.return_value = True
        processor.handle(BotMessage(user_id="user1", text="/run 1"))
        # Wait for thread to complete
        time.sleep(0.5)
        notifier.assert_called_once_with(
            "user1", Messages.TASK_EXECUTED_SUCCESS.format("Backup", 1)
        )

    def test_run_async_failure_notifies(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """After failed execution, notifier is called with failure message."""
        notifier = MagicMock()
        processor.set_notifier(notifier)
        task = _make_task(task_id=1, name="Backup")
        scheduler_mock.list_tasks.return_value = [task]
        scheduler_mock.run_task.return_value = False
        processor.handle(BotMessage(user_id="user1", text="/run 1"))
        time.sleep(0.5)
        notifier.assert_called_once_with(
            "user1", Messages.TASK_EXECUTED_FAILURE.format("Backup", 1)
        )

    def test_run_async_exception_notifies(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """After exception, notifier is called with error message."""
        notifier = MagicMock()
        processor.set_notifier(notifier)
        task = _make_task(task_id=1, name="Backup")
        scheduler_mock.list_tasks.return_value = [task]
        scheduler_mock.run_task.side_effect = RuntimeError("Connection lost")
        processor.handle(BotMessage(user_id="user1", text="/run 1"))
        time.sleep(0.5)
        notifier.assert_called_once_with(
            "user1", Messages.TASK_EXECUTION_ERROR.format(1, "Connection lost")
        )

    def test_run_no_notifier_does_not_crash(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """Without a notifier set, async execution completes without crash."""
        task = _make_task(task_id=1, name="Backup")
        scheduler_mock.list_tasks.return_value = [task]
        scheduler_mock.run_task.return_value = True
        processor.handle(BotMessage(user_id="user1", text="/run 1"))
        time.sleep(0.5)
        # No crash = success

    def test_run_invalid_id_not_a_number(self, processor: TaskCommandProcessor) -> None:
        msg = BotMessage(user_id="user1", text="/run abc")
        response = processor.handle(msg)
        assert response.text == Messages.INVALID_TASK_ID.format(Commands.RUN)

    def test_run_missing_id(self, processor: TaskCommandProcessor) -> None:
        msg = BotMessage(user_id="user1", text="/run")
        response = processor.handle(msg)
        assert response.text == Messages.INVALID_TASK_ID.format(Commands.RUN)

    def test_run_nonexistent_task_returns_ack_with_fallback_name(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """When task not in list, uses fallback name but still spawns thread."""
        scheduler_mock.list_tasks.return_value = []
        scheduler_mock.run_task.side_effect = ValueError("Task with ID 99 not found")
        notifier = MagicMock()
        processor.set_notifier(notifier)
        msg = BotMessage(user_id="user1", text="/run 99")
        response = processor.handle(msg)
        assert response.text == Messages.TASK_RUNNING.format("Task 99", 99)
        time.sleep(0.5)
        # ValueError is caught as str(e)
        notifier.assert_called_once()
        call_text = notifier.call_args[0][1]
        assert "99" in call_text

    def test_run_async_passes_bot_script_output(
        self, processor: TaskCommandProcessor, scheduler_mock: MagicMock
    ) -> None:
        """_run_task_async passes a BotScriptOutput to scheduler.run_task()."""
        notifier = MagicMock()
        processor.set_notifier(notifier)
        task = _make_task(task_id=1, name="Backup")
        scheduler_mock.list_tasks.return_value = [task]
        scheduler_mock.run_task.return_value = True
        processor.handle(BotMessage(user_id="user1", text="/run 1"))
        time.sleep(0.5)
        scheduler_mock.run_task.assert_called_once()
        call_kwargs = scheduler_mock.run_task.call_args
        script_output = call_kwargs.kwargs.get("script_output")
        assert script_output is not None
        assert isinstance(script_output, BotScriptOutput)


"""Tests for TaskScheduler.run_task() return value."""
from unittest.mock import MagicMock, patch
import pytest
from src.scheduler import TaskScheduler
from src.script_runner import ScriptRunner
from src.database import Database
from src.status_page import StatusPage
from src.constants import TaskTypes


@pytest.fixture
def mock_scheduler():
    """Create a TaskScheduler with mocked dependencies."""
    with patch.object(TaskScheduler, "__init__", lambda self: None):
        scheduler = TaskScheduler()
        scheduler.logger = MagicMock()
        scheduler.script_runner = MagicMock(spec=ScriptRunner)
        scheduler.db = MagicMock(spec=Database)
        scheduler.status_page = MagicMock(spec=StatusPage)
        scheduler.scheduler = MagicMock()
        scheduler._task_checksums = {}
        return scheduler


def _make_task(
    task_id: int = 1,
    name: str = "Test Task",
    script_path: str = "/path/to/script.py",
    arguments: list = None,
    task_type: str = TaskTypes.SCRIPT,
    command: str = None,
    start_time: str = None,
) -> dict:
    """Helper to create a task dictionary matching database format."""
    return {
        "id": task_id,
        "name": name,
        "script_path": script_path,
        "arguments": arguments or [],
        "interval": 5,
        "task_type": task_type,
        "command": command,
        "start_time": start_time,
    }


class TestRunTaskReturnValue:
    """Tests verifying run_task returns a bool from _process_job."""

    def test_run_task_returns_true_on_success(self, mock_scheduler):
        """run_task should return True when script execution succeeds."""
        task = _make_task()
        mock_scheduler.db.get_all_tasks.return_value = [task]
        mock_scheduler.script_runner.run_script.return_value = True

        result = mock_scheduler.run_task(1)

        assert result is True

    def test_run_task_returns_false_on_failure(self, mock_scheduler):
        """run_task should return False when script execution fails."""
        task = _make_task()
        mock_scheduler.db.get_all_tasks.return_value = [task]
        mock_scheduler.script_runner.run_script.return_value = False

        result = mock_scheduler.run_task(1)

        assert result is False

    def test_run_task_raises_for_nonexistent_task(self, mock_scheduler):
        """run_task should raise ValueError when task_id does not exist."""
        mock_scheduler.db.get_all_tasks.return_value = []

        with pytest.raises(ValueError, match="Task with ID 999 not found"):
            mock_scheduler.run_task(999)

    def test_run_task_uv_command_returns_true(self, mock_scheduler):
        """run_task should return True for a successful uv_command task."""
        task = _make_task(
            task_type=TaskTypes.UV_COMMAND,
            command="my-cmd",
            script_path="/path/to/project",
        )
        mock_scheduler.db.get_all_tasks.return_value = [task]
        mock_scheduler.script_runner.run_uv_command.return_value = True

        result = mock_scheduler.run_task(1)

        assert result is True

    def test_run_task_uv_command_returns_false(self, mock_scheduler):
        """run_task should return False for a failed uv_command task."""
        task = _make_task(
            task_type=TaskTypes.UV_COMMAND,
            command="my-cmd",
            script_path="/path/to/project",
        )
        mock_scheduler.db.get_all_tasks.return_value = [task]
        mock_scheduler.script_runner.run_uv_command.return_value = False

        result = mock_scheduler.run_task(1)

        assert result is False


class TestProcessJobReturnValue:
    """Tests verifying _process_job returns a bool."""

    def test_process_job_returns_true_on_success(self, mock_scheduler):
        """_process_job should return True when script succeeds."""
        mock_scheduler.script_runner.run_script.return_value = True

        result = mock_scheduler._process_job(
            task_id=1,
            name="Test",
            script_path="/path/to/script.py",
            arguments=[],
        )

        assert result is True

    def test_process_job_returns_false_on_failure(self, mock_scheduler):
        """_process_job should return False when script fails."""
        mock_scheduler.script_runner.run_script.return_value = False

        result = mock_scheduler._process_job(
            task_id=1,
            name="Test",
            script_path="/path/to/script.py",
            arguments=[],
        )

        assert result is False

    def test_process_job_uv_command_returns_success(self, mock_scheduler):
        """_process_job should return True for successful uv_command."""
        mock_scheduler.script_runner.run_uv_command.return_value = True

        result = mock_scheduler._process_job(
            task_id=1,
            name="Test UV",
            script_path="/path/to/project",
            arguments=[],
            task_type=TaskTypes.UV_COMMAND,
            command="my-cmd",
        )

        assert result is True

    def test_process_job_records_execution(self, mock_scheduler):
        """_process_job should still record execution to database."""
        mock_scheduler.script_runner.run_script.return_value = True

        mock_scheduler._process_job(
            task_id=1,
            name="Test",
            script_path="/path/to/script.py",
            arguments=[],
        )

        mock_scheduler.db.add_task_execution.assert_called_once_with(1, True)

    def test_process_job_updates_status_page(self, mock_scheduler):
        """_process_job should still update the status page."""
        mock_scheduler.script_runner.run_script.return_value = True

        mock_scheduler._process_job(
            task_id=1,
            name="Test",
            script_path="/path/to/script.py",
            arguments=[],
        )

        mock_scheduler.status_page.update.assert_called_once()

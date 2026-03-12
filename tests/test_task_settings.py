"""Tests for task settings commands (rename, etc.)."""

import pytest
from unittest.mock import MagicMock, patch

from src.cli_output import CliOutput
from src.constants import TaskTypes
from src.scheduler import TaskScheduler
from src.commands.task_settings import handle_rename


@pytest.fixture
def mock_scheduler():
    """Create a mock TaskScheduler."""
    return MagicMock(spec=TaskScheduler)


@pytest.fixture
def mock_cli():
    """Create a mock CliOutput."""
    return MagicMock(spec=CliOutput)


@pytest.fixture
def sample_task():
    """A sample task dict as returned by list_tasks()."""
    return {
        "id": 5,
        "name": "Old Name",
        "script_path": "C:\\scripts\\test.py",
        "interval": 10,
        "arguments": ["--verbose"],
        "task_type": TaskTypes.SCRIPT,
        "command": None,
        "start_time": "09:00",
    }


class TestHandleRename:
    """Tests for handle_rename()."""

    def test_rename_succeeds(self, mock_scheduler, mock_cli, sample_task):
        """Rename calls edit_task with the new name and all other fields unchanged."""
        mock_scheduler.list_tasks.return_value = [sample_task]

        handle_rename(mock_scheduler, mock_cli, 5, "New Name")

        mock_scheduler.edit_task.assert_called_once_with(
            task_id=5,
            name="New Name",
            script_path="C:\\scripts\\test.py",
            interval=10,
            arguments=["--verbose"],
            task_type=TaskTypes.SCRIPT,
            command=None,
            start_time="09:00",
            launch_new_process=False,
        )
        mock_cli.info.assert_called_once_with(
            "Task 'Old Name' (ID: 5) renamed to 'New Name'"
        )

    def test_task_not_found_exits(self, mock_scheduler, mock_cli):
        """Exits with error when task ID does not exist."""
        mock_scheduler.list_tasks.return_value = []

        with pytest.raises(SystemExit) as exc_info:
            handle_rename(mock_scheduler, mock_cli, 99, "New Name")

        assert exc_info.value.code == 1
        mock_cli.error.assert_called_once_with("No task found with ID 99")

    def test_edit_task_error_exits(self, mock_scheduler, mock_cli, sample_task):
        """Exits with error when edit_task raises ValueError."""
        mock_scheduler.list_tasks.return_value = [sample_task]
        mock_scheduler.edit_task.side_effect = ValueError("Name already exists")

        with pytest.raises(SystemExit) as exc_info:
            handle_rename(mock_scheduler, mock_cli, 5, "New Name")

        assert exc_info.value.code == 1
        mock_cli.error.assert_called_once_with("Name already exists")

    def test_prompts_for_name_when_not_provided(
        self, mock_scheduler, mock_cli, sample_task
    ):
        """Prompts interactively when new_name is None."""
        mock_scheduler.list_tasks.return_value = [sample_task]

        with patch("src.commands.task_settings.PromptSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.prompt.return_value = "Prompted Name"

            handle_rename(mock_scheduler, mock_cli, 5)

        mock_scheduler.edit_task.assert_called_once_with(
            task_id=5,
            name="Prompted Name",
            script_path="C:\\scripts\\test.py",
            interval=10,
            arguments=["--verbose"],
            task_type=TaskTypes.SCRIPT,
            command=None,
            start_time="09:00",
            launch_new_process=False,
        )
        mock_cli.info.assert_any_call("\nTask: Old Name (ID: 5)")

    def test_prompt_empty_keeps_current_name(
        self, mock_scheduler, mock_cli, sample_task
    ):
        """Empty prompt input keeps the current name."""
        mock_scheduler.list_tasks.return_value = [sample_task]

        with patch("src.commands.task_settings.PromptSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.prompt.return_value = ""

            handle_rename(mock_scheduler, mock_cli, 5)

        mock_scheduler.edit_task.assert_called_once_with(
            task_id=5,
            name="Old Name",
            script_path="C:\\scripts\\test.py",
            interval=10,
            arguments=["--verbose"],
            task_type=TaskTypes.SCRIPT,
            command=None,
            start_time="09:00",
            launch_new_process=False,
        )

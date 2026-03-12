"""Tests for launch_new_process feature."""

import os
import subprocess
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from bot_commander import CONFIRMED_SENTINEL

from src.bot.conversation import AddWizard, EditWizard
from src.bot.formatters import (
    format_add_summary,
    format_task_detail,
    format_task_list_compact,
)
from src.constants import TaskTypes, Database as DbConstants
from src.database import Database
from src.formatters import format_task_list
from src.scheduler import TaskScheduler
from src.script_runner import ScriptRunner
from src.status_page import StatusPage


# ---------------------------------------------------------------------------
# Database tests
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = os.path.join(tmpdir, "test.sqlite")
        db = Database(db_path)
        yield db


class TestDatabaseLaunchNewProcess:
    """Tests for launch_new_process column in database."""

    def test_add_task_default_launch_new_process_false(self, temp_db):
        """Default launch_new_process should be False."""
        temp_db.add_task("Test", "/path/script.py", 0)
        tasks = temp_db.get_all_tasks()
        assert tasks[0]["launch_new_process"] is False

    def test_add_task_with_launch_new_process_true(self, temp_db):
        """Should store launch_new_process=True."""
        temp_db.add_task("Test", "/path/script.py", 0, launch_new_process=True)
        tasks = temp_db.get_all_tasks()
        assert tasks[0]["launch_new_process"] is True

    def test_edit_task_sets_launch_new_process(self, temp_db):
        """edit_task should update launch_new_process."""
        task_id = temp_db.add_task("Test", "/path/script.py", 0)
        temp_db.edit_task(
            task_id, "Test", "/path/script.py", 0, launch_new_process=True
        )
        tasks = temp_db.get_all_tasks()
        assert tasks[0]["launch_new_process"] is True

    def test_edit_task_clears_launch_new_process(self, temp_db):
        """edit_task should be able to clear launch_new_process."""
        task_id = temp_db.add_task(
            "Test", "/path/script.py", 0, launch_new_process=True
        )
        temp_db.edit_task(
            task_id, "Test", "/path/script.py", 0, launch_new_process=False
        )
        tasks = temp_db.get_all_tasks()
        assert tasks[0]["launch_new_process"] is False

    def test_migration_adds_column(self, temp_db):
        """Migration should add launch_new_process column to existing databases."""
        import sqlite3

        with sqlite3.connect(temp_db.db_path) as conn:
            cursor = conn.execute("PRAGMA table_info(tasks)")
            columns = [row[1] for row in cursor.fetchall()]
            assert DbConstants.COL_LAUNCH_NEW_PROCESS in columns


# ---------------------------------------------------------------------------
# ScriptRunner tests
# ---------------------------------------------------------------------------


class TestScriptRunnerLaunchInNewConsole:
    """Tests for launch_in_new_console method."""

    def test_launch_script_uses_popen_with_create_new_console(self):
        """launch_in_new_console should use Popen with CREATE_NEW_CONSOLE."""
        runner = ScriptRunner()
        script_path = os.path.abspath("C:/scripts/test.py")
        script_dir = os.path.dirname(script_path)

        with patch.object(runner, "_is_uv_project", return_value=False):
            with patch.object(runner, "_activate_venv") as mock_venv:
                mock_venv.return_value = os.path.join(
                    script_dir, "venv", "Scripts", "activate"
                )
                with patch("os.path.exists", return_value=True):
                    with patch("subprocess.Popen") as mock_popen:
                        mock_popen.return_value = MagicMock()
                        result = runner.launch_in_new_console(
                            script_path, [], TaskTypes.SCRIPT, None
                        )

                        assert result is True
                        mock_popen.assert_called_once()
                        call_kwargs = mock_popen.call_args
                        assert (
                            call_kwargs.kwargs.get("creationflags")
                            == subprocess.CREATE_NEW_CONSOLE
                        )

    def test_launch_batch_file_uses_create_new_console(self):
        """launch_in_new_console should handle batch files."""
        runner = ScriptRunner()
        script_path = "C:/scripts/test.bat"

        with patch("os.path.exists", return_value=True):
            with patch("subprocess.Popen") as mock_popen:
                mock_popen.return_value = MagicMock()
                result = runner.launch_in_new_console(
                    script_path, [], TaskTypes.SCRIPT, None
                )

                assert result is True
                mock_popen.assert_called_once()
                call_kwargs = mock_popen.call_args
                assert (
                    call_kwargs.kwargs.get("creationflags")
                    == subprocess.CREATE_NEW_CONSOLE
                )

    def test_launch_uv_command_uses_create_new_console(self):
        """launch_in_new_console should handle uv commands."""
        runner = ScriptRunner()
        project_dir = "C:/projects/myproject"

        with patch("os.path.isdir", return_value=True):
            with patch.object(runner, "_is_uv_project", return_value=True):
                with patch("subprocess.Popen") as mock_popen:
                    mock_popen.return_value = MagicMock()
                    result = runner.launch_in_new_console(
                        project_dir, ["--verbose"], TaskTypes.UV_COMMAND, "my-command"
                    )

                    assert result is True
                    mock_popen.assert_called_once()
                    call_kwargs = mock_popen.call_args
                    assert (
                        call_kwargs.kwargs.get("creationflags")
                        == subprocess.CREATE_NEW_CONSOLE
                    )

    def test_launch_returns_false_on_exception(self):
        """launch_in_new_console should return False on errors."""
        runner = ScriptRunner()

        with patch("os.path.exists", return_value=True):
            with patch("subprocess.Popen", side_effect=OSError("fail")):
                result = runner.launch_in_new_console(
                    "C:/scripts/test.bat", [], TaskTypes.SCRIPT, None
                )
                assert result is False


# ---------------------------------------------------------------------------
# Scheduler tests
# ---------------------------------------------------------------------------


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


class TestRunTaskLaunchNewProcess:
    """Tests for run_task routing based on launch_new_process flag."""

    def test_run_task_launches_in_new_console_when_flag_set(self, mock_scheduler):
        """run_task should use launch_in_new_console when launch_new_process=True."""
        task = {
            "id": 1,
            "name": "Manual Task",
            "script_path": "/path/to/script.py",
            "arguments": [],
            "interval": 0,
            "task_type": TaskTypes.SCRIPT,
            "command": None,
            "start_time": None,
            "launch_new_process": True,
        }
        mock_scheduler.db.get_all_tasks.return_value = [task]
        mock_scheduler.script_runner.launch_in_new_console.return_value = True

        result = mock_scheduler.run_task(1)

        assert result is True
        mock_scheduler.script_runner.launch_in_new_console.assert_called_once()
        mock_scheduler.db.add_task_execution.assert_called_once_with(1, True)
        # Should NOT call _process_job / run_script
        mock_scheduler.script_runner.run_script.assert_not_called()

    def test_run_task_uses_process_job_when_flag_not_set(self, mock_scheduler):
        """run_task should use _process_job when launch_new_process=False."""
        task = {
            "id": 1,
            "name": "Manual Task",
            "script_path": "/path/to/script.py",
            "arguments": [],
            "interval": 0,
            "task_type": TaskTypes.SCRIPT,
            "command": None,
            "start_time": None,
            "launch_new_process": False,
        }
        mock_scheduler.db.get_all_tasks.return_value = [task]
        mock_scheduler.script_runner.run_script.return_value = True

        result = mock_scheduler.run_task(1)

        assert result is True
        mock_scheduler.script_runner.run_script.assert_called_once()
        mock_scheduler.script_runner.launch_in_new_console.assert_not_called()

    def test_run_task_records_history_for_new_console_launch(self, mock_scheduler):
        """run_task should record execution history even for new console launches."""
        task = {
            "id": 42,
            "name": "Detached Task",
            "script_path": "/path/to/script.py",
            "arguments": ["--arg"],
            "interval": 0,
            "task_type": TaskTypes.SCRIPT,
            "command": None,
            "start_time": None,
            "launch_new_process": True,
        }
        mock_scheduler.db.get_all_tasks.return_value = [task]
        mock_scheduler.script_runner.launch_in_new_console.return_value = True

        mock_scheduler.run_task(42)

        mock_scheduler.db.add_task_execution.assert_called_once_with(42, True)


class TestEditTaskClearsLaunchNewProcess:
    """Tests for edit_task clearing launch_new_process when interval changes."""

    def test_edit_task_clears_launch_when_interval_nonzero(self, mock_scheduler):
        """edit_task should force launch_new_process=False when interval != 0."""
        mock_scheduler.scheduler.running = True
        mock_scheduler.db.edit_task.return_value = True
        mock_scheduler.db.get_last_execution_per_task.return_value = {}

        mock_scheduler.edit_task(
            task_id=1,
            name="Task",
            script_path="/path/script.py",
            interval=5,
            launch_new_process=True,
        )

        # Should have been called with launch_new_process=False
        db_call = mock_scheduler.db.edit_task.call_args
        assert db_call.kwargs.get("launch_new_process") is False or (
            len(db_call.args) > 8 and db_call.args[8] is False
        )

    def test_edit_task_preserves_launch_when_interval_zero(self, mock_scheduler):
        """edit_task should preserve launch_new_process when interval == 0."""
        mock_scheduler.scheduler.running = True
        mock_scheduler.db.edit_task.return_value = True

        mock_scheduler.edit_task(
            task_id=1,
            name="Task",
            script_path="/path/script.py",
            interval=0,
            launch_new_process=True,
        )

        db_call = mock_scheduler.db.edit_task.call_args
        assert db_call.kwargs.get("launch_new_process") is True


class TestTaskChecksumIncludesLaunchNewProcess:
    """Tests for _get_task_checksum including launch_new_process."""

    def test_checksum_differs_with_launch_new_process(self, mock_scheduler):
        """Checksum should change when launch_new_process changes."""
        task_a = {
            "name": "Task",
            "script_path": "/path/script.py",
            "interval": 0,
            "start_time": None,
            "arguments": [],
            "task_type": TaskTypes.SCRIPT,
            "command": None,
            "launch_new_process": False,
        }
        task_b = dict(task_a, launch_new_process=True)

        checksum_a = mock_scheduler._get_task_checksum(task_a)
        checksum_b = mock_scheduler._get_task_checksum(task_b)

        assert checksum_a != checksum_b


# ---------------------------------------------------------------------------
# CLI Formatter tests
# ---------------------------------------------------------------------------


class TestFormatTaskListLaunchNewProcess:
    """Tests for format_task_list showing launch mode."""

    def test_shows_launch_mode_when_true(self):
        """format_task_list should show 'Launch mode: new console' when true."""
        tasks = [
            {
                "id": 1,
                "name": "Manual Task",
                "script_path": "/path/to/script.py",
                "arguments": [],
                "interval": 0,
                "task_type": TaskTypes.SCRIPT,
                "command": None,
                "start_time": None,
                "launch_new_process": True,
                "last_run_time": None,
                "last_run_success": None,
                "next_run_time": None,
            }
        ]
        result = format_task_list(tasks, show_next_run=False)
        assert "Launch mode: new console" in result

    def test_no_launch_mode_when_false(self):
        """format_task_list should NOT show launch mode when false."""
        tasks = [
            {
                "id": 1,
                "name": "Manual Task",
                "script_path": "/path/to/script.py",
                "arguments": [],
                "interval": 0,
                "task_type": TaskTypes.SCRIPT,
                "command": None,
                "start_time": None,
                "launch_new_process": False,
                "last_run_time": None,
                "last_run_success": None,
                "next_run_time": None,
            }
        ]
        result = format_task_list(tasks, show_next_run=False)
        assert "Launch mode" not in result


# ---------------------------------------------------------------------------
# Bot formatter tests
# ---------------------------------------------------------------------------


class TestBotFormattersLaunchNewProcess:
    """Tests for bot formatters with launch_new_process."""

    def test_task_detail_shows_launch_mode(self):
        """format_task_detail should show 'Launch mode: new console' when true."""
        task = {
            "id": 1,
            "name": "Manual Task",
            "script_path": "/path/to/script.py",
            "arguments": [],
            "interval": 0,
            "task_type": TaskTypes.SCRIPT,
            "command": None,
            "start_time": None,
            "launch_new_process": True,
            "last_run_time": None,
            "last_run_success": None,
            "next_run_time": None,
        }
        result = format_task_detail(task)
        assert "Launch mode: new console" in result

    def test_task_detail_no_launch_mode_when_false(self):
        """format_task_detail should NOT show launch mode when false."""
        task = {
            "id": 1,
            "name": "Manual Task",
            "script_path": "/path/to/script.py",
            "arguments": [],
            "interval": 0,
            "task_type": TaskTypes.SCRIPT,
            "command": None,
            "start_time": None,
            "launch_new_process": False,
            "last_run_time": None,
            "last_run_success": None,
            "next_run_time": None,
        }
        result = format_task_detail(task)
        assert "Launch mode" not in result

    def test_add_summary_shows_launch_mode(self):
        """format_add_summary should show launch mode when true."""
        data = {
            "name": "Manual Task",
            "script_path": "/path/to/script.py",
            "interval": 0,
            "task_type": TaskTypes.SCRIPT,
            "start_time": None,
            "arguments": "",
            "launch_new_process": True,
        }
        result = format_add_summary(data)
        assert "Launch mode: new console" in result

    def test_compact_list_shows_launch_tag(self):
        """format_task_list_compact should show [new console] when true."""
        tasks = [
            {
                "id": 1,
                "name": "Manual Task",
                "script_path": "/path/to/script.py",
                "arguments": [],
                "interval": 0,
                "task_type": TaskTypes.SCRIPT,
                "command": None,
                "start_time": None,
                "launch_new_process": True,
                "last_run_time": None,
                "last_run_success": None,
                "next_run_time": None,
            }
        ]
        result = format_task_list_compact(tasks)
        assert "[new console]" in result


# ---------------------------------------------------------------------------
# Bot conversation wizard tests
# ---------------------------------------------------------------------------


class TestAddWizardLaunchNewProcess:
    """Tests for AddWizard with launch_new_process prompt."""

    def test_interval_zero_prompts_launch_new_process(self):
        """After interval=0, wizard should prompt for launch_new_process."""
        state, _ = AddWizard.start()
        state, _ = AddWizard.advance(state, "backup.py")
        assert state is not None
        state, _ = AddWizard.advance(state, "Manual Backup")
        assert state is not None
        new_state, response = AddWizard.advance(state, "0")
        assert new_state is not None
        assert new_state.step == 5  # launch_new_process step
        assert "console" in response.text.lower() or "launch" in response.text.lower()

    def test_interval_nonzero_skips_launch_new_process(self):
        """After interval>0, wizard should skip launch_new_process."""
        state, _ = AddWizard.start()
        state, _ = AddWizard.advance(state, "backup.py")
        assert state is not None
        state, _ = AddWizard.advance(state, "Scheduled Backup")
        assert state is not None
        new_state, response = AddWizard.advance(state, "5")
        assert new_state is not None
        assert new_state.step == 4  # start_time step
        assert "start time" in response.text.lower() or "HH:MM" in response.text

    def test_launch_yes_stores_true(self):
        """Answering 'yes' to launch prompt should store True."""
        state, _ = AddWizard.start()
        state, _ = AddWizard.advance(state, "backup.py")
        assert state is not None
        state, _ = AddWizard.advance(state, "Manual Backup")
        assert state is not None
        state, _ = AddWizard.advance(state, "0")
        assert state is not None
        # Now at step 5 (launch_new_process)
        new_state, response = AddWizard.advance(state, "yes")
        assert new_state is not None
        assert new_state.data["launch_new_process"] is True
        assert new_state.step == 6  # arguments step

    def test_launch_no_stores_false(self):
        """Answering 'no' to launch prompt should store False."""
        state, _ = AddWizard.start()
        state, _ = AddWizard.advance(state, "backup.py")
        assert state is not None
        state, _ = AddWizard.advance(state, "Manual Backup")
        assert state is not None
        state, _ = AddWizard.advance(state, "0")
        assert state is not None
        new_state, response = AddWizard.advance(state, "no")
        assert new_state is not None
        assert new_state.data["launch_new_process"] is False
        assert new_state.step == 6  # arguments step

    def test_full_flow_with_launch_new_process(self):
        """Full add flow with launch_new_process=True."""
        state, _ = AddWizard.start()
        state, _ = AddWizard.advance(state, "backup.py")
        assert state is not None
        state, _ = AddWizard.advance(state, "Manual Backup")
        assert state is not None
        state, _ = AddWizard.advance(state, "0")  # interval
        assert state is not None
        state, _ = AddWizard.advance(state, "yes")  # launch_new_process
        assert state is not None
        state, _ = AddWizard.advance(state, "skip")  # arguments
        assert state is not None

        assert state.data["launch_new_process"] is True

        result_state, response = AddWizard.advance(state, "yes")  # confirm
        assert result_state is None
        assert response.text == CONFIRMED_SENTINEL


class TestEditWizardLaunchNewProcess:
    """Tests for EditWizard with launch_new_process."""

    def test_edit_interval_to_zero_prompts_launch(self):
        """Changing interval to 0 should prompt for launch_new_process."""
        task = {
            "id": 1,
            "name": "Backup Script",
            "script_path": "C:/scripts/backup.py",
            "arguments": [],
            "interval": 60,
            "task_type": "script",
            "command": None,
            "start_time": "09:00",
            "launch_new_process": False,
        }
        state, _ = EditWizard.start(task)
        state, _ = EditWizard.advance(state, "skip")  # script_path
        assert state is not None
        state, _ = EditWizard.advance(state, "skip")  # name
        assert state is not None
        new_state, response = EditWizard.advance(state, "0")  # interval -> 0
        assert new_state is not None
        assert new_state.step == 5  # launch_new_process step
        assert "console" in response.text.lower() or "launch" in response.text.lower()

    def test_edit_interval_nonzero_skips_launch(self):
        """Keeping interval > 0 should skip launch_new_process."""
        task = {
            "id": 1,
            "name": "Backup Script",
            "script_path": "C:/scripts/backup.py",
            "arguments": [],
            "interval": 60,
            "task_type": "script",
            "command": None,
            "start_time": "09:00",
            "launch_new_process": True,
        }
        state, _ = EditWizard.start(task)
        state, _ = EditWizard.advance(state, "skip")  # script_path
        assert state is not None
        state, _ = EditWizard.advance(state, "skip")  # name
        assert state is not None
        new_state, response = EditWizard.advance(state, "skip")  # keep interval 60
        assert new_state is not None
        assert new_state.step == 4  # start_time step (not launch)

    def test_edit_skip_launch_keeps_original(self):
        """Skipping launch prompt on a task with launch=True should keep True."""
        task = {
            "id": 1,
            "name": "Manual Task",
            "script_path": "C:/scripts/manual.py",
            "arguments": [],
            "interval": 0,
            "task_type": "script",
            "command": None,
            "start_time": None,
            "launch_new_process": True,
        }
        state, _ = EditWizard.start(task)
        state, _ = EditWizard.advance(state, "skip")  # script_path
        assert state is not None
        state, _ = EditWizard.advance(state, "skip")  # name
        assert state is not None
        state, _ = EditWizard.advance(state, "skip")  # interval (keep 0)
        assert state is not None
        # Now at step 5 (launch_new_process)
        new_state, response = EditWizard.advance(state, "skip")
        assert new_state is not None
        # skip means no change, should proceed to arguments
        assert new_state.step == 6
        assert "launch_new_process" not in new_state.data["changes"]

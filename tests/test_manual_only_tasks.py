"""Tests for manual-only tasks (interval 0)."""

from unittest.mock import MagicMock, patch

import pytest

from bot_commander import CONFIRMED_SENTINEL

from src.bot.constants import Messages
from src.bot.conversation import AddWizard, EditWizard
from src.bot.formatters import (
    format_add_summary,
    format_task_detail,
    format_task_list_compact,
)
from src.constants import Defaults, TaskTypes
from src.database import Database
from src.formatters import format_task_list
from src.scheduler import TaskScheduler
from src.script_runner import ScriptRunner
from src.status_page import StatusPage


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


class TestScheduleTaskInterval0:
    """Tests for _schedule_task with interval 0."""

    def test_interval_zero_does_not_create_apscheduler_job(self, mock_scheduler):
        """_schedule_task should not call scheduler.add_job when interval is 0."""
        mock_scheduler._schedule_task(
            task_id=1,
            name="Manual Task",
            script_path="/path/to/script.py",
            interval=0,
        )
        mock_scheduler.scheduler.add_job.assert_not_called()

    def test_interval_zero_logs_manual_only(self, mock_scheduler):
        """_schedule_task should log manual-only message for interval 0."""
        mock_scheduler._schedule_task(
            task_id=1,
            name="Manual Task",
            script_path="/path/to/script.py",
            interval=0,
        )
        mock_scheduler.logger.info.assert_called_once()
        log_msg = mock_scheduler.logger.info.call_args[0][0]
        assert Defaults.MANUAL_ONLY_LABEL in log_msg

    def test_interval_positive_creates_apscheduler_job(self, mock_scheduler):
        """_schedule_task should call scheduler.add_job when interval > 0."""
        mock_scheduler.db.get_last_execution_per_task.return_value = {}
        mock_scheduler._schedule_task(
            task_id=1,
            name="Scheduled Task",
            script_path="/path/to/script.py",
            interval=5,
        )
        mock_scheduler.scheduler.add_job.assert_called_once()


class TestRunTaskManualOnly:
    """Tests for running manual-only tasks with run_task."""

    def test_run_task_works_for_manual_only_task(self, mock_scheduler):
        """run_task should execute a task with interval 0 successfully."""
        task = {
            "id": 1,
            "name": "Manual Task",
            "script_path": "/path/to/script.py",
            "arguments": [],
            "interval": 0,
            "task_type": TaskTypes.SCRIPT,
            "command": None,
            "start_time": None,
        }
        mock_scheduler.db.get_all_tasks.return_value = [task]
        mock_scheduler.script_runner.run_script.return_value = True

        result = mock_scheduler.run_task(1)

        assert result is True
        mock_scheduler.script_runner.run_script.assert_called_once()


class TestAddTaskManualOnly:
    """Tests for add_task with interval 0."""

    def test_add_task_interval_zero_logs_manual_only(self, mock_scheduler):
        """add_task log message should show 'manual only' for interval 0."""
        mock_scheduler.db.add_task.return_value = 1

        mock_scheduler.add_task(
            name="Manual Task",
            script_path="/path/to/script.py",
            interval=0,
        )

        # Check the info log contains "manual only"
        log_calls = mock_scheduler.logger.info.call_args_list
        found = any(Defaults.MANUAL_ONLY_LABEL in str(call) for call in log_calls)
        assert found, "Expected 'manual only' in log messages"


class TestEditTaskManualOnly:
    """Tests for edit_task with interval 0."""

    def test_edit_task_interval_zero_removes_old_job(self, mock_scheduler):
        """edit_task should try to remove old job and not schedule new one."""
        mock_scheduler.scheduler.running = True
        mock_scheduler.db.edit_task.return_value = True

        mock_scheduler.edit_task(
            task_id=1,
            name="Manual Task",
            script_path="/path/to/script.py",
            interval=0,
        )

        # Should try to remove old job
        mock_scheduler.scheduler.remove_job.assert_called_once()
        # Should not add a new APScheduler job (only the _schedule_task guard log)
        mock_scheduler.scheduler.add_job.assert_not_called()


class TestListTasksManualOnly:
    """Tests for list_tasks with manual-only tasks."""

    def test_manual_task_has_none_next_run_time(self, mock_scheduler):
        """Manual-only task should have next_run_time = None since no APScheduler job."""
        task = {
            "id": 1,
            "name": "Manual Task",
            "script_path": "/path/to/script.py",
            "arguments": [],
            "interval": 0,
            "task_type": TaskTypes.SCRIPT,
            "command": None,
            "start_time": None,
        }
        mock_scheduler.db.get_all_tasks.return_value = [task]
        mock_scheduler.scheduler.get_jobs.return_value = []
        mock_scheduler.db.get_last_execution_per_task.return_value = {}

        tasks = mock_scheduler.list_tasks()

        assert tasks[0]["next_run_time"] is None


# ---------------------------------------------------------------------------
# CLI Formatter tests
# ---------------------------------------------------------------------------


class TestFormatTaskListManualOnly:
    """Tests for format_task_list with manual-only tasks."""

    def test_interval_zero_shows_manual_only_label(self):
        """format_task_list should show 'manual only' for interval 0."""
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
                "last_run_time": None,
                "last_run_success": None,
                "next_run_time": None,
            }
        ]
        result = format_task_list(tasks)
        assert Defaults.MANUAL_ONLY_LABEL in result

    def test_interval_zero_next_run_shows_manual_only(self):
        """Next run for manual-only task should show 'manual only'."""
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
                "last_run_time": None,
                "last_run_success": None,
                "next_run_time": None,
            }
        ]
        result = format_task_list(tasks, show_next_run=True)
        assert "Next run: manual only" in result

    def test_interval_positive_shows_minutes(self):
        """format_task_list should show minutes for positive interval."""
        tasks = [
            {
                "id": 1,
                "name": "Scheduled Task",
                "script_path": "/path/to/script.py",
                "arguments": [],
                "interval": 5,
                "task_type": TaskTypes.SCRIPT,
                "command": None,
                "start_time": None,
                "last_run_time": None,
                "last_run_success": None,
                "next_run_time": None,
            }
        ]
        result = format_task_list(tasks, show_next_run=False)
        assert "5 minute(s)" in result


# ---------------------------------------------------------------------------
# Bot formatter tests
# ---------------------------------------------------------------------------


class TestBotFormattersManualOnly:
    """Tests for bot formatters with manual-only tasks."""

    def test_compact_list_shows_manual_tag(self):
        """format_task_list_compact should show [manual] for interval 0."""
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
                "last_run_time": None,
                "last_run_success": None,
                "next_run_time": None,
            }
        ]
        result = format_task_list_compact(tasks)
        assert "[manual]" in result

    def test_compact_list_positive_interval_shows_min(self):
        """format_task_list_compact should show [Xmin] for positive interval."""
        tasks = [
            {
                "id": 1,
                "name": "Scheduled Task",
                "script_path": "/path/to/script.py",
                "arguments": [],
                "interval": 10,
                "task_type": TaskTypes.SCRIPT,
                "command": None,
                "start_time": None,
                "last_run_time": None,
                "last_run_success": None,
                "next_run_time": None,
            }
        ]
        result = format_task_list_compact(tasks)
        assert "[10min]" in result

    def test_detail_shows_manual_only_interval(self):
        """format_task_detail should show 'manual only' for interval 0."""
        task = {
            "id": 1,
            "name": "Manual Task",
            "script_path": "/path/to/script.py",
            "arguments": [],
            "interval": 0,
            "task_type": TaskTypes.SCRIPT,
            "command": None,
            "start_time": None,
            "last_run_time": None,
            "last_run_success": None,
            "next_run_time": None,
        }
        result = format_task_detail(task)
        assert "Interval: manual only" in result

    def test_add_summary_shows_manual_only_interval(self):
        """format_add_summary should show 'manual only' for interval 0."""
        data = {
            "name": "Manual Task",
            "script_path": "/path/to/script.py",
            "interval": 0,
            "task_type": TaskTypes.SCRIPT,
            "start_time": None,
            "arguments": "",
        }
        result = format_add_summary(data)
        assert "Interval: manual only" in result


# ---------------------------------------------------------------------------
# Bot conversation wizard tests
# ---------------------------------------------------------------------------


class TestAddWizardManualOnly:
    """Tests for AddWizard with interval 0 (manual-only)."""

    def test_interval_zero_skips_start_time(self):
        """Interval 0 should skip start_time step and go to arguments."""
        state, _ = AddWizard.start()
        state, _ = AddWizard.advance(state, "backup.py")
        assert state is not None
        state, _ = AddWizard.advance(state, "Manual Backup")
        assert state is not None
        new_state, response = AddWizard.advance(state, "0")
        assert new_state is not None
        assert new_state.data["interval"] == 0
        assert new_state.data["start_time"] is None
        assert new_state.step == 5
        assert response.text == Messages.WIZARD_ADD_ARGUMENTS

    def test_full_manual_only_flow(self):
        """Full flow for manual-only task: path -> name -> interval(0) -> args -> confirm."""
        state, _ = AddWizard.start()
        state, _ = AddWizard.advance(state, "backup.py")
        assert state is not None
        state, _ = AddWizard.advance(state, "Manual Backup")
        assert state is not None
        state, _ = AddWizard.advance(state, "0")
        assert state is not None
        state, _ = AddWizard.advance(state, "skip")
        assert state is not None

        assert state.data["interval"] == 0
        assert state.data["start_time"] is None
        assert state.data["arguments"] is None

        result_state, response = AddWizard.advance(state, "yes")
        assert result_state is None
        assert response.text == CONFIRMED_SENTINEL

    def test_negative_interval_still_invalid(self):
        """Negative intervals should still be rejected."""
        state, _ = AddWizard.start()
        state, _ = AddWizard.advance(state, "backup.py")
        assert state is not None
        state, _ = AddWizard.advance(state, "Backup")
        assert state is not None
        new_state, response = AddWizard.advance(state, "-1")
        assert new_state is not None
        assert new_state.step == 3
        assert response.text == Messages.WIZARD_INVALID_INTERVAL


class TestEditWizardManualOnly:
    """Tests for EditWizard with interval 0 (manual-only)."""

    def test_edit_interval_to_zero_skips_start_time(self):
        """Changing interval to 0 should skip start_time and clear it."""
        task = {
            "id": 1,
            "name": "Backup Script",
            "script_path": "C:/scripts/backup.py",
            "arguments": ["--verbose"],
            "interval": 60,
            "task_type": "script",
            "command": None,
            "start_time": "09:00",
        }
        state, _ = EditWizard.start(task)
        state, _ = EditWizard.advance(state, "skip")  # script_path
        assert state is not None
        state, _ = EditWizard.advance(state, "skip")  # name
        assert state is not None
        new_state, response = EditWizard.advance(state, "0")  # interval -> 0
        assert new_state is not None
        assert new_state.data["changes"]["interval"] == 0
        assert new_state.data["changes"]["start_time"] is None
        assert new_state.step == 5  # skipped start_time, went to arguments

    def test_edit_skip_interval_when_original_zero(self):
        """Skipping interval on a manual-only task should skip start_time too."""
        task = {
            "id": 1,
            "name": "Manual Task",
            "script_path": "C:/scripts/manual.py",
            "arguments": [],
            "interval": 0,
            "task_type": "script",
            "command": None,
            "start_time": None,
        }
        state, _ = EditWizard.start(task)
        state, _ = EditWizard.advance(state, "skip")  # script_path
        assert state is not None
        state, _ = EditWizard.advance(state, "skip")  # name
        assert state is not None
        new_state, response = EditWizard.advance(state, "skip")  # interval (keep 0)
        assert new_state is not None
        # Should skip start_time since effective interval is still 0
        assert new_state.step == 5

    def test_edit_negative_interval_still_invalid(self):
        """Negative intervals should still be rejected in edit wizard."""
        task = {
            "id": 1,
            "name": "Backup Script",
            "script_path": "C:/scripts/backup.py",
            "arguments": [],
            "interval": 60,
            "task_type": "script",
            "command": None,
            "start_time": None,
        }
        state, _ = EditWizard.start(task)
        state, _ = EditWizard.advance(state, "skip")  # script_path
        assert state is not None
        state, _ = EditWizard.advance(state, "skip")  # name
        assert state is not None
        new_state, response = EditWizard.advance(state, "-1")
        assert new_state is not None
        assert new_state.step == 3
        assert response.text == Messages.WIZARD_INVALID_INTERVAL


# ---------------------------------------------------------------------------
# Bot constants tests
# ---------------------------------------------------------------------------


class TestBotConstantsManualOnly:
    """Tests for bot constants with manual-only references."""

    def test_wizard_add_interval_mentions_manual(self):
        """WIZARD_ADD_INTERVAL should mention 0 = manual only."""
        assert "0" in Messages.WIZARD_ADD_INTERVAL
        assert "manual" in Messages.WIZARD_ADD_INTERVAL.lower()

    def test_wizard_invalid_interval_mentions_zero(self):
        """WIZARD_INVALID_INTERVAL should mention 0 is valid."""
        assert "0" in Messages.WIZARD_INVALID_INTERVAL

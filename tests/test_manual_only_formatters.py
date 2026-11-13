"""Tests for manual-only tasks (interval 0)."""




from src.bot.formatters import (
    format_add_summary,
    format_task_detail,
    format_task_list_compact,
)
from src.constants import Defaults, TaskTypes
from src.formatters import format_task_list


# ---------------------------------------------------------------------------
# Scheduler tests
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

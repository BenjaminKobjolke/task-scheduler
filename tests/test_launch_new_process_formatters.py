"""Tests for launch_new_process feature."""




from src.bot.formatters import (
    format_add_summary,
    format_task_detail,
    format_task_list_compact,
)
from src.constants import TaskTypes
from src.formatters import format_task_list


# ---------------------------------------------------------------------------
# Database tests
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

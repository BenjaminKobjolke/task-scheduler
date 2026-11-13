"""Focused tests for bot formatter output."""

from src.bot.formatters import format_task_detail


class TestFormatTaskDetail:
    """Tests for format_task_detail."""

    def test_script_task_detail(self) -> None:
        task = {
            "id": 1,
            "name": "Backup Script",
            "script_path": "C:/scripts/backup.py",
            "arguments": ["--verbose", "--dry-run"],
            "interval": 60,
            "task_type": "script",
            "command": None,
            "start_time": "09:00",
            "last_run_time": "2026-02-26 10:00:00",
            "last_run_success": True,
            "next_run_time": None,
        }
        result = format_task_detail(task)
        assert "Backup Script" in result
        assert "1" in result
        assert "C:/scripts/backup.py" in result
        assert "60" in result
        assert "--verbose" in result
        assert "09:00" in result
        assert "2026-02-26 10:00:00" in result

    def test_uv_command_task_detail(self) -> None:
        task = {
            "id": 3,
            "name": "Serve App",
            "script_path": "C:/projects/myapp",
            "arguments": [],
            "interval": 5,
            "task_type": "uv_command",
            "command": "serve",
            "start_time": None,
            "last_run_time": None,
            "last_run_success": None,
            "next_run_time": None,
        }
        result = format_task_detail(task)
        assert "Serve App" in result
        assert "C:/projects/myapp" in result
        assert "serve" in result
        assert "uv" in result.lower()

    def test_task_detail_no_arguments(self) -> None:
        task = {
            "id": 1,
            "name": "Simple",
            "script_path": "script.py",
            "arguments": [],
            "interval": 10,
            "task_type": "script",
            "command": None,
            "start_time": None,
            "last_run_time": None,
            "last_run_success": None,
            "next_run_time": None,
        }
        result = format_task_detail(task)
        assert "None" in result or "none" in result.lower()

    def test_task_detail_with_next_run(self) -> None:
        task = {
            "id": 1,
            "name": "Scheduled",
            "script_path": "script.py",
            "arguments": [],
            "interval": 10,
            "task_type": "script",
            "command": None,
            "start_time": None,
            "last_run_time": None,
            "last_run_success": None,
            "next_run_time": "2026-02-26 12:00:00",
        }
        result = format_task_detail(task)
        assert "2026-02-26 12:00:00" in result

    def test_task_detail_last_run_failed(self) -> None:
        task = {
            "id": 1,
            "name": "Failed Task",
            "script_path": "script.py",
            "arguments": [],
            "interval": 10,
            "task_type": "script",
            "command": None,
            "start_time": None,
            "last_run_time": "2026-02-26 10:00:00",
            "last_run_success": False,
            "next_run_time": None,
        }
        result = format_task_detail(task)
        assert "failed" in result.lower()


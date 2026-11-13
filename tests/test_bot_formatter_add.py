"""Focused tests for bot formatter output."""

from src.bot.formatters import format_add_summary


class TestFormatAddSummary:
    """Tests for format_add_summary."""

    def test_script_task_summary(self) -> None:
        data = {
            "name": "Backup",
            "script_path": "C:/scripts/backup.py",
            "interval": 60,
            "task_type": "script",
            "start_time": None,
            "arguments": "--verbose",
        }
        result = format_add_summary(data)
        assert "Backup" in result
        assert "C:/scripts/backup.py" in result
        assert "60" in result
        assert "--verbose" in result

    def test_uv_command_task_summary(self) -> None:
        data = {
            "name": "Serve",
            "script_path": "C:/projects/myapp",
            "interval": 5,
            "task_type": "uv_command",
            "command": "serve",
            "start_time": None,
            "arguments": "",
        }
        result = format_add_summary(data)
        assert "Serve" in result
        assert "C:/projects/myapp" in result
        assert "serve" in result

    def test_summary_with_start_time(self) -> None:
        data = {
            "name": "Morning Job",
            "script_path": "job.py",
            "interval": 60,
            "task_type": "script",
            "start_time": "09:00",
            "arguments": "",
        }
        result = format_add_summary(data)
        assert "09:00" in result

    def test_summary_without_start_time(self) -> None:
        data = {
            "name": "Anytime Job",
            "script_path": "job.py",
            "interval": 10,
            "task_type": "script",
            "start_time": None,
            "arguments": "",
        }
        result = format_add_summary(data)
        assert "Anytime Job" in result

    def test_summary_without_arguments(self) -> None:
        data = {
            "name": "Simple",
            "script_path": "script.py",
            "interval": 10,
            "task_type": "script",
            "start_time": None,
            "arguments": "",
        }
        result = format_add_summary(data)
        assert "Simple" in result


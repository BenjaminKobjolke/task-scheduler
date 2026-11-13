"""Focused tests for bot formatter output."""

from src.bot.formatters import format_task_list_compact


class TestFormatTaskListCompact:
    """Tests for format_task_list_compact."""

    def test_empty_list_returns_no_tasks(self) -> None:
        result = format_task_list_compact([])
        assert result == "No tasks scheduled."

    def test_single_script_task(self) -> None:
        tasks = [
            {
                "id": 1,
                "name": "Backup Script",
                "script_path": "C:/scripts/backup.py",
                "arguments": [],
                "interval": 60,
                "task_type": "script",
                "command": None,
                "start_time": None,
                "last_run_time": None,
                "last_run_success": None,
                "next_run_time": None,
            }
        ]
        result = format_task_list_compact(tasks)
        assert "1." in result
        assert "Backup Script" in result
        assert "60min" in result

    def test_single_task_with_last_run_success(self) -> None:
        tasks = [
            {
                "id": 1,
                "name": "Backup Script",
                "script_path": "C:/scripts/backup.py",
                "arguments": [],
                "interval": 60,
                "task_type": "script",
                "command": None,
                "start_time": None,
                "last_run_time": "2026-02-26 10:00:00",
                "last_run_success": True,
                "next_run_time": None,
            }
        ]
        result = format_task_list_compact(tasks)
        assert "success" in result.lower()

    def test_single_task_with_last_run_failure(self) -> None:
        tasks = [
            {
                "id": 2,
                "name": "Deploy",
                "script_path": "C:/scripts/deploy.py",
                "arguments": [],
                "interval": 30,
                "task_type": "script",
                "command": None,
                "start_time": None,
                "last_run_time": "2026-02-26 10:00:00",
                "last_run_success": False,
                "next_run_time": None,
            }
        ]
        result = format_task_list_compact(tasks)
        assert "failed" in result.lower()

    def test_multiple_tasks(self) -> None:
        tasks = [
            {
                "id": 1,
                "name": "Backup",
                "script_path": "backup.py",
                "arguments": [],
                "interval": 60,
                "task_type": "script",
                "command": None,
                "start_time": None,
                "last_run_time": None,
                "last_run_success": None,
                "next_run_time": None,
            },
            {
                "id": 2,
                "name": "Deploy",
                "script_path": "deploy.py",
                "arguments": [],
                "interval": 30,
                "task_type": "script",
                "command": None,
                "start_time": None,
                "last_run_time": "2026-02-26 10:00:00",
                "last_run_success": True,
                "next_run_time": None,
            },
        ]
        result = format_task_list_compact(tasks)
        lines = result.strip().split("\n")
        assert len(lines) == 2
        assert "1." in lines[0]
        assert "Backup" in lines[0]
        assert "2." in lines[1]
        assert "Deploy" in lines[1]

    def test_uv_command_task_shows_uv_tag(self) -> None:
        tasks = [
            {
                "id": 3,
                "name": "Serve",
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
        ]
        result = format_task_list_compact(tasks)
        assert "uv" in result.lower()

    def test_task_never_run(self) -> None:
        tasks = [
            {
                "id": 1,
                "name": "New Task",
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
        ]
        result = format_task_list_compact(tasks)
        # Should not contain last run status info for tasks never run
        assert "never" in result.lower() or "last" not in result.lower()


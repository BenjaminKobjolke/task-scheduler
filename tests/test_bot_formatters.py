"""Tests for bot formatters module."""
from src.bot.formatters import (
    format_add_summary,
    format_edit_changes,
    format_execution_history_compact,
    format_task_detail,
    format_task_list_compact,
)


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


class TestFormatExecutionHistoryCompact:
    """Tests for format_execution_history_compact."""

    def test_empty_history(self) -> None:
        result = format_execution_history_compact([])
        assert result == "No execution history found."

    def test_single_successful_execution(self) -> None:
        executions = [
            {
                "execution_time": "2026-02-26 10:00:00",
                "name": "Backup",
                "success": True,
            }
        ]
        result = format_execution_history_compact(executions)
        assert "2026-02-26 10:00:00" in result
        assert "Backup" in result
        assert "success" in result.lower()

    def test_single_failed_execution(self) -> None:
        executions = [
            {
                "execution_time": "2026-02-26 10:00:00",
                "name": "Deploy",
                "success": False,
            }
        ]
        result = format_execution_history_compact(executions)
        assert "Deploy" in result
        assert "failed" in result.lower()

    def test_multiple_executions(self) -> None:
        executions = [
            {
                "execution_time": "2026-02-26 10:00:00",
                "name": "Backup",
                "success": True,
            },
            {
                "execution_time": "2026-02-26 09:00:00",
                "name": "Deploy",
                "success": False,
            },
            {
                "execution_time": "2026-02-26 08:00:00",
                "name": "Cleanup",
                "success": True,
            },
        ]
        result = format_execution_history_compact(executions)
        lines = result.strip().split("\n")
        assert len(lines) == 3
        assert "Backup" in lines[0]
        assert "Deploy" in lines[1]
        assert "Cleanup" in lines[2]


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


class TestFormatEditChanges:
    """Tests for format_edit_changes."""

    def test_no_changes(self) -> None:
        original = {"name": "Backup", "interval": 60}
        changes: dict = {}
        result = format_edit_changes(original, changes)
        assert "no changes" in result.lower()

    def test_single_change(self) -> None:
        original = {"name": "Backup", "interval": 60}
        changes = {"name": "New Backup"}
        result = format_edit_changes(original, changes)
        assert "Backup" in result
        assert "New Backup" in result

    def test_multiple_changes(self) -> None:
        original = {"name": "Backup", "interval": 60, "script_path": "old.py"}
        changes = {"name": "New Backup", "interval": 30}
        result = format_edit_changes(original, changes)
        assert "Backup" in result
        assert "New Backup" in result
        assert "60" in result
        assert "30" in result

    def test_interval_change(self) -> None:
        original = {"interval": 60}
        changes = {"interval": 30}
        result = format_edit_changes(original, changes)
        assert "60" in result
        assert "30" in result

    def test_script_path_change(self) -> None:
        original = {"script_path": "old.py"}
        changes = {"script_path": "new.py"}
        result = format_edit_changes(original, changes)
        assert "old.py" in result
        assert "new.py" in result

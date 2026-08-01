"""Tests for task query and execution commands."""

from unittest.mock import MagicMock, call, patch

import pytest

from src.cli_output import CliOutput
from src.commands.query import handle_run_name
from src.scheduler import TaskScheduler


def _make_task(task_id: int, name: str) -> dict:
    """Create the task fields required by the command formatter."""
    return {
        "id": task_id,
        "name": name,
        "script_path": f"C:\\tasks\\{name}.bat",
        "interval": 0,
        "arguments": [],
    }


class TestHandleRunName:
    """Verify partial-name lookup and interactive task selection."""

    def test_filters_case_insensitively_and_runs_selected_match(self) -> None:
        scheduler = MagicMock(spec=TaskScheduler)
        cli = MagicMock(spec=CliOutput)
        scheduler.list_tasks.return_value = [
            _make_task(3, "Daily Backup"),
            _make_task(7, "Backup Cleanup"),
            _make_task(9, "Send Report"),
        ]

        with (
            patch("builtins.input", return_value="2"),
            patch("src.commands.query.handle_run_id") as run_id,
        ):
            handle_run_name(scheduler, cli, "BACKUP")

        run_id.assert_called_once_with(scheduler, cli, 7)
        matching_output = cli.info.call_args_list[0].args[0]
        assert "1. Daily Backup (ID: 3)" in matching_output
        assert "2. Backup Cleanup (ID: 7)" in matching_output
        assert "Send Report" not in matching_output

    def test_retries_until_selection_is_valid(self) -> None:
        scheduler = MagicMock(spec=TaskScheduler)
        cli = MagicMock(spec=CliOutput)
        scheduler.list_tasks.return_value = [_make_task(3, "Backup")]

        with (
            patch("builtins.input", side_effect=["invalid", "2", "1"]),
            patch("src.commands.query.handle_run_id") as run_id,
        ):
            handle_run_name(scheduler, cli, "backup")

        assert cli.error.call_args_list == [
            call("Please enter a number between 1 and 1."),
            call("Please enter a number between 1 and 1."),
        ]
        run_id.assert_called_once_with(scheduler, cli, 3)

    def test_empty_filter_allows_selection_from_all_tasks(self) -> None:
        scheduler = MagicMock(spec=TaskScheduler)
        cli = MagicMock(spec=CliOutput)
        scheduler.list_tasks.return_value = [
            _make_task(2, "Backup"),
            _make_task(8, "Report"),
        ]

        with (
            patch("builtins.input", return_value="2"),
            patch("src.commands.query.handle_run_id") as run_id,
        ):
            handle_run_name(scheduler, cli, "")

        run_id.assert_called_once_with(scheduler, cli, 8)

    def test_exits_when_no_tasks_match(self) -> None:
        scheduler = MagicMock(spec=TaskScheduler)
        cli = MagicMock(spec=CliOutput)
        scheduler.list_tasks.return_value = [_make_task(2, "Backup")]

        with pytest.raises(SystemExit) as exc_info:
            handle_run_name(scheduler, cli, "report")

        assert exc_info.value.code == 1
        cli.error.assert_called_once_with("No tasks found matching 'report'.")

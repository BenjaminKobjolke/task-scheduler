"""Focused tests for bot formatter output."""

from src.bot.formatters import format_execution_history_compact


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


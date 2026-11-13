"""Focused tests for bot formatter output."""

from src.bot.formatters import format_edit_changes


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


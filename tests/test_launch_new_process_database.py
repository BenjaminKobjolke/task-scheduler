"""Tests for launch_new_process feature."""

import os
import tempfile

import pytest


from src.constants import Database as DbConstants
from src.database import Database


# ---------------------------------------------------------------------------
# Database tests
# ---------------------------------------------------------------------------


@pytest.fixture


def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = os.path.join(tmpdir, "test.sqlite")
        db = Database(db_path)
        yield db


class TestDatabaseLaunchNewProcess:
    """Tests for launch_new_process column in database."""

    def test_add_task_default_launch_new_process_false(self, temp_db):
        """Default launch_new_process should be False."""
        temp_db.add_task("Test", "/path/script.py", 0)
        tasks = temp_db.get_all_tasks()
        assert tasks[0]["launch_new_process"] is False

    def test_add_task_with_launch_new_process_true(self, temp_db):
        """Should store launch_new_process=True."""
        temp_db.add_task("Test", "/path/script.py", 0, launch_new_process=True)
        tasks = temp_db.get_all_tasks()
        assert tasks[0]["launch_new_process"] is True

    def test_edit_task_sets_launch_new_process(self, temp_db):
        """edit_task should update launch_new_process."""
        task_id = temp_db.add_task("Test", "/path/script.py", 0)
        temp_db.edit_task(
            task_id, "Test", "/path/script.py", 0, launch_new_process=True
        )
        tasks = temp_db.get_all_tasks()
        assert tasks[0]["launch_new_process"] is True

    def test_edit_task_clears_launch_new_process(self, temp_db):
        """edit_task should be able to clear launch_new_process."""
        task_id = temp_db.add_task(
            "Test", "/path/script.py", 0, launch_new_process=True
        )
        temp_db.edit_task(
            task_id, "Test", "/path/script.py", 0, launch_new_process=False
        )
        tasks = temp_db.get_all_tasks()
        assert tasks[0]["launch_new_process"] is False

    def test_migration_adds_column(self, temp_db):
        """Migration should add launch_new_process column to existing databases."""
        import sqlite3

        with sqlite3.connect(temp_db.db_path) as conn:
            cursor = conn.execute("PRAGMA table_info(tasks)")
            columns = [row[1] for row in cursor.fetchall()]
            assert DbConstants.COL_LAUNCH_NEW_PROCESS in columns

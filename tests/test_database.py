"""Tests for database module."""
import os
import tempfile
import pytest
from src.database import Database
from src.constants import TaskTypes


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    # Use ignore_cleanup_errors for Windows SQLite file locking issues
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = os.path.join(tmpdir, "test.sqlite")
        db = Database(db_path)
        yield db


class TestDatabaseAddTask:
    """Tests for add_task method."""

    def test_add_task_returns_id(self, temp_db):
        task_id = temp_db.add_task("Test Task", "/path/to/script.py", 5)
        assert isinstance(task_id, int)
        assert task_id > 0

    def test_add_task_with_arguments(self, temp_db):
        args = ["--input", "file.txt", "--output", "result.txt"]
        task_id = temp_db.add_task("Test Task", "/path/to/script.py", 5, args)
        assert task_id > 0

    def test_add_multiple_tasks(self, temp_db):
        id1 = temp_db.add_task("Task 1", "/path/1.py", 1)
        id2 = temp_db.add_task("Task 2", "/path/2.py", 2)
        assert id1 != id2


class TestDatabaseGetTasks:
    """Tests for get_all_tasks method."""

    def test_get_empty_tasks(self, temp_db):
        tasks = temp_db.get_all_tasks()
        assert tasks == []

    def test_get_all_tasks_returns_added(self, temp_db):
        temp_db.add_task("Task 1", "/path/1.py", 5)
        temp_db.add_task("Task 2", "/path/2.py", 10)

        tasks = temp_db.get_all_tasks()
        assert len(tasks) == 2
        assert tasks[0]["name"] == "Task 1"
        assert tasks[1]["name"] == "Task 2"

    def test_get_task_preserves_arguments(self, temp_db):
        args = ["--verbose", "--debug"]
        temp_db.add_task("Test", "/path/script.py", 5, args)

        tasks = temp_db.get_all_tasks()
        assert tasks[0]["arguments"] == args


class TestDatabaseRemoveTask:
    """Tests for remove_task method."""

    def test_remove_task(self, temp_db):
        task_id = temp_db.add_task("Test", "/path/script.py", 5)
        temp_db.remove_task(task_id)

        tasks = temp_db.get_all_tasks()
        assert len(tasks) == 0

    def test_remove_nonexistent_task(self, temp_db):
        # Should not raise an error
        temp_db.remove_task(999)


class TestDatabaseEditTask:
    """Tests for edit_task method."""

    def test_edit_task_name(self, temp_db):
        task_id = temp_db.add_task("Original", "/path/script.py", 5)
        result = temp_db.edit_task(task_id, "Updated", "/path/script.py", 5)

        assert result is True
        tasks = temp_db.get_all_tasks()
        assert tasks[0]["name"] == "Updated"

    def test_edit_task_interval(self, temp_db):
        task_id = temp_db.add_task("Test", "/path/script.py", 5)
        temp_db.edit_task(task_id, "Test", "/path/script.py", 15)

        tasks = temp_db.get_all_tasks()
        assert tasks[0]["interval"] == 15

    def test_edit_nonexistent_task(self, temp_db):
        result = temp_db.edit_task(999, "Test", "/path/script.py", 5)
        assert result is False


class TestDatabaseExecutionHistory:
    """Tests for execution history methods."""

    def test_add_execution(self, temp_db):
        task_id = temp_db.add_task("Test", "/path/script.py", 5)
        temp_db.add_task_execution(task_id, True)

        executions = temp_db.get_recent_executions(10)
        assert len(executions) == 1
        assert executions[0]["success"] == 1

    def test_get_recent_executions_limit(self, temp_db):
        task_id = temp_db.add_task("Test", "/path/script.py", 5)

        for _ in range(5):
            temp_db.add_task_execution(task_id, True)

        executions = temp_db.get_recent_executions(3)
        assert len(executions) == 3

    def test_execution_includes_task_details(self, temp_db):
        task_id = temp_db.add_task("My Task", "/path/script.py", 5, ["--arg"])
        temp_db.add_task_execution(task_id, True)

        executions = temp_db.get_recent_executions(10)
        assert executions[0]["name"] == "My Task"
        assert executions[0]["script_path"] == "/path/script.py"


class TestDatabaseClearAll:
    """Tests for clear_all_tasks method."""

    def test_clear_all_tasks(self, temp_db):
        temp_db.add_task("Task 1", "/path/1.py", 5)
        temp_db.add_task("Task 2", "/path/2.py", 10)
        temp_db.clear_all_tasks()

        tasks = temp_db.get_all_tasks()
        assert len(tasks) == 0


class TestDatabaseUvCommandTasks:
    """Tests for uv command task support."""

    def test_add_uv_command_task(self, temp_db):
        task_id = temp_db.add_task(
            name="UV Task",
            script_path="/path/to/project",
            interval=5,
            task_type=TaskTypes.UV_COMMAND,
            command="my-command"
        )
        assert task_id > 0

    def test_get_uv_command_task(self, temp_db):
        temp_db.add_task(
            name="UV Task",
            script_path="/path/to/project",
            interval=5,
            task_type=TaskTypes.UV_COMMAND,
            command="my-command"
        )

        tasks = temp_db.get_all_tasks()
        assert len(tasks) == 1
        assert tasks[0]["task_type"] == TaskTypes.UV_COMMAND
        assert tasks[0]["command"] == "my-command"

    def test_edit_uv_command_task(self, temp_db):
        task_id = temp_db.add_task(
            name="UV Task",
            script_path="/path/to/project",
            interval=5,
            task_type=TaskTypes.UV_COMMAND,
            command="old-command"
        )

        result = temp_db.edit_task(
            task_id, "UV Task", "/path/to/project", 5,
            task_type=TaskTypes.UV_COMMAND,
            command="new-command"
        )

        assert result is True
        tasks = temp_db.get_all_tasks()
        assert tasks[0]["command"] == "new-command"

    def test_legacy_tasks_default_to_script(self, temp_db):
        # Simulate legacy task (task_type defaults to 'script')
        _task_id = temp_db.add_task("Legacy", "/path/script.py", 5)

        tasks = temp_db.get_all_tasks()
        assert tasks[0]["task_type"] == TaskTypes.SCRIPT
        assert tasks[0]["command"] is None

    def test_execution_includes_task_type(self, temp_db):
        task_id = temp_db.add_task(
            "UV Task", "/path/to/project", 5,
            task_type=TaskTypes.UV_COMMAND,
            command="my-command"
        )
        temp_db.add_task_execution(task_id, True)

        executions = temp_db.get_recent_executions(10)
        assert executions[0]["task_type"] == TaskTypes.UV_COMMAND
        assert executions[0]["command"] == "my-command"

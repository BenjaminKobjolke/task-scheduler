"""Tests for launch_new_process feature."""




from src.constants import TaskTypes


# ---------------------------------------------------------------------------
# Database tests
# ---------------------------------------------------------------------------






class TestRunTaskLaunchNewProcess:
    """Tests for run_task routing based on launch_new_process flag."""

    def test_run_task_launches_in_new_console_when_flag_set(self, mock_scheduler):
        """run_task should use launch_in_new_console when launch_new_process=True."""
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
        }
        mock_scheduler.db.get_all_tasks.return_value = [task]
        mock_scheduler.script_runner.launch_in_new_console.return_value = True

        result = mock_scheduler.run_task(1)

        assert result is True
        mock_scheduler.script_runner.launch_in_new_console.assert_called_once()
        mock_scheduler.db.add_task_execution.assert_called_once_with(1, True)
        # Should NOT call _process_job / run_script
        mock_scheduler.script_runner.run_script.assert_not_called()

    def test_run_task_uses_process_job_when_flag_not_set(self, mock_scheduler):
        """run_task should use _process_job when launch_new_process=False."""
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
        }
        mock_scheduler.db.get_all_tasks.return_value = [task]
        mock_scheduler.script_runner.run_script.return_value = True

        result = mock_scheduler.run_task(1)

        assert result is True
        mock_scheduler.script_runner.run_script.assert_called_once()
        mock_scheduler.script_runner.launch_in_new_console.assert_not_called()

    def test_run_task_records_history_for_new_console_launch(self, mock_scheduler):
        """run_task should record execution history even for new console launches."""
        task = {
            "id": 42,
            "name": "Detached Task",
            "script_path": "/path/to/script.py",
            "arguments": ["--arg"],
            "interval": 0,
            "task_type": TaskTypes.SCRIPT,
            "command": None,
            "start_time": None,
            "launch_new_process": True,
        }
        mock_scheduler.db.get_all_tasks.return_value = [task]
        mock_scheduler.script_runner.launch_in_new_console.return_value = True

        mock_scheduler.run_task(42)

        mock_scheduler.db.add_task_execution.assert_called_once_with(42, True)


class TestEditTaskClearsLaunchNewProcess:
    """Tests for edit_task clearing launch_new_process when interval changes."""

    def test_edit_task_clears_launch_when_interval_nonzero(self, mock_scheduler):
        """edit_task should force launch_new_process=False when interval != 0."""
        mock_scheduler.scheduler.running = True
        mock_scheduler.db.edit_task.return_value = True
        mock_scheduler.db.get_last_execution_per_task.return_value = {}

        mock_scheduler.edit_task(
            task_id=1,
            name="Task",
            script_path="/path/script.py",
            interval=5,
            launch_new_process=True,
        )

        # Should have been called with launch_new_process=False
        db_call = mock_scheduler.db.edit_task.call_args
        assert db_call.kwargs.get("launch_new_process") is False or (
            len(db_call.args) > 8 and db_call.args[8] is False
        )

    def test_edit_task_preserves_launch_when_interval_zero(self, mock_scheduler):
        """edit_task should preserve launch_new_process when interval == 0."""
        mock_scheduler.scheduler.running = True
        mock_scheduler.db.edit_task.return_value = True

        mock_scheduler.edit_task(
            task_id=1,
            name="Task",
            script_path="/path/script.py",
            interval=0,
            launch_new_process=True,
        )

        db_call = mock_scheduler.db.edit_task.call_args
        assert db_call.kwargs.get("launch_new_process") is True


class TestTaskChecksumIncludesLaunchNewProcess:
    """Tests for _get_task_checksum including launch_new_process."""

    def test_checksum_differs_with_launch_new_process(self, mock_scheduler):
        """Checksum should change when launch_new_process changes."""
        task_a = {
            "name": "Task",
            "script_path": "/path/script.py",
            "interval": 0,
            "start_time": None,
            "arguments": [],
            "task_type": TaskTypes.SCRIPT,
            "command": None,
            "launch_new_process": False,
        }
        task_b = dict(task_a, launch_new_process=True)

        checksum_a = mock_scheduler._get_task_checksum(task_a)
        checksum_b = mock_scheduler._get_task_checksum(task_b)

        assert checksum_a != checksum_b

"""Tests for manual-only tasks (interval 0)."""




from src.constants import Defaults, TaskTypes


# ---------------------------------------------------------------------------
# Scheduler tests
# ---------------------------------------------------------------------------






class TestScheduleTaskInterval0:
    """Tests for _schedule_task with interval 0."""

    def test_interval_zero_does_not_create_apscheduler_job(self, mock_scheduler):
        """_schedule_task should not call scheduler.add_job when interval is 0."""
        mock_scheduler._schedule_task(
            task_id=1,
            name="Manual Task",
            script_path="/path/to/script.py",
            interval=0,
        )
        mock_scheduler.scheduler.add_job.assert_not_called()

    def test_interval_zero_logs_manual_only(self, mock_scheduler):
        """_schedule_task should log manual-only message for interval 0."""
        mock_scheduler._schedule_task(
            task_id=1,
            name="Manual Task",
            script_path="/path/to/script.py",
            interval=0,
        )
        mock_scheduler.logger.info.assert_called_once()
        log_msg = mock_scheduler.logger.info.call_args[0][0]
        assert Defaults.MANUAL_ONLY_LABEL in log_msg

    def test_interval_positive_creates_apscheduler_job(self, mock_scheduler):
        """_schedule_task should call scheduler.add_job when interval > 0."""
        mock_scheduler.db.get_last_execution_per_task.return_value = {}
        mock_scheduler._schedule_task(
            task_id=1,
            name="Scheduled Task",
            script_path="/path/to/script.py",
            interval=5,
        )
        mock_scheduler.scheduler.add_job.assert_called_once()


class TestRunTaskManualOnly:
    """Tests for running manual-only tasks with run_task."""

    def test_run_task_works_for_manual_only_task(self, mock_scheduler):
        """run_task should execute a task with interval 0 successfully."""
        task = {
            "id": 1,
            "name": "Manual Task",
            "script_path": "/path/to/script.py",
            "arguments": [],
            "interval": 0,
            "task_type": TaskTypes.SCRIPT,
            "command": None,
            "start_time": None,
        }
        mock_scheduler.db.get_all_tasks.return_value = [task]
        mock_scheduler.script_runner.run_script.return_value = True

        result = mock_scheduler.run_task(1)

        assert result is True
        mock_scheduler.script_runner.run_script.assert_called_once()


class TestAddTaskManualOnly:
    """Tests for add_task with interval 0."""

    def test_add_task_interval_zero_logs_manual_only(self, mock_scheduler):
        """add_task log message should show 'manual only' for interval 0."""
        mock_scheduler.db.add_task.return_value = 1

        mock_scheduler.add_task(
            name="Manual Task",
            script_path="/path/to/script.py",
            interval=0,
        )

        # Check the info log contains "manual only"
        log_calls = mock_scheduler.logger.info.call_args_list
        found = any(Defaults.MANUAL_ONLY_LABEL in str(call) for call in log_calls)
        assert found, "Expected 'manual only' in log messages"


class TestEditTaskManualOnly:
    """Tests for edit_task with interval 0."""

    def test_edit_task_interval_zero_removes_old_job(self, mock_scheduler):
        """edit_task should try to remove old job and not schedule new one."""
        mock_scheduler.scheduler.running = True
        mock_scheduler.db.edit_task.return_value = True

        mock_scheduler.edit_task(
            task_id=1,
            name="Manual Task",
            script_path="/path/to/script.py",
            interval=0,
        )

        # Should try to remove old job
        mock_scheduler.scheduler.remove_job.assert_called_once()
        # Should not add a new APScheduler job (only the _schedule_task guard log)
        mock_scheduler.scheduler.add_job.assert_not_called()


class TestListTasksManualOnly:
    """Tests for list_tasks with manual-only tasks."""

    def test_manual_task_has_none_next_run_time(self, mock_scheduler):
        """Manual-only task should have next_run_time = None since no APScheduler job."""
        task = {
            "id": 1,
            "name": "Manual Task",
            "script_path": "/path/to/script.py",
            "arguments": [],
            "interval": 0,
            "task_type": TaskTypes.SCRIPT,
            "command": None,
            "start_time": None,
        }
        mock_scheduler.db.get_all_tasks.return_value = [task]
        mock_scheduler.scheduler.get_jobs.return_value = []
        mock_scheduler.db.get_last_execution_per_task.return_value = {}

        tasks = mock_scheduler.list_tasks()

        assert tasks[0]["next_run_time"] is None

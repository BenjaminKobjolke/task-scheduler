from typing import Dict, List, Optional
import hashlib
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta, time
from .logger import Logger
from .script_runner import ScriptRunner
from .database import Database
from .status_page import StatusPage
from .constants import Paths, Defaults, TaskTypes


class TaskScheduler:
    """Manages scheduled tasks using APScheduler."""

    def __init__(self):
        """Initialize the task scheduler."""
        self.logger = Logger("TaskScheduler")
        self.script_runner = ScriptRunner()
        self.db = Database()

        # Create data directory if it doesn't exist
        os.makedirs(Paths.DATA_DIR, exist_ok=True)

        # Initialize scheduler without persistent job store
        self.scheduler = BackgroundScheduler()
        self.status_page = StatusPage()
        self._task_checksums = {}  # Track task state for hot-reload change detection

    def start(self):
        """Start the scheduler and load tasks from database."""
        # Load all tasks from database
        tasks = self.db.get_all_tasks()
        for task in tasks:
            self._schedule_task(
                task["id"],
                task["name"],
                task["script_path"],
                task["interval"],
                task["arguments"],
                task.get("task_type", TaskTypes.SCRIPT),
                task.get("command"),
                task.get("start_time"),
            )
            # Store initial checksum for hot-reload
            self._task_checksums[task["id"]] = self._get_task_checksum(task)

        # Add periodic hot-reload job to detect database changes
        self.scheduler.add_job(
            func=self._reload_tasks,
            trigger=IntervalTrigger(seconds=Defaults.RELOAD_INTERVAL),
            id="_hot_reload",
            name="Hot-reload task checker",
            replace_existing=True,
        )

        self.scheduler.start()
        self.logger.info(
            f"Scheduler started with {len(tasks)} tasks (hot-reload every {Defaults.RELOAD_INTERVAL}s)"
        )

    def shutdown(self):
        """Shutdown the scheduler."""
        self.scheduler.shutdown()
        self.logger.info("Scheduler shutdown")

    def _get_job_id(self, task_id: int) -> str:
        """Generate a unique job ID for a task.

        Args:
            task_id: ID of the task

        Returns:
            str: Unique job identifier
        """
        return f"job_{task_id}"

    def _get_task_checksum(self, task: Dict) -> str:
        """Generate a checksum of task properties to detect changes.

        Args:
            task: Task dictionary from database

        Returns:
            str: MD5 checksum of task properties
        """
        data = (
            f"{task['name']}|{task['script_path']}|{task['interval']}|"
            f"{task.get('start_time')}|{task['arguments']}|"
            f"{task.get('task_type')}|{task.get('command')}"
        )
        return hashlib.md5(data.encode()).hexdigest()

    def _reload_tasks(self):
        """Check database for changes and update scheduler accordingly (hot-reload)."""
        try:
            db_tasks = self.db.get_all_tasks()
            db_task_ids = {task["id"] for task in db_tasks}
            scheduled_task_ids = set(self._task_checksums.keys())

            # Check for new or modified tasks
            for task in db_tasks:
                task_id = task["id"]
                checksum = self._get_task_checksum(task)

                if task_id not in scheduled_task_ids:
                    # New task - add it
                    self._schedule_task(
                        task_id,
                        task["name"],
                        task["script_path"],
                        task["interval"],
                        task["arguments"],
                        task.get("task_type", TaskTypes.SCRIPT),
                        task.get("command"),
                        task.get("start_time"),
                    )
                    self._task_checksums[task_id] = checksum
                    self.logger.info(
                        f"Hot-reload: Added new task '{task['name']}' (ID: {task_id})"
                    )
                elif self._task_checksums.get(task_id) != checksum:
                    # Task changed - reschedule it
                    try:
                        self.scheduler.remove_job(self._get_job_id(task_id))
                    except Exception:
                        pass  # Job may not exist
                    self._schedule_task(
                        task_id,
                        task["name"],
                        task["script_path"],
                        task["interval"],
                        task["arguments"],
                        task.get("task_type", TaskTypes.SCRIPT),
                        task.get("command"),
                        task.get("start_time"),
                    )
                    self._task_checksums[task_id] = checksum
                    self.logger.info(
                        f"Hot-reload: Updated task '{task['name']}' (ID: {task_id})"
                    )

            # Check for removed tasks
            for task_id in scheduled_task_ids - db_task_ids:
                try:
                    self.scheduler.remove_job(self._get_job_id(task_id))
                except Exception:
                    pass  # Job may not exist
                del self._task_checksums[task_id]
                self.logger.info(f"Hot-reload: Removed task ID {task_id}")

        except Exception as e:
            self.logger.error(f"Error during hot-reload: {str(e)}")

    def _calculate_next_aligned_run(self, start_time: str, interval: int) -> datetime:
        """
        Calculate next run time aligned to start_time grid.

        Args:
            start_time: Start time in HH:MM format
            interval: Interval in minutes

        Returns:
            datetime: Next aligned run time
        """
        now = datetime.now()
        today = now.date()
        hour, minute = map(int, start_time.split(":"))
        anchor = datetime.combine(today, time(hour, minute))

        if now < anchor:
            # Check if there's a slot before the anchor today
            minutes_diff = (anchor - now).total_seconds() / 60
            intervals_back = int(minutes_diff / interval)
            candidate = anchor - timedelta(minutes=intervals_back * interval)
            if candidate <= now:
                return candidate + timedelta(minutes=interval)
            return candidate
        else:
            # Calculate next slot after now
            minutes_since = (now - anchor).total_seconds() / 60
            intervals_passed = int(minutes_since / interval)
            return anchor + timedelta(minutes=(intervals_passed + 1) * interval)

    def _update_status_page(self):
        """Update the status page and sync to FTP if enabled."""
        recent = self.db.get_recent_executions(Defaults.HISTORY_LIMIT)
        jobs = self.scheduler.get_jobs()
        tasks = self.db.get_all_tasks()
        # Sort jobs by next run time
        next_jobs = sorted(jobs, key=lambda x: x.next_run_time) if jobs else []
        self.status_page.update(recent, next_jobs, tasks)

        # Sync to FTP if enabled (errors are logged but don't crash scheduler)
        self.status_page.sync_to_ftp()

    def _process_job(
        self,
        task_id: int,
        name: str,
        script_path: str,
        arguments: List[str],
        task_type: str = TaskTypes.SCRIPT,
        command: Optional[str] = None,
    ) -> bool:
        """
        Process a single job.

        Args:
            task_id: ID of the task
            name: Name of the task
            script_path: Path to the script (or project directory for uv_command)
            arguments: Arguments for the script/command
            task_type: Type of task ('script' or 'uv_command')
            command: Command name for uv_command tasks

        Returns:
            bool: True if execution succeeded, False otherwise
        """
        if task_type == TaskTypes.UV_COMMAND and command:
            success = self.script_runner.run_uv_command(script_path, command, arguments)
        else:
            success = self.script_runner.run_script(script_path, arguments)

        if success:
            self.logger.info(f"Successfully executed task '{name}'")
        else:
            self.logger.error(f"Failed to execute task '{name}'")

        # Record the execution
        self.db.add_task_execution(task_id, success)

        # Update the status page
        self._update_status_page()

        return success

    def _schedule_task(
        self,
        task_id: int,
        name: str,
        script_path: str,
        interval: int,
        arguments: Optional[List[str]] = None,
        task_type: str = TaskTypes.SCRIPT,
        command: Optional[str] = None,
        start_time: Optional[str] = None,
    ):
        """
        Schedule a task in the APScheduler.

        Calculates next_run_time based on last execution to ensure proper scheduling
        for long-interval tasks. If a task is overdue, it runs immediately (catch-up).
        If start_time is provided, aligns execution to the start_time grid.

        Args:
            task_id: ID of the task
            name: Name of the task
            script_path: Path to the Python script or batch file (or project dir for uv_command)
            interval: Interval in minutes
            arguments: Arguments for the script/command
            task_type: Type of task ('script' or 'uv_command')
            command: Command name for uv_command tasks
            start_time: Optional start time for aligned scheduling (HH:MM format)
        """
        # Manual-only tasks (interval 0) don't get an APScheduler job
        if interval == 0:
            self.logger.info(
                f"Task '{name}' (ID: {task_id}) is {Defaults.MANUAL_ONLY_LABEL} — no scheduled job created"
            )
            return

        # Create unique job ID using task ID
        job_id = self._get_job_id(task_id)

        # Get last execution time to calculate proper next_run_time
        last_executions = self.db.get_last_execution_per_task()

        if start_time:
            # Use aligned scheduling based on start_time
            next_run = self._calculate_next_aligned_run(start_time, interval)
            self.logger.debug(
                f"Task '{name}' (ID: {task_id}) using aligned scheduling from {start_time}, "
                f"next run at {next_run.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        elif task_id in last_executions:
            last_run = datetime.strptime(
                last_executions[task_id]["execution_time"], "%Y-%m-%d %H:%M:%S"
            )
            next_run = last_run + timedelta(minutes=interval)

            # If overdue, run immediately (catch-up)
            if next_run < datetime.now():
                self.logger.info(
                    f"Task '{name}' (ID: {task_id}) is overdue, scheduling immediate catch-up"
                )
                next_run = datetime.now()
        else:
            # New task with no execution history, run immediately
            next_run = datetime.now()

        # Scale misfire_grace_time based on interval
        # Minimum 60s, maximum 10% of interval (capped at 1 hour)
        grace_time = max(60, min(interval * 60 * 0.1, 3600))

        # Add the job to the scheduler
        self.scheduler.add_job(
            func=self._process_job,
            trigger=IntervalTrigger(minutes=interval),
            args=[task_id, name, script_path, arguments or [], task_type, command],
            next_run_time=next_run,
            id=job_id,
            replace_existing=True,  # Replace if job exists
            name=name,  # Store task name
            misfire_grace_time=int(grace_time),
            coalesce=True,  # If multiple runs were missed, only run once
        )

    def add_task(
        self,
        name: str,
        script_path: str,
        interval: int,
        arguments: Optional[List[str]] = None,
        task_type: str = TaskTypes.SCRIPT,
        command: Optional[str] = None,
        start_time: Optional[str] = None,
    ):
        """
        Add a new task to both database and scheduler.

        Args:
            name: Name of the task
            script_path: Path to the Python script or batch file (or project dir for uv_command)
            interval: Interval in minutes
            arguments: List of command line arguments for the script/command
            task_type: Type of task ('script' or 'uv_command')
            command: Command name for uv_command tasks
            start_time: Optional start time for aligned scheduling (HH:MM format)
        """
        try:
            # Add to database first and get the task ID
            task_id = self.db.add_task(
                name, script_path, interval, arguments, task_type, command, start_time
            )

            # Schedule the task with the ID
            self._schedule_task(
                task_id,
                name,
                script_path,
                interval,
                arguments,
                task_type,
                command,
                start_time,
            )

            interval_info = Defaults.MANUAL_ONLY_LABEL if interval == 0 else f"{interval} minutes"
            start_time_info = f" starting at {start_time}" if start_time else ""
            if task_type == TaskTypes.UV_COMMAND:
                self.logger.info(
                    f"Added uv command task '{name}': {command} in {script_path} with interval {interval_info}{start_time_info}"
                    f"{' and arguments: ' + ' '.join(arguments) if arguments else ''}"
                )
            else:
                self.logger.info(
                    f"Added task '{name}': {script_path} with interval {interval_info}{start_time_info}"
                    f"{' and arguments: ' + ' '.join(arguments) if arguments else ''}"
                )

            return task_id

        except Exception as e:
            self.logger.error(f"Error adding task '{name}' ({script_path}): {str(e)}")
            raise

    def remove_task(self, task_id: int):
        """
        Remove a task from both database and scheduler.

        Args:
            task_id: ID of the task to remove
        """
        try:
            # Get task details before removal
            tasks = self.db.get_all_tasks()
            task = next((t for t in tasks if t["id"] == task_id), None)

            if task:
                # Remove from database first
                self.db.remove_task(task_id)

                # Only try to remove from scheduler if it's running
                if self.scheduler.running:
                    try:
                        self.scheduler.remove_job(self._get_job_id(task_id))
                    except Exception as e:
                        # Log but don't fail if job removal fails
                        self.logger.warning(
                            f"Could not remove job from scheduler: {str(e)}"
                        )

                self.logger.info(f"Removed task '{task['name']}' (ID: {task_id})")
            else:
                self.logger.error(f"Task with ID {task_id} not found")
                raise ValueError(f"Task with ID {task_id} not found")

        except ValueError:
            # Re-raise ValueError for task not found
            raise
        except Exception as e:
            self.logger.error(f"Error removing task {task_id}: {str(e)}")
            raise

    def edit_task(
        self,
        task_id: int,
        name: str,
        script_path: str,
        interval: int,
        arguments: Optional[List[str]] = None,
        task_type: str = TaskTypes.SCRIPT,
        command: Optional[str] = None,
        start_time: Optional[str] = None,
    ):
        """
        Edit an existing task in both database and scheduler.

        Args:
            task_id: ID of the task to edit
            name: New name for the task
            script_path: New path to the Python script or batch file (or project dir for uv_command)
            interval: New interval in minutes
            arguments: New list of command line arguments
            task_type: Type of task ('script' or 'uv_command')
            command: Command name for uv_command tasks
            start_time: Optional start time for aligned scheduling (HH:MM format)

        Raises:
            ValueError: If task is not found or update fails
        """
        try:
            # Update in database first
            if not self.db.edit_task(
                task_id,
                name,
                script_path,
                interval,
                arguments,
                task_type,
                command,
                start_time,
            ):
                raise ValueError(f"Task with ID {task_id} not found")

            # Update in scheduler if running
            if self.scheduler.running:
                # Remove old job
                try:
                    self.scheduler.remove_job(self._get_job_id(task_id))
                except Exception as e:
                    self.logger.warning(
                        f"Could not remove old job from scheduler: {str(e)}"
                    )

                # Schedule new job
                self._schedule_task(
                    task_id,
                    name,
                    script_path,
                    interval,
                    arguments,
                    task_type,
                    command,
                    start_time,
                )

            interval_info = Defaults.MANUAL_ONLY_LABEL if interval == 0 else f"{interval} minutes"
            start_time_info = f" starting at {start_time}" if start_time else ""
            self.logger.info(
                f"Updated task '{name}' (ID: {task_id}): {script_path} with interval {interval_info}{start_time_info}"
                f"{' and arguments: ' + ' '.join(arguments) if arguments else ''}"
            )

        except Exception as e:
            self.logger.error(f"Error updating task {task_id}: {str(e)}")
            raise

    def list_tasks(self) -> List[Dict]:
        """
        Get a list of all tasks with their next run times and last execution info.

        Returns:
            List of task dictionaries with additional scheduler information
        """
        tasks = self.db.get_all_tasks()
        scheduler_jobs = {job.id: job for job in self.scheduler.get_jobs()}
        last_executions = self.db.get_last_execution_per_task()

        for task in tasks:
            job_id = self._get_job_id(task["id"])
            if job_id in scheduler_jobs:
                task["next_run_time"] = scheduler_jobs[job_id].next_run_time
            else:
                task["next_run_time"] = None

            # Add last execution info
            if task["id"] in last_executions:
                task["last_run_time"] = last_executions[task["id"]]["execution_time"]
                task["last_run_success"] = last_executions[task["id"]]["success"]
            else:
                task["last_run_time"] = None
                task["last_run_success"] = None

        return tasks

    def run_task(self, task_id: int) -> bool:
        """
        Run a specific task by its ID.

        Args:
            task_id: ID of the task to run

        Returns:
            bool: True if execution succeeded, False otherwise

        Raises:
            ValueError: If task with given ID is not found
        """
        try:
            # Get task details from the database
            tasks = self.db.get_all_tasks()
            task = next((t for t in tasks if t["id"] == task_id), None)

            if not task:
                self.logger.error(f"Task with ID {task_id} not found")
                raise ValueError(f"Task with ID {task_id} not found")

            # Run the task and return result
            return self._process_job(
                task["id"],
                task["name"],
                task["script_path"],
                task["arguments"],
                task.get("task_type", TaskTypes.SCRIPT),
                task.get("command"),
            )

        except Exception as e:
            self.logger.error(f"Error running task {task_id}: {str(e)}")
            raise

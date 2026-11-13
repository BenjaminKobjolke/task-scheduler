from __future__ import annotations

import os
from typing import TYPE_CHECKING, Dict, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .constants import Defaults, Paths, TaskTypes
from .database import Database
from .logger import Logger
from .script_runner import ScriptRunner
from .scheduler_hot_reload import SchedulerHotReload
from .scheduler_jobs import SchedulerJobs
from .status_page import StatusPage

if TYPE_CHECKING:
    from .interaction import InteractionHandler, ScriptOutput


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
        self._job_scheduling = SchedulerJobs(
            self.scheduler, self.db, self.logger, self._process_job, self._get_job_id
        )
        self._hot_reload = SchedulerHotReload(
            self.db,
            self.scheduler,
            self.logger,
            self._get_task_checksum,
            self._get_job_id,
            self._schedule_task,
            self._task_checksums,
        )

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
                days_of_month=task.get("days_of_month"),
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

    def shutdown(self, wait: bool = False):
        """Shutdown the scheduler.

        wait=False (default) stops dispatching immediately without blocking on
        jobs already running. Any external script subprocess already launched is a
        separate OS process and keeps running to completion on its own.
        """
        self.scheduler.shutdown(wait=wait)
        self.logger.info("Scheduler shutdown")

    def _get_job_id(self, task_id: int) -> str:
        """Return the stable APScheduler id for a task."""
        return f"job_{task_id}"

    def _get_task_checksum(self, task: Dict) -> str:
        """Hash scheduler-relevant task fields for hot-reload comparison."""
        return SchedulerHotReload.get_task_checksum(task)

    def _reload_tasks(self):
        self._hot_reload.reload_tasks()

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
        interaction_handler: InteractionHandler | None = None,
        script_output: ScriptOutput | None = None,
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
            interaction_handler: Optional handler for interactive prompts
            script_output: Optional output handler for direct console display

        Returns:
            bool: True if execution succeeded, False otherwise
        """
        if task_type == TaskTypes.UV_COMMAND and command:
            success = self.script_runner.run_uv_command(
                script_path,
                command,
                arguments,
                interaction_handler=interaction_handler,
                script_output=script_output,
            )
        else:
            success = self.script_runner.run_script(
                script_path,
                arguments,
                interaction_handler=interaction_handler,
                script_output=script_output,
            )

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
        days_of_month: Optional[str] = None,
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
        self._job_scheduling.schedule_task(
            task_id,
            name,
            script_path,
            interval,
            arguments,
            task_type,
            command,
            start_time,
            days_of_month,
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
        launch_new_process: bool = False,
        days_of_month: Optional[str] = None,
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
            launch_new_process: Whether to launch in a new console window (manual tasks only)
        """
        try:
            # Add to database first and get the task ID
            task_id = self.db.add_task(
                name,
                script_path,
                interval,
                arguments,
                task_type,
                command,
                start_time,
                launch_new_process=launch_new_process,
                days_of_month=days_of_month,
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
                days_of_month=days_of_month,
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
        launch_new_process: bool = False,
        days_of_month: Optional[str] = None,
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
            launch_new_process: Whether to launch in a new console window (manual tasks only)

        Raises:
            ValueError: If task is not found or update fails
        """
        try:
            # Force launch_new_process off for scheduled tasks
            if interval != 0:
                launch_new_process = False

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
                launch_new_process=launch_new_process,
                days_of_month=days_of_month,
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
                    days_of_month=days_of_month,
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

    def run_task(
        self,
        task_id: int,
        interaction_handler: InteractionHandler | None = None,
        script_output: ScriptOutput | None = None,
    ) -> bool:
        """
        Run a specific task by its ID.

        Args:
            task_id: ID of the task to run
            interaction_handler: Optional handler for interactive prompts
            script_output: Optional output handler for direct console display

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

            # Launch in new console if configured
            if task.get("launch_new_process"):
                self.logger.info(
                    f"Launching task '{task['name']}' (ID: {task_id}) in new console window"
                )
                launched = self.script_runner.launch_in_new_console(
                    task["script_path"],
                    task["arguments"],
                    task.get("task_type", TaskTypes.SCRIPT),
                    task.get("command"),
                )
                self.db.add_task_execution(task_id, launched)
                self._update_status_page()
                return launched

            # Run the task and return result
            return self._process_job(
                task["id"],
                task["name"],
                task["script_path"],
                task["arguments"],
                task.get("task_type", TaskTypes.SCRIPT),
                task.get("command"),
                interaction_handler=interaction_handler,
                script_output=script_output,
            )

        except Exception as e:
            self.logger.error(f"Error running task {task_id}: {str(e)}")
            raise

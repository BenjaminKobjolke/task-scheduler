"""Keep scheduled jobs in sync with database task changes."""

import hashlib
from typing import Callable, Dict

from .constants import TaskTypes
from .database import Database
from .logger import Logger


class SchedulerHotReload:
    """Add, update, and remove jobs when persisted tasks change."""

    def __init__(
        self,
        db: Database,
        scheduler,
        logger: Logger,
        get_task_checksum: Callable[[Dict], str],
        get_job_id: Callable[[int], str],
        schedule_task: Callable,
        task_checksums: Dict[int, str],
    ):
        self.db = db
        self.scheduler = scheduler
        self.logger = logger
        self.get_task_checksum = get_task_checksum
        self.get_job_id = get_job_id
        self.schedule_task = schedule_task
        self.task_checksums = task_checksums

    @staticmethod
    def get_task_checksum(task: Dict) -> str:
        """Hash scheduler-relevant task fields for change detection."""
        data = (
            f"{task['name']}|{task['script_path']}|{task['interval']}|"
            f"{task.get('start_time')}|{task['arguments']}|"
            f"{task.get('task_type')}|{task.get('command')}|"
            f"{task.get('launch_new_process', False)}|{task.get('days_of_month')}"
        )
        return hashlib.md5(data.encode()).hexdigest()

    def reload_tasks(self) -> None:
        """Check database tasks and update their scheduled jobs."""
        try:
            db_tasks = self.db.get_all_tasks()
            db_task_ids = {task["id"] for task in db_tasks}
            scheduled_task_ids = set(self.task_checksums)

            for task in db_tasks:
                task_id = task["id"]
                checksum = self.get_task_checksum(task)

                if task_id not in scheduled_task_ids:
                    self.schedule_task_from_record(task)
                    self.task_checksums[task_id] = checksum
                    self.logger.info(
                        f"Hot-reload: Added new task '{task['name']}' (ID: {task_id})"
                    )
                elif self.task_checksums.get(task_id) != checksum:
                    try:
                        self.scheduler.remove_job(self.get_job_id(task_id))
                    except Exception:
                        pass  # The job may no longer exist.
                    self.schedule_task_from_record(task)
                    self.task_checksums[task_id] = checksum
                    self.logger.info(
                        f"Hot-reload: Updated task '{task['name']}' (ID: {task_id})"
                    )

            for task_id in scheduled_task_ids - db_task_ids:
                try:
                    self.scheduler.remove_job(self.get_job_id(task_id))
                except Exception:
                    pass  # The job may no longer exist.
                del self.task_checksums[task_id]
                self.logger.info(f"Hot-reload: Removed task ID {task_id}")

        except Exception as error:
            self.logger.error(f"Error during hot-reload: {str(error)}")

    def schedule_task_from_record(self, task: Dict) -> None:
        """Schedule a database task using the scheduler's stable call shape."""
        self.schedule_task(
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

"""Create APScheduler jobs for persisted tasks."""

from datetime import datetime, time, timedelta
from typing import Callable, Dict, List, Optional

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from .constants import Defaults, TaskTypes
from .database import Database
from .logger import Logger
from .month_days import cron_fields, next_monthly_run


class SchedulerJobs:
    """Own interval and calendar job configuration."""

    def __init__(
        self,
        scheduler,
        db: Database,
        logger: Logger,
        process_job: Callable,
        get_job_id: Callable[[int], str],
    ):
        self.scheduler = scheduler
        self.db = db
        self.logger = logger
        self.process_job = process_job
        self.get_job_id = get_job_id

    def calculate_next_aligned_run(self, start_time: str, interval: int) -> datetime:
        """Calculate the next run time aligned to the start-time grid."""
        now = datetime.now()
        today = now.date()
        hour, minute = map(int, start_time.split(":"))
        anchor = datetime.combine(today, time(hour, minute))

        if now < anchor:
            minutes_diff = (anchor - now).total_seconds() / 60
            intervals_back = int(minutes_diff / interval)
            candidate = anchor - timedelta(minutes=intervals_back * interval)
            if candidate <= now:
                return candidate + timedelta(minutes=interval)
            return candidate

        minutes_since = (now - anchor).total_seconds() / 60
        intervals_passed = int(minutes_since / interval)
        return anchor + timedelta(minutes=(intervals_passed + 1) * interval)

    def schedule_task(
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
    ) -> None:
        """Create an interval or calendar job for one task."""
        if interval == 0:
            self.logger.info(
                f"Task '{name}' (ID: {task_id}) is {Defaults.MANUAL_ONLY_LABEL} — no scheduled job created"
            )
            return

        job_id = self.get_job_id(task_id)
        last_executions = self.db.get_last_execution_per_task()

        if days_of_month:
            self.schedule_days_task(
                task_id,
                name,
                script_path,
                arguments,
                task_type,
                command,
                start_time,
                days_of_month,
                last_executions.get(task_id),
            )
            return

        if start_time:
            next_run = self.calculate_next_aligned_run(start_time, interval)
            self.logger.debug(
                f"Task '{name}' (ID: {task_id}) using aligned scheduling from {start_time}, "
                f"next run at {next_run.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        elif task_id in last_executions:
            last_run = datetime.strptime(
                last_executions[task_id]["execution_time"], "%Y-%m-%d %H:%M:%S"
            )
            next_run = last_run + timedelta(minutes=interval)
            if next_run < datetime.now():
                self.logger.info(
                    f"Task '{name}' (ID: {task_id}) is overdue, scheduling immediate catch-up"
                )
                next_run = datetime.now()
        else:
            next_run = datetime.now()

        grace_time = max(60, min(interval * 60 * 0.1, 3600))
        self.scheduler.add_job(
            func=self.process_job,
            trigger=IntervalTrigger(minutes=interval),
            args=[task_id, name, script_path, arguments or [], task_type, command],
            next_run_time=next_run,
            id=job_id,
            replace_existing=True,
            name=name,
            misfire_grace_time=int(grace_time),
            coalesce=True,
        )

    def schedule_days_task(
        self,
        task_id: int,
        name: str,
        script_path: str,
        arguments: Optional[List[str]],
        task_type: str,
        command: Optional[str],
        start_time: Optional[str],
        days_of_month: str,
        last_execution: Optional[Dict],
    ) -> None:
        """Create a cron job that runs on selected days of the month."""
        now = datetime.now()
        last_run = (
            datetime.strptime(last_execution["execution_time"], "%Y-%m-%d %H:%M:%S")
            if last_execution
            else None
        )
        next_run = next_monthly_run(days_of_month, start_time, last_run, now)
        self.logger.info(
            f"Task '{name}' (ID: {task_id}) runs on days {days_of_month}, "
            f"next run at {next_run.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.scheduler.add_job(
            func=self.process_job,
            trigger=CronTrigger(**cron_fields(days_of_month, start_time)),
            args=[task_id, name, script_path, arguments or [], task_type, command],
            next_run_time=next_run,
            id=self.get_job_id(task_id),
            replace_existing=True,
            name=name,
            misfire_grace_time=Defaults.DAYS_MISFIRE_GRACE_TIME,
            coalesce=True,
        )

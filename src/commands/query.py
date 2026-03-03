import sys

from ..cli_output import CliOutput
from ..config import Config
from ..formatters import format_execution_history, format_task_list
from ..interaction import CliInteractionHandler
from ..scheduler import TaskScheduler
from ..status_page import StatusPage


def handle_list(scheduler: TaskScheduler, cli: CliOutput, filter_term: str) -> None:
    """List scheduled tasks and exit."""
    tasks = scheduler.list_tasks()
    if filter_term:
        filter_lower = filter_term.lower()
        tasks = [t for t in tasks if filter_lower in t["name"].lower()]
    cli.info("Scheduled tasks:" + format_task_list(tasks, show_next_run=False))


def handle_history(scheduler: TaskScheduler, cli: CliOutput, count: int) -> None:
    """Show execution history and exit."""
    executions = scheduler.db.get_recent_executions(count)
    cli.info("Recent task executions:\n" + format_execution_history(executions))


def handle_run_id(scheduler: TaskScheduler, cli: CliOutput, task_id: int) -> None:
    """Run a specific task by its ID."""
    tasks = scheduler.list_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)

    if not task:
        cli.error(f"No task found with ID {task_id}")
        sys.exit(1)

    cli.info(f"Running task {task['name']} (ID: {task['id']})")
    try:
        handler = CliInteractionHandler()
        scheduler.run_task(task["id"], interaction_handler=handler)
    except Exception as e:
        cli.error(f"Error running task {task['name']} (ID: {task['id']}): {str(e)}")
        sys.exit(1)


def handle_ftp_sync(cli: CliOutput, config: Config) -> None:
    """Manually trigger FTP sync of the status page."""
    status_page = StatusPage()
    cli.info(f"Starting FTP sync from {status_page.get_output_dir()}")

    if not config.is_ftp_enabled():
        cli.warning(
            "FTP sync is disabled in config. Enable it first in config.ini [FTP] section."
        )
        sys.exit(1)

    if status_page.sync_to_ftp():
        cli.info("FTP sync completed successfully")
    else:
        cli.error("FTP sync failed")
        sys.exit(1)

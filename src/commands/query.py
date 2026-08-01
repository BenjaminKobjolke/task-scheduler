import sys

from ..cli_output import CliOutput
from ..config import Config
from ..constants import Messages
from ..formatters import format_execution_history, format_task_list
from ..interaction import CliInteractionHandler, ConsoleScriptOutput
from ..scheduler import TaskScheduler
from ..status_page import StatusPage
from ..task_queries import filter_tasks_by_name


def handle_list(scheduler: TaskScheduler, cli: CliOutput, filter_term: str) -> None:
    """List scheduled tasks and exit."""
    tasks = filter_tasks_by_name(scheduler.list_tasks(), filter_term)
    cli.info("Scheduled tasks:" + format_task_list(tasks, show_next_run=False))


def handle_run_name(
    scheduler: TaskScheduler, cli: CliOutput, filter_term: str
) -> None:
    """Select and run a task from case-insensitive partial-name matches."""
    tasks = filter_tasks_by_name(scheduler.list_tasks(), filter_term)
    if not tasks:
        cli.error(Messages.RUN_NAME_NO_MATCHES.format(filter_term=filter_term))
        sys.exit(1)

    choices = "\n".join(
        Messages.RUN_NAME_CHOICE.format(
            position=position,
            name=task["name"],
            task_id=task["id"],
        )
        for position, task in enumerate(tasks, start=1)
    )
    cli.info(f"{Messages.RUN_NAME_MATCHES}\n{choices}")
    selected_task = _prompt_for_task_selection(tasks, cli)
    handle_run_id(scheduler, cli, selected_task["id"])


def _prompt_for_task_selection(tasks: list[dict], cli: CliOutput) -> dict:
    """Prompt until the user selects a valid one-based task position."""
    task_count = len(tasks)
    while True:
        selection = input(Messages.RUN_NAME_PROMPT.format(count=task_count)).strip()
        try:
            selection_index = int(selection) - 1
        except ValueError:
            selection_index = -1

        if 0 <= selection_index < task_count:
            return tasks[selection_index]

        cli.error(Messages.RUN_NAME_INVALID_SELECTION.format(count=task_count))


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

    if task.get("launch_new_process"):
        cli.info(
            f"Launching task {task['name']} (ID: {task['id']}) in new console window..."
        )
        try:
            scheduler.run_task(task["id"])
        except Exception as e:
            cli.error(
                f"Error launching task {task['name']} (ID: {task['id']}): {str(e)}"
            )
            sys.exit(1)
    else:
        cli.info(f"Running task {task['name']} (ID: {task['id']})")
        try:
            handler = CliInteractionHandler()
            output = ConsoleScriptOutput()
            scheduler.run_task(
                task["id"], interaction_handler=handler, script_output=output
            )
        except Exception as e:
            cli.error(
                f"Error running task {task['name']} (ID: {task['id']}): {str(e)}"
            )
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

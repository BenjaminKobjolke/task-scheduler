import os
import sys
from argparse import Namespace

from ..cli_input import get_task_input
from ..constants import Paths, TaskTypes
from ..formatters import format_task_list
from ..logger import Logger
from ..scheduler import TaskScheduler


def _log_task_details(logger: Logger, task_details: dict) -> None:
    """Log task details after add/edit."""
    logger.info(f"Name: {task_details['name']}")
    if task_details.get("task_type") == TaskTypes.UV_COMMAND:
        logger.info("Type: uv command")
        logger.info(f"Project: {task_details['script_path']}")
        logger.info(f"Command: {task_details.get('command')}")
    else:
        logger.info(f"Script: {task_details['script_path']}")
    logger.info(f"Interval: {task_details['interval']} minute(s)")
    if task_details.get("start_time"):
        logger.info(f"Start time: {task_details['start_time']}")
    if task_details.get("arguments"):
        logger.info(f"Arguments: {' '.join(task_details['arguments'])}")


def handle_add(scheduler: TaskScheduler, logger: Logger) -> None:
    """Add a new task interactively."""
    task_details = get_task_input()

    scheduler.add_task(
        name=task_details["name"],
        script_path=os.path.abspath(task_details["script_path"]),
        interval=task_details["interval"],
        arguments=task_details["arguments"],
        task_type=task_details.get("task_type", TaskTypes.SCRIPT),
        command=task_details.get("command"),
        start_time=task_details.get("start_time"),
    )

    logger.info("Task added successfully:")
    _log_task_details(logger, task_details)


def handle_edit(scheduler: TaskScheduler, logger: Logger, task_id: int) -> None:
    """Edit a task interactively."""
    tasks = scheduler.list_tasks()
    task = next((t for t in tasks if t['id'] == task_id), None)

    if not task:
        logger.error(f"No task found with ID {task_id}")
        sys.exit(1)

    logger.info("\nEditing task:")
    logger.info(format_task_list([task], show_next_run=False))

    task_details = get_task_input(task)

    try:
        scheduler.edit_task(
            task_id=task_id,
            name=task_details["name"],
            script_path=os.path.abspath(task_details["script_path"]),
            interval=task_details["interval"],
            arguments=task_details["arguments"],
            task_type=task_details.get("task_type", TaskTypes.SCRIPT),
            command=task_details.get("command"),
            start_time=task_details.get("start_time"),
        )
        logger.info("Task updated successfully:")
        _log_task_details(logger, task_details)
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)


def handle_delete(scheduler: TaskScheduler, logger: Logger, task_id: int) -> None:
    """Delete a task by ID after confirmation."""
    tasks = scheduler.list_tasks()
    task = next((t for t in tasks if t['id'] == task_id), None)

    if not task:
        logger.error(f"No task found with ID {task_id}")
        sys.exit(1)

    logger.info("\nTask to delete:")
    logger.info(format_task_list([task], show_next_run=False))

    confirmation = input("\nAre you sure you want to delete this task? (y/N): ")
    if confirmation.lower() == 'y':
        try:
            scheduler.remove_task(task_id)
            logger.info("Task deleted successfully")
        except ValueError as e:
            logger.error(str(e))
            sys.exit(1)
    else:
        logger.info("Deletion cancelled")


def handle_script(scheduler: TaskScheduler, logger: Logger, args) -> None:
    """Add a new task via CLI arguments."""
    if not args.name:
        logger.error("--name is required when adding a new task")
        sys.exit(1)

    if not args.interval:
        logger.error("--interval is required when adding a new task")
        sys.exit(1)

    if args.interval < 1:
        logger.error("Interval must be at least 1 minute")
        sys.exit(1)

    start_time = None
    if args.start_time:
        try:
            from datetime import datetime
            datetime.strptime(args.start_time, "%H:%M")
            start_time = args.start_time
        except ValueError:
            logger.error(f"Invalid start time format: {args.start_time}. Use HH:MM format (e.g., 09:00).")
            sys.exit(1)

    script_path = os.path.abspath(args.script)
    script_args = args.script_args[1:] if args.script_args and args.script_args[0] == '--' else args.script_args

    scheduler.add_task(args.name, script_path, args.interval, script_args, start_time=start_time)

    logger.info("Task added successfully:")
    logger.info(f"Name: {args.name}")
    logger.info(f"Script: {script_path}")
    logger.info(f"Interval: {args.interval} minute(s)")
    if start_time:
        logger.info(f"Start time: {start_time}")
    if script_args:
        logger.info(f"Arguments: {' '.join(script_args)}")


def handle_copy_task(scheduler: TaskScheduler, logger: Logger, task_id: int) -> None:
    """Copy an existing task."""
    tasks = scheduler.list_tasks()
    task = next((t for t in tasks if t['id'] == task_id), None)

    if not task:
        logger.error(f"No task found with ID {task_id}")
        sys.exit(1)

    try:
        new_task_id = scheduler.add_task(
            name=task['name'] + " (copy)",
            script_path=task['script_path'],
            interval=task['interval'],
            arguments=task['arguments'] if task['arguments'] else None,
            task_type=task.get('task_type', TaskTypes.SCRIPT),
            command=task.get('command'),
            start_time=task.get('start_time'),
        )
        logger.info(f"Task '{task['name']}' (ID: {task['id']}) copied successfully as new task (ID: {new_task_id})")
    except Exception as e:
        logger.error(f"Failed to copy task: {str(e)}")
        sys.exit(1)


def handle_uv_command(scheduler: TaskScheduler, logger: Logger, args: Namespace) -> None:
    """Add a new uv command task via CLI arguments."""
    if not args.name:
        logger.error("--name is required when adding a new task")
        sys.exit(1)

    if args.interval is None:
        logger.error("--interval is required when adding a new task")
        sys.exit(1)

    if args.interval < 1:
        logger.error("Interval must be at least 1 minute")
        sys.exit(1)

    project_dir, command_name = args.uv_command

    if not os.path.isdir(project_dir):
        logger.error(f"Project directory does not exist: {project_dir}")
        sys.exit(1)

    if not os.path.isfile(os.path.join(project_dir, Paths.PYPROJECT_TOML)):
        logger.error(f"Not a valid uv project: missing {Paths.PYPROJECT_TOML} in {project_dir}")
        sys.exit(1)

    if not os.path.isfile(os.path.join(project_dir, Paths.UV_LOCK)):
        logger.error(f"Not a valid uv project: missing {Paths.UV_LOCK} in {project_dir}")
        sys.exit(1)

    start_time = None
    if args.start_time:
        try:
            from datetime import datetime
            datetime.strptime(args.start_time, "%H:%M")
            start_time = args.start_time
        except ValueError:
            logger.error(f"Invalid start time format: {args.start_time}. Use HH:MM format (e.g., 09:00).")
            sys.exit(1)

    script_args = args.script_args[1:] if args.script_args and args.script_args[0] == '--' else args.script_args

    scheduler.add_task(
        name=args.name,
        script_path=project_dir,
        interval=args.interval,
        arguments=script_args,
        task_type=TaskTypes.UV_COMMAND,
        command=command_name,
        start_time=start_time,
    )

    task_details = {
        "name": args.name,
        "script_path": project_dir,
        "interval": args.interval,
        "task_type": TaskTypes.UV_COMMAND,
        "command": command_name,
        "start_time": start_time,
        "arguments": script_args,
    }
    logger.info("Task added successfully:")
    _log_task_details(logger, task_details)

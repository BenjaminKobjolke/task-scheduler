import os
import sys
from argparse import Namespace

from ..cli_input import get_task_input
from ..cli_output import CliOutput
from ..constants import Defaults, Paths, TaskTypes
from ..formatters import format_task_list
from ..scheduler import TaskScheduler


def _log_task_details(cli: CliOutput, task_details: dict) -> None:
    """Log task details after add/edit."""
    cli.info(f"Name: {task_details['name']}")
    if task_details.get("task_type") == TaskTypes.UV_COMMAND:
        cli.info("Type: uv command")
        cli.info(f"Project: {task_details['script_path']}")
        cli.info(f"Command: {task_details.get('command')}")
    else:
        cli.info(f"Script: {task_details['script_path']}")
    interval = task_details["interval"]
    interval_display = Defaults.MANUAL_ONLY_LABEL if interval == 0 else f"{interval} minute(s)"
    cli.info(f"Interval: {interval_display}")
    if task_details.get("start_time"):
        cli.info(f"Start time: {task_details['start_time']}")
    if task_details.get("arguments"):
        cli.info(f"Arguments: {' '.join(task_details['arguments'])}")


def handle_add(scheduler: TaskScheduler, cli: CliOutput) -> None:
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

    cli.info("Task added successfully:")
    _log_task_details(cli, task_details)


def handle_edit(scheduler: TaskScheduler, cli: CliOutput, task_id: int) -> None:
    """Edit a task interactively."""
    tasks = scheduler.list_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)

    if not task:
        cli.error(f"No task found with ID {task_id}")
        sys.exit(1)

    cli.info("\nEditing task:")
    cli.info(format_task_list([task], show_next_run=False))

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
        cli.info("Task updated successfully:")
        _log_task_details(cli, task_details)
    except ValueError as e:
        cli.error(str(e))
        sys.exit(1)


def handle_delete(scheduler: TaskScheduler, cli: CliOutput, task_id: int) -> None:
    """Delete a task by ID after confirmation."""
    tasks = scheduler.list_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)

    if not task:
        cli.error(f"No task found with ID {task_id}")
        sys.exit(1)

    cli.info("\nTask to delete:")
    cli.info(format_task_list([task], show_next_run=False))

    confirmation = input("\nAre you sure you want to delete this task? (y/N): ")
    if confirmation.lower() == "y":
        try:
            scheduler.remove_task(task_id)
            cli.info("Task deleted successfully")
        except ValueError as e:
            cli.error(str(e))
            sys.exit(1)
    else:
        cli.info("Deletion cancelled")


def handle_script(scheduler: TaskScheduler, cli: CliOutput, args) -> None:
    """Add a new task via CLI arguments."""
    if not args.name:
        cli.error("--name is required when adding a new task")
        sys.exit(1)

    if not args.interval:
        cli.error("--interval is required when adding a new task")
        sys.exit(1)

    if args.interval < 0:
        cli.error("Interval must be 0 or higher. Use 0 for manual-only tasks.")
        sys.exit(1)

    start_time = None
    if args.start_time:
        if args.interval == 0:
            cli.error("Start time is not applicable for manual-only tasks (interval 0).")
            sys.exit(1)
        try:
            from datetime import datetime

            datetime.strptime(args.start_time, "%H:%M")
            start_time = args.start_time
        except ValueError:
            cli.error(
                f"Invalid start time format: {args.start_time}. Use HH:MM format (e.g., 09:00)."
            )
            sys.exit(1)

    script_path = os.path.abspath(args.script)
    script_args = (
        args.script_args[1:]
        if args.script_args and args.script_args[0] == "--"
        else args.script_args
    )

    scheduler.add_task(
        args.name, script_path, args.interval, script_args, start_time=start_time
    )

    interval_display = Defaults.MANUAL_ONLY_LABEL if args.interval == 0 else f"{args.interval} minute(s)"
    cli.info("Task added successfully:")
    cli.info(f"Name: {args.name}")
    cli.info(f"Script: {script_path}")
    cli.info(f"Interval: {interval_display}")
    if start_time:
        cli.info(f"Start time: {start_time}")
    if script_args:
        cli.info(f"Arguments: {' '.join(script_args)}")


def handle_copy_task(scheduler: TaskScheduler, cli: CliOutput, task_id: int) -> None:
    """Copy an existing task."""
    tasks = scheduler.list_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)

    if not task:
        cli.error(f"No task found with ID {task_id}")
        sys.exit(1)

    try:
        new_task_id = scheduler.add_task(
            name=task["name"] + " (copy)",
            script_path=task["script_path"],
            interval=task["interval"],
            arguments=task["arguments"] if task["arguments"] else None,
            task_type=task.get("task_type", TaskTypes.SCRIPT),
            command=task.get("command"),
            start_time=task.get("start_time"),
        )
        cli.info(
            f"Task '{task['name']}' (ID: {task['id']}) copied successfully as new task (ID: {new_task_id})"
        )
    except Exception as e:
        cli.error(f"Failed to copy task: {str(e)}")
        sys.exit(1)


def handle_uv_command(
    scheduler: TaskScheduler, cli: CliOutput, args: Namespace
) -> None:
    """Add a new uv command task via CLI arguments."""
    if not args.name:
        cli.error("--name is required when adding a new task")
        sys.exit(1)

    if args.interval is None:
        cli.error("--interval is required when adding a new task")
        sys.exit(1)

    if args.interval < 0:
        cli.error("Interval must be 0 or higher. Use 0 for manual-only tasks.")
        sys.exit(1)

    project_dir, command_name = args.uv_command

    if not os.path.isdir(project_dir):
        cli.error(f"Project directory does not exist: {project_dir}")
        sys.exit(1)

    if not os.path.isfile(os.path.join(project_dir, Paths.PYPROJECT_TOML)):
        cli.error(
            f"Not a valid uv project: missing {Paths.PYPROJECT_TOML} in {project_dir}"
        )
        sys.exit(1)

    if not os.path.isfile(os.path.join(project_dir, Paths.UV_LOCK)):
        cli.error(
            f"Not a valid uv project: missing {Paths.UV_LOCK} in {project_dir}"
        )
        sys.exit(1)

    start_time = None
    if args.start_time:
        try:
            from datetime import datetime

            datetime.strptime(args.start_time, "%H:%M")
            start_time = args.start_time
        except ValueError:
            cli.error(
                f"Invalid start time format: {args.start_time}. Use HH:MM format (e.g., 09:00)."
            )
            sys.exit(1)

    script_args = (
        args.script_args[1:]
        if args.script_args and args.script_args[0] == "--"
        else args.script_args
    )

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
    cli.info("Task added successfully:")
    _log_task_details(cli, task_details)

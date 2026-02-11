import shlex
import sys
from datetime import datetime
from typing import List

from prompt_toolkit import PromptSession

from ..cli_input import _create_path_key_bindings
from ..constants import TaskTypes
from ..logger import Logger
from ..scheduler import TaskScheduler


def handle_set_start_time(
    scheduler: TaskScheduler, logger: Logger, task_id_str: str, time_value: str
) -> None:
    """Set or clear start time for a task."""
    try:
        task_id = int(task_id_str)
    except ValueError:
        logger.error(f"Invalid task ID: {task_id_str}")
        sys.exit(1)

    tasks = scheduler.list_tasks()
    task = next((t for t in tasks if t['id'] == task_id), None)

    if not task:
        logger.error(f"No task found with ID {task_id}")
        sys.exit(1)

    if time_value.lower() == 'none':
        new_start_time = None
    else:
        try:
            datetime.strptime(time_value, "%H:%M")
            new_start_time = time_value
        except ValueError:
            logger.error(f"Invalid time format: {time_value}. Use HH:MM format or 'none' to clear.")
            sys.exit(1)

    try:
        scheduler.edit_task(
            task_id=task_id,
            name=task['name'],
            script_path=task['script_path'],
            interval=task['interval'],
            arguments=task['arguments'],
            task_type=task.get('task_type', TaskTypes.SCRIPT),
            command=task.get('command'),
            start_time=new_start_time,
        )
        if new_start_time:
            logger.info(f"Task '{task['name']}' (ID: {task_id}) start time set to {new_start_time}")
        else:
            logger.info(f"Task '{task['name']}' (ID: {task_id}) start time cleared")
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)


def handle_set_interval(
    scheduler: TaskScheduler, logger: Logger, task_id_str: str, interval_str: str
) -> None:
    """Set interval for a task."""
    try:
        task_id = int(task_id_str)
    except ValueError:
        logger.error(f"Invalid task ID: {task_id_str}")
        sys.exit(1)

    try:
        new_interval = int(interval_str)
        if new_interval < 1:
            logger.error("Interval must be at least 1 minute")
            sys.exit(1)
    except ValueError:
        logger.error(f"Invalid interval: {interval_str}. Must be a positive integer.")
        sys.exit(1)

    tasks = scheduler.list_tasks()
    task = next((t for t in tasks if t['id'] == task_id), None)

    if not task:
        logger.error(f"No task found with ID {task_id}")
        sys.exit(1)

    try:
        scheduler.edit_task(
            task_id=task_id,
            name=task['name'],
            script_path=task['script_path'],
            interval=new_interval,
            arguments=task['arguments'],
            task_type=task.get('task_type', TaskTypes.SCRIPT),
            command=task.get('command'),
            start_time=task.get('start_time'),
        )
        logger.info(f"Task '{task['name']}' (ID: {task_id}) interval set to {new_interval} minute(s)")
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)


def handle_set_arguments(scheduler: TaskScheduler, logger: Logger, task_id: int) -> None:
    """Interactively set arguments for a task."""
    tasks = scheduler.list_tasks()
    task = next((t for t in tasks if t['id'] == task_id), None)

    if not task:
        logger.error(f"No task found with ID {task_id}")
        sys.exit(1)

    print(f"\nTask: {task['name']} (ID: {task_id})")
    print(f"Current arguments: {' '.join(task['arguments']) if task['arguments'] else 'None'}")
    print("\nEnter new arguments (press Enter to keep current, type 'none' to clear):")
    print("Example: --source \"path/to/source\" --target \"path/to/target\"")

    kb = _create_path_key_bindings()
    session = PromptSession()
    new_arguments = None
    arg_lines: List[str] = []
    while True:
        arg = session.prompt("> ", key_bindings=kb).strip()
        if not arg:
            if not arg_lines and task['arguments']:
                new_arguments = task['arguments']
            elif arg_lines:
                full_input = ' '.join(arg_lines)
                if full_input.lower() == 'none':
                    new_arguments = None
                else:
                    new_arguments = shlex.split(full_input)
            break
        arg_lines.append(arg)

    try:
        scheduler.edit_task(
            task_id=task_id,
            name=task['name'],
            script_path=task['script_path'],
            interval=task['interval'],
            arguments=new_arguments,
            task_type=task.get('task_type', TaskTypes.SCRIPT),
            command=task.get('command'),
            start_time=task.get('start_time'),
        )
        if new_arguments:
            logger.info(f"Task '{task['name']}' (ID: {task_id}) arguments set to: {' '.join(new_arguments)}")
        else:
            logger.info(f"Task '{task['name']}' (ID: {task_id}) arguments cleared")
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

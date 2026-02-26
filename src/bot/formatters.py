"""Compact formatters for bot chat output."""

from typing import Dict, List

from ..constants import TaskTypes
from .constants import Messages


def format_task_list_compact(tasks: List[Dict]) -> str:
    """Format tasks for chat - one line per task.

    Format: "ID. Name [interval] [uv] (last: status)"
    e.g.: "1. Backup Script [60min] (last: success)"
    """
    if not tasks:
        return Messages.NO_TASKS

    lines: List[str] = []
    for task in tasks:
        task_type = task.get("task_type", TaskTypes.SCRIPT)
        line = f"{task['id']}. {task['name']} [{task['interval']}min]"

        if task_type == TaskTypes.UV_COMMAND:
            line += " [uv]"

        last_run_time = task.get("last_run_time")
        if last_run_time:
            status = "success" if task.get("last_run_success") else "failed"
            line += f" (last: {status})"
        else:
            line += " (never run)"

        lines.append(line)

    return "\n".join(lines)


def format_task_detail(task: Dict) -> str:
    """Format a single task with full details for chat."""
    task_type = task.get("task_type", TaskTypes.SCRIPT)
    lines: List[str] = []

    lines.append(f"Task #{task['id']}: {task['name']}")

    if task_type == TaskTypes.UV_COMMAND:
        lines.append("Type: uv command")
        lines.append(f"Project: {task['script_path']}")
        lines.append(f"Command: {task.get('command', 'N/A')}")
    else:
        lines.append("Type: script")
        lines.append(f"Script: {task['script_path']}")

    lines.append(f"Interval: {task['interval']} min")

    start_time = task.get("start_time")
    if start_time:
        lines.append(f"Start time: {start_time}")

    arguments = task.get("arguments", [])
    if arguments:
        lines.append(f"Arguments: {' '.join(arguments)}")
    else:
        lines.append("Arguments: None")

    last_run_time = task.get("last_run_time")
    if last_run_time:
        status = "success" if task.get("last_run_success") else "failed"
        lines.append(f"Last run: {last_run_time} ({status})")
    else:
        lines.append("Last run: Never")

    next_run_time = task.get("next_run_time")
    if next_run_time:
        lines.append(f"Next run: {next_run_time}")

    return "\n".join(lines)


def format_execution_history_compact(executions: List[Dict]) -> str:
    """Format execution history for chat.

    Format: "Time - Name - Status"
    """
    if not executions:
        return Messages.NO_HISTORY

    lines: List[str] = []
    for execution in executions:
        status = "success" if execution["success"] else "failed"
        line = f"{execution['execution_time']} - {execution['name']} - {status}"
        lines.append(line)

    return "\n".join(lines)


def format_add_summary(data: Dict) -> str:
    """Format add wizard summary for confirmation."""
    task_type = data.get("task_type", TaskTypes.SCRIPT)
    lines: List[str] = []

    lines.append(f"Name: {data['name']}")

    if task_type == TaskTypes.UV_COMMAND:
        lines.append("Type: uv command")
        lines.append(f"Project: {data['script_path']}")
        command = data.get("command", "")
        if command:
            lines.append(f"Command: {command}")
    else:
        lines.append("Type: script")
        lines.append(f"Script: {data['script_path']}")

    lines.append(f"Interval: {data['interval']} min")

    start_time = data.get("start_time")
    if start_time:
        lines.append(f"Start time: {start_time}")

    arguments = data.get("arguments", "")
    if arguments:
        lines.append(f"Arguments: {arguments}")

    return "\n".join(lines)


def format_edit_changes(original: Dict, changes: Dict) -> str:
    """Format edit wizard change summary."""
    if not changes:
        return Messages.WIZARD_EDIT_NO_CHANGES

    lines: List[str] = []
    for key, new_value in changes.items():
        old_value = original.get(key, "")
        lines.append(f"{key}: {old_value} -> {new_value}")

    return "\n".join(lines)

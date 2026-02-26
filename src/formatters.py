from typing import Dict, List

from .constants import TaskTypes


def format_execution_history(executions: List[Dict]) -> str:
    """Format execution history for display."""
    if not executions:
        return "No execution history found."

    output = []
    for i, execution in enumerate(executions, 1):
        status = "Success" if execution["success"] else "Failed"
        status_symbol = "+" if execution["success"] else "-"
        output.append(
            f"{i}. {execution['execution_time']} - {execution['name']} - [{status_symbol}] {status}"
        )
    return "\n".join(output)


def format_task_list(tasks: List[Dict], show_next_run: bool = True) -> str:
    """Format task list for display."""
    if not tasks:
        return "No tasks scheduled."

    output = []
    for task in tasks:
        task_type = task.get("task_type", TaskTypes.SCRIPT)

        start_time = task.get("start_time")
        if task_type == TaskTypes.UV_COMMAND:
            lines = [
                f"\n{task['id']}. {task['name']} [uv command]",
                f"   Project: {task['script_path']}",
                f"   Command: {task.get('command', 'N/A')}",
                f"   Interval: {task['interval']} minute(s)",
            ]
        else:
            lines = [
                f"\n{task['id']}. {task['name']}",
                f"   Script: {task['script_path']}",
                f"   Interval: {task['interval']} minute(s)",
            ]

        if start_time:
            lines.append(f"   Start time: {start_time}")

        lines.append(
            f"   Arguments: {' '.join(task['arguments']) if task['arguments'] else 'None'}"
        )

        # Add last run info
        last_run_time = task.get("last_run_time")
        if last_run_time:
            success_str = "success" if task.get("last_run_success") else "failed"
            lines.append(f"   Last run: {last_run_time} ({success_str})")
        else:
            lines.append("   Last run: Never")

        if show_next_run:
            next_run = (
                task["next_run_time"].strftime("%Y-%m-%d %H:%M:%S")
                if task["next_run_time"]
                else "Not scheduled"
            )
            lines.append(f"   Next run: {next_run}")
        output.extend(lines)
    return "\n".join(output)

from typing import Dict, List

from .constants import Defaults, TaskTypes


_INTERVAL_SUFFIX_MINUTES = {
    "m": 1,
    "h": 60,
    "d": 1440,
    "w": 10080,
}


def parse_interval(value: str) -> int:
    """Parse a user-supplied interval string into minutes.

    Accepted forms:
        "5"  -> 5 minutes (bare integer)
        "5m" -> 5 minutes
        "4h" -> 240 minutes
        "7d" -> 10080 minutes
        "1w" -> 10080 minutes
        "0"  -> 0 (manual-only)

    Suffix is case-insensitive. No combinations (e.g. "1h30m") and no
    fractional values. Negative values are rejected.

    Raises:
        ValueError: if the value is empty, malformed, or negative.
    """
    if value is None:
        raise ValueError("Interval is required.")
    text = str(value).strip().lower()
    if not text:
        raise ValueError("Interval is required.")

    multiplier = 1
    if text[-1].isalpha():
        suffix = text[-1]
        if suffix not in _INTERVAL_SUFFIX_MINUTES:
            raise ValueError(
                f"Invalid interval suffix '{suffix}'. Use m, h, d, or w "
                f"(e.g. 5, 4h, 7d, 1w)."
            )
        multiplier = _INTERVAL_SUFFIX_MINUTES[suffix]
        text = text[:-1].strip()
        if not text:
            raise ValueError(
                "Interval is missing a number before the suffix "
                "(e.g. 4h, 7d)."
            )

    try:
        amount = int(text)
    except ValueError as exc:
        raise ValueError(
            f"Invalid interval: {value!r}. Use a whole number of minutes "
            f"(e.g. 5) or a suffixed value (e.g. 4h, 7d)."
        ) from exc

    if amount < 0:
        raise ValueError(
            "Interval must be 0 or higher. Use 0 for manual-only tasks."
        )

    return amount * multiplier


def format_interval(interval: int) -> str:
    """Format an interval (in minutes) for human-readable display.

    Returns the manual-only label for 0, the raw minute count for short
    intervals, and the raw minute count plus a parenthetical breakdown
    in days/hours/minutes for intervals of one hour or more.

    Examples:
        0     -> "manual only"
        5     -> "5 minute(s)"
        60    -> "60 minute(s) (1 hour)"
        90    -> "90 minute(s) (1 hour, 30 minutes)"
        1440  -> "1440 minute(s) (1 day)"
        10080 -> "10080 minute(s) (7 days)"
    """
    if interval == 0:
        return Defaults.MANUAL_ONLY_LABEL

    base = f"{interval} minute(s)"
    if interval < 60:
        return base

    days, rem = divmod(interval, 1440)
    hours, minutes = divmod(rem, 60)

    parts: List[str] = []
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

    return f"{base} ({', '.join(parts)})"


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
        interval = task["interval"]
        interval_display = format_interval(interval)
        if task_type == TaskTypes.UV_COMMAND:
            lines = [
                f"\n{task['id']}. {task['name']} [uv command]",
                f"   Project: {task['script_path']}",
                f"   Command: {task.get('command', 'N/A')}",
                f"   Interval: {interval_display}",
            ]
        else:
            lines = [
                f"\n{task['id']}. {task['name']}",
                f"   Script: {task['script_path']}",
                f"   Interval: {interval_display}",
            ]

        if start_time:
            lines.append(f"   Start time: {start_time}")

        if task.get("launch_new_process"):
            lines.append("   Launch mode: new console")

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
            if interval == 0:
                next_run = Defaults.MANUAL_ONLY_LABEL
            elif task["next_run_time"]:
                next_run = task["next_run_time"].strftime("%Y-%m-%d %H:%M:%S")
            else:
                next_run = "Not scheduled"
            lines.append(f"   Next run: {next_run}")
        output.extend(lines)
    return "\n".join(output)

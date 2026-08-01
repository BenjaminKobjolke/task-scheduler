"""Shared task lookup helpers."""


def filter_tasks_by_name(tasks: list[dict], filter_term: str) -> list[dict]:
    """Return tasks whose names contain the case-insensitive filter term."""
    if not filter_term:
        return tasks
    filter_lower = filter_term.lower()
    return [task for task in tasks if filter_lower in task["name"].lower()]

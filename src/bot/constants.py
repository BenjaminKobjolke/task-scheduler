"""Constants for bot integration."""


class Commands:
    """Bot command constants."""

    LIST = "/list"
    RUN = "/run"
    HISTORY = "/history"
    ADD = "/add"
    EDIT = "/edit"
    DELETE = "/delete"
    HELP = "/help"
    CANCEL = "/cancel"

    # Short alias -> canonical command name (without slash)
    ALIASES: dict[str, str] = {
        "l": "list",
        "r": "run",
        "hi": "history",
        "a": "add",
        "e": "edit",
        "d": "delete",
        "h": "help",
        "c": "cancel",
    }


class Messages:
    """Bot response message templates."""

    HELP = (
        "Available commands:\n"
        "/list (l) [filter] - List tasks\n"
        "/run (r) <id> - Run a task\n"
        "/history (hi) [n] - Show execution history\n"
        "/add (a) - Add a new task\n"
        "/edit (e) <id> - Edit a task\n"
        "/delete (d) <id> - Delete a task\n"
        "/cancel (c) - Cancel current operation\n"
        "/help (h) - Show this help\n\n"
        "Commands work with or without / prefix."
    )
    UNKNOWN_COMMAND = "Unknown command.\n\n" + HELP
    COMMAND_DISABLED = "Command {} is disabled by configuration."
    TASK_NOT_FOUND = "No task found with ID {}"
    TASK_EXECUTED_SUCCESS = "Task '{}' (ID: {}) executed successfully."
    TASK_EXECUTED_FAILURE = "Task '{}' (ID: {}) failed."
    TASK_EXECUTION_ERROR = "Error executing task {}: {}"
    CONFIRM_DELETE = (
        "Delete task '{}' (ID: {})?\nReply 'y' or 'yes' to confirm. Anything else cancels."
    )
    TASK_DELETED = "Task '{}' (ID: {}) deleted."
    DELETE_CANCELLED = "Delete cancelled."
    OPERATION_CANCELLED = "Operation cancelled."
    NO_TASKS = "No tasks scheduled."
    NO_HISTORY = "No execution history found."
    INVALID_TASK_ID = "Invalid task ID. Usage: {} <id>"
    CONVERSATION_EXPIRED = "Session expired. Please start over."
    # Add wizard messages
    WIZARD_ADD_START = (
        "Let's add a new task.\n\n"
        "Enter the script path (prefix with 'uv:' for uv command project):"
    )
    WIZARD_ADD_COMMAND = "Enter the uv command name:"
    WIZARD_ADD_NAME = "Enter a name for this task:"
    WIZARD_ADD_INTERVAL = "Enter interval in minutes (0 = manual only):"
    WIZARD_ADD_START_TIME = "Enter start time (HH:MM) or 'skip' (s):"
    WIZARD_ADD_ARGUMENTS = "Enter arguments (space-separated) or 'skip' (s):"
    WIZARD_ADD_CONFIRM = (
        "Please confirm:\n{}\n\nReply 'y' or 'yes' to add. Anything else cancels."
    )
    WIZARD_ADD_SUCCESS = "Task '{}' added successfully (ID: {})."
    WIZARD_INVALID_INTERVAL = "Please enter a valid number (0 or higher). Use 0 for manual-only tasks."
    WIZARD_INVALID_TIME = "Invalid time format. Use HH:MM (e.g., 09:00) or 'skip'."
    # Edit wizard messages
    WIZARD_EDIT_START = "Editing task '{}' (ID: {}).\n\nCurrent values:\n\n{}"
    WIZARD_EDIT_SCRIPT = "Script path [{}]:\nEnter new path or 'skip' (s) to keep current."
    WIZARD_EDIT_COMMAND = "Command [{}]:\nEnter new command or 'skip' (s) to keep current."
    WIZARD_EDIT_NAME = "Name [{}]:\nEnter new name or 'skip' (s) to keep current."
    WIZARD_EDIT_INTERVAL = (
        "Interval in minutes [{}]:\n"
        "Enter new interval or 'skip' (s) to keep current. Use 0 for manual-only."
    )
    WIZARD_EDIT_START_TIME = (
        "Start time [{}]:\n"
        "Enter time (HH:MM), 'none' to clear, or 'skip' (s) to keep current."
    )
    WIZARD_EDIT_ARGUMENTS = (
        "Arguments [{}]:\n"
        "Enter new arguments, 'none' to clear, or 'skip' (s) to keep current."
    )
    WIZARD_EDIT_CONFIRM = "Changes:\n{}\n\nReply 'y' or 'yes' to save. Anything else cancels."
    WIZARD_EDIT_SUCCESS = "Task '{}' (ID: {}) updated."
    WIZARD_EDIT_NO_CHANGES = "No changes made."

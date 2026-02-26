import os
import shlex
from datetime import datetime
from typing import Dict, Any, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import PathCompleter, FuzzyCompleter
from prompt_toolkit.key_binding import KeyBindings

from .script_runner import ScriptRunner
from .constants import TaskTypes, Paths


def _create_path_key_bindings() -> KeyBindings:
    """Create key bindings for path input with tab completion."""
    kb = KeyBindings()

    @kb.add("enter")
    def _(event):
        if event.app.current_buffer.complete_state:
            current_text = event.app.current_buffer.text
            if os.path.isdir(current_text):
                new_text = current_text.rstrip("\\") + "\\"
                event.app.current_buffer.text = new_text
                event.app.current_buffer.cursor_position = len(new_text)
            event.app.current_buffer.complete_state = None
        else:
            event.app.current_buffer.validate_and_handle()

    return kb


def _get_script_path(
    session: PromptSession,
    completer: FuzzyCompleter,
    kb: KeyBindings,
    existing_task: Optional[Dict[str, Any]],
    script_runner: ScriptRunner,
) -> tuple:
    """
    Get script path or uv project directory from user.

    Returns:
        Tuple of (script_path, task_type, command)
    """
    while True:
        prompt_text = "\nScript path or uv project directory (Use Tab for suggestions)"
        if existing_task:
            prompt_text += f" [{existing_task['script_path']}]"
        prompt_text += ":"
        print(prompt_text)

        path_input = session.prompt(
            "Path: ",
            completer=completer,
            key_bindings=kb,
            default=existing_task["script_path"] if existing_task else "",
        ).strip()

        # Keep existing value if empty input
        if existing_task and not path_input:
            return (
                existing_task["script_path"],
                existing_task.get("task_type", TaskTypes.SCRIPT),
                existing_task.get("command"),
            )

        # Check if it's a uv project directory
        if os.path.isdir(path_input):
            pyproject_path = os.path.join(path_input, Paths.PYPROJECT_TOML)
            uv_lock_path = os.path.join(path_input, Paths.UV_LOCK)

            if os.path.exists(pyproject_path) and os.path.exists(uv_lock_path):
                result = _handle_uv_project(path_input, script_runner)
                if result:
                    return (path_input, result[0], result[1])
                continue
            else:
                print(
                    "Error: Directory is not a valid uv project (missing pyproject.toml or uv.lock)"
                )
                print(
                    "Please enter a script file path or a valid uv project directory."
                )
                continue

        # Check if it's a file
        if os.path.isfile(path_input):
            return (path_input, TaskTypes.SCRIPT, None)

        print(
            "Error: Not a valid file or uv project directory. Please enter a valid path."
        )


def _handle_uv_project(path_input: str, script_runner: ScriptRunner) -> Optional[tuple]:
    """
    Handle uv project selection, returning (task_type, command) or None if user should retry.
    """
    commands = script_runner.get_uv_commands(path_input)

    if commands:
        print("\nDetected uv project! Available commands:")
        for i, cmd in enumerate(commands, 1):
            print(f"  {i}. {cmd}")
        print(f"  {len(commands) + 1}. [Custom command]")

        while True:
            cmd_input = input(f"\nSelect command [1-{len(commands) + 1}]: ").strip()
            try:
                cmd_idx = int(cmd_input) - 1
                if 0 <= cmd_idx < len(commands):
                    return (TaskTypes.UV_COMMAND, commands[cmd_idx])
                elif cmd_idx == len(commands):
                    custom_cmd = input(
                        "Enter custom command (e.g., python -m module_name): "
                    ).strip()
                    if custom_cmd:
                        return (TaskTypes.UV_COMMAND, custom_cmd)
                    print("Error: Command cannot be empty.")
                else:
                    print(
                        f"Error: Please enter a number between 1 and {len(commands) + 1}"
                    )
            except ValueError:
                print("Error: Please enter a valid number.")
    else:
        print("\nDetected uv project! No predefined commands found.")
        custom_cmd = input(
            "Enter custom command (e.g., python -m module_name): "
        ).strip()
        if custom_cmd:
            return (TaskTypes.UV_COMMAND, custom_cmd)
        print("Error: Command cannot be empty.")
        return None


def get_task_input(existing_task: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Get task details interactively from user.

    Args:
        existing_task: Optional dictionary containing current task values for editing

    Returns:
        Dictionary with task details: script_path, name, interval, arguments,
        task_type, command, start_time
    """
    print("\nAdding new task interactively:")

    kb = _create_path_key_bindings()
    path_completer = PathCompleter(get_paths=lambda: ["."], expanduser=True)
    completer = FuzzyCompleter(path_completer)
    session = PromptSession()
    script_runner = ScriptRunner()

    # If editing, show current values
    if existing_task:
        task_type = existing_task.get("task_type", TaskTypes.SCRIPT)
        print("\nEditing task (press Enter to keep current value):")
        print("Current values:")
        print(f"Name: {existing_task['name']}")
        if task_type == TaskTypes.UV_COMMAND:
            print("Type: uv command")
            print(f"Project: {existing_task['script_path']}")
            print(f"Command: {existing_task.get('command', 'N/A')}")
        else:
            print("Type: script")
            print(f"Script: {existing_task['script_path']}")
        print(f"Interval: {existing_task['interval']} minute(s)")
        if existing_task.get("start_time"):
            print(f"Start time: {existing_task['start_time']}")
        print(
            f"Arguments: {' '.join(existing_task['arguments']) if existing_task['arguments'] else 'None'}"
        )

    # Get script path
    script_path, task_type, command = _get_script_path(
        session, completer, kb, existing_task, script_runner
    )

    # Get task name
    name = _get_task_name(existing_task, command)

    # Get interval
    interval = _get_interval(existing_task)

    # Get start time
    start_time = _get_start_time(existing_task)

    # Get arguments
    arguments = _get_arguments(session, kb, existing_task)

    return {
        "script_path": script_path,
        "name": name,
        "interval": interval,
        "arguments": arguments,
        "task_type": task_type,
        "command": command,
        "start_time": start_time,
    }


def _get_task_name(
    existing_task: Optional[Dict[str, Any]],
    command: Optional[str],
) -> str:
    """Get task name from user input."""
    default_name = command if command else ""
    prompt_text = "\nTask name"
    if existing_task:
        prompt_text += f" [{existing_task['name']}]"
    elif default_name:
        prompt_text += f" [{default_name}]"
    prompt_text += ": "

    name = input(prompt_text).strip()
    if existing_task and not name:
        name = existing_task["name"]
    elif not name and default_name:
        name = default_name
    while not name:
        print("Error: Name cannot be empty.")
        name = input(prompt_text).strip()

    return name


def _get_interval(existing_task: Optional[Dict[str, Any]]) -> int:
    """Get interval in minutes from user input."""
    while True:
        prompt_text = "\nInterval in minutes"
        if existing_task:
            prompt_text += f" [{existing_task['interval']}]"
        prompt_text += ": "

        interval_input = input(prompt_text).strip()
        if existing_task and not interval_input:
            return existing_task["interval"]

        try:
            interval = int(interval_input)
            if interval < 1:
                print("Error: Interval must be at least 1 minute.")
                continue
            return interval
        except ValueError:
            print("Error: Please enter a valid number.")


def _get_start_time(existing_task: Optional[Dict[str, Any]]) -> Optional[str]:
    """Get optional start time in HH:MM format from user input."""
    while True:
        prompt_text = "\nStart time (optional, HH:MM format for aligned scheduling)"
        if existing_task and existing_task.get("start_time"):
            prompt_text += f" [{existing_task['start_time']}]"
        prompt_text += ": "

        start_time_input = input(prompt_text).strip()
        if existing_task and not start_time_input:
            return existing_task.get("start_time")
        elif not start_time_input:
            return None

        try:
            datetime.strptime(start_time_input, "%H:%M")
            return start_time_input
        except ValueError:
            print("Error: Please enter time in HH:MM format (e.g., 09:00).")


def _get_arguments(
    session: PromptSession,
    kb: KeyBindings,
    existing_task: Optional[Dict[str, Any]],
) -> Optional[list]:
    """Get optional arguments from user input."""
    print("\nEnter arguments (press Enter twice to finish):")
    print('Example: --source "path/to/source" --target "path/to/target"')
    if existing_task and existing_task["arguments"]:
        print(f"Current arguments: {' '.join(existing_task['arguments'])}")

    args = None
    arg_lines = []
    while True:
        arg = session.prompt("> ", key_bindings=kb).strip()

        if not arg:
            if not arg_lines and existing_task:
                args = shlex.split(" ".join(existing_task["arguments"]))
            elif arg_lines:
                args = shlex.split(" ".join(arg_lines))
            break
        arg_lines.append(arg)

    return args if args else None

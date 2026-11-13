"""Script and project selection for interactive task setup."""
import os
from typing import Any, Dict, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import FuzzyCompleter
from prompt_toolkit.key_binding import KeyBindings

from .script_runner import ScriptRunner
from .constants import Messages, Paths, TaskTypes


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
        prompt_text = "\nScript path or project directory (Use Tab for suggestions)"
        if existing_task:
            prompt_text += "\n(Enter = keep current)"
        prompt_text += ":"
        print(prompt_text)

        path_input = session.prompt(
            "Path: ",
            completer=completer,
            key_bindings=kb,
            default=existing_task["script_path"] if existing_task else "",
        ).strip()

        # Keep existing value if empty or unchanged
        if existing_task and (not path_input or path_input == existing_task["script_path"]):
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
            scripts = _find_shell_scripts(path_input)
            if not scripts:
                print(Messages.DIR_NOT_RUNNABLE.format(path=path_input))
                continue
            selected = _select_shell_script(scripts)
            if selected:
                return (selected, TaskTypes.SCRIPT, None)
            continue

        # Check if it's a file
        if os.path.isfile(path_input):
            return (path_input, TaskTypes.SCRIPT, None)

        print(
            "Error: Not a valid file or uv project directory. Please enter a valid path."
        )


def _find_shell_scripts(directory: str) -> list[str]:
    """Top-level .bat/.ps1 files in directory as absolute paths, sorted by name."""
    extensions = (Paths.BAT_EXTENSION, Paths.PS1_EXTENSION)
    try:
        with os.scandir(directory) as entries:
            found = [
                os.path.abspath(e.path)
                for e in entries
                if e.is_file() and os.path.splitext(e.name)[1].lower() in extensions
            ]
    except OSError:
        return []
    return sorted(found, key=lambda p: os.path.basename(p).lower())


def _select_shell_script(scripts: list[str]) -> Optional[str]:
    """Let the user pick one of scripts; returns None on empty input."""
    print(Messages.SCRIPT_FILES_FOUND)
    for position, path in enumerate(scripts, 1):
        print(Messages.SCRIPT_FILE_CHOICE.format(position=position, name=os.path.basename(path)))

    count = len(scripts)
    while True:
        choice = input(Messages.SCRIPT_FILE_PROMPT.format(count=count)).strip()
        if not choice:
            return None
        if choice.isdigit() and 1 <= int(choice) <= count:
            return scripts[int(choice) - 1]
        print(Messages.SCRIPT_FILE_INVALID_SELECTION.format(count=count))


def _handle_uv_project(path_input: str, script_runner: ScriptRunner) -> Optional[tuple]:
    """
    Handle uv project selection, returning (task_type, command) or None if user should retry.
    """
    predefined = script_runner.get_uv_commands(path_input)
    discovered = script_runner.discover_entry_points(path_input)

    # Build combined option list: (command, description_or_none)
    options: list[tuple[str, Optional[str]]] = []

    has_predefined = len(predefined) > 0
    has_discovered = len(discovered) > 0

    if not has_predefined and not has_discovered:
        print("\nDetected uv project! No predefined or discovered commands found.")
        custom_cmd = input(
            "Enter custom command (e.g., python -m module_name): "
        ).strip()
        if custom_cmd:
            return (TaskTypes.UV_COMMAND, custom_cmd)
        print("Error: Command cannot be empty.")
        return None

    if has_predefined and has_discovered:
        print("\nDetected uv project! Available commands:")
        print("  Predefined:")
        for cmd in predefined:
            options.append((cmd, None))
            print(f"    {len(options)}. {cmd}")
        print("  Discovered:")
        for cmd, desc in discovered:
            options.append((cmd, desc))
            print(f"    {len(options)}. {cmd}  ({desc})")
    elif has_predefined:
        print("\nDetected uv project! Available commands:")
        for cmd in predefined:
            options.append((cmd, None))
            print(f"  {len(options)}. {cmd}")
    else:
        print("\nDetected uv project! No predefined commands, but found possible entry points:")
        for cmd, desc in discovered:
            options.append((cmd, desc))
            print(f"  {len(options)}. {cmd}  ({desc})")

    custom_idx = len(options) + 1
    print(f"  {custom_idx}. [Custom command]")

    while True:
        cmd_input = input(f"\nSelect command [1-{custom_idx}]: ").strip()
        try:
            choice = int(cmd_input)
            if 1 <= choice <= len(options):
                return (TaskTypes.UV_COMMAND, options[choice - 1][0])
            elif choice == custom_idx:
                custom_cmd = input(
                    "Enter custom command (e.g., python -m module_name): "
                ).strip()
                if custom_cmd:
                    return (TaskTypes.UV_COMMAND, custom_cmd)
                print("Error: Command cannot be empty.")
            else:
                print(f"Error: Please enter a number between 1 and {custom_idx}")
        except ValueError:
            print("Error: Please enter a valid number.")



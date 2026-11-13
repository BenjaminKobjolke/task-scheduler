"""Command-line argument parsing for the task scheduler."""
import argparse

from src.formatters import parse_interval


def _interval_arg(value: str) -> int:
    """Argparse adapter for parse_interval that surfaces friendly errors."""
    try:
        return parse_interval(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Task Scheduler for Python Scripts, Batch and PowerShell Files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Add a new task with arguments (use -- to separate scheduler args from script args)
    python main.py --script "script.py" --name "task" --interval 5 -- --source "path with spaces" --target "another path"
                                                                    ^^ Everything after this is passed to the script

    # Add a task using relative path
    python main.py --script "script.py" --name "local script" --interval 1

    # Add a batch file task
    python main.py --script "backup.bat" --name "backup task" --interval 60

    # Add a PowerShell task (runs via powershell.exe -ExecutionPolicy Bypass -File)
    python main.py --script "C:\\prosody\\renew-certificates.ps1" --name "renew certs" --interval 1d

    # Intervals can use suffixes m/h/d/w (e.g. 4h, 7d, 1w)
    python main.py --script "weekly.py" --name "weekly job" --interval 7d

    # Add a uv command task with arguments
    python main.py --uv-command "D:\\project" "sync-to-local" --name "Sync" --interval 5 -- --config "config.json"

    # Add a task interactively
    python main.py --add

    # Edit a task interactively
    python main.py --edit 1

    # List and run existing tasks
    python main.py

    # Change logging settings
    python main.py --log-level DEBUG --detailed-logs true

Note:
    - Python scripts should have their own venv in their directory.
    - Batch and PowerShell (.ps1) files will run from their own directory.
        """
    )

    group = parser.add_mutually_exclusive_group()

    group.add_argument(
        "--add",
        action="store_true",
        help="Interactive mode to add a new task"
    )

    group.add_argument(
        "--edit",
        type=int,
        metavar="ID",
        help="Edit a task by its ID"
    )

    group.add_argument(
        "--script",
        type=str,
        help="Path to the Python script, batch or PowerShell file to schedule"
    )

    group.add_argument(
        "--uv-command",
        nargs=2,
        metavar=("PROJECT_DIR", "COMMAND"),
        help="Add a uv command task: PROJECT_DIR is the uv project path, COMMAND is the uv command to run"
    )

    group.add_argument(
        "--shutdown",
        action="store_true",
        help="Ask the running scheduler instance to stop and wait for it to exit"
    )

    parser.add_argument(
        "--name",
        type=str,
        help="Descriptive name for the task"
    )

    parser.add_argument(
        "--interval",
        type=_interval_arg,
        metavar="INTERVAL",
        help=(
            "Interval between executions: bare minutes (e.g. 5) or with "
            "suffix Nm/Nh/Nd/Nw (e.g. 4h, 7d, 1w). Use 0 for manual only."
        ),
    )

    parser.add_argument(
        "--start-time",
        type=str,
        metavar="HH:MM",
        help="Optional start time for aligned scheduling (e.g., 09:00)"
    )

    parser.add_argument(
        "--set-start-time",
        nargs=2,
        metavar=("ID", "TIME"),
        help="Set or clear start time for a task (use 'none' to clear)"
    )

    parser.add_argument(
        "--set-interval",
        nargs=2,
        metavar=("ID", "INTERVAL"),
        help="Set interval for a task (e.g. 5, 4h, 7d, 1w; 0 = manual only)"
    )

    parser.add_argument(
        "--set-arguments",
        type=int,
        metavar="ID",
        help="Set arguments for a task interactively"
    )

    parser.add_argument(
        "--rename",
        type=int,
        metavar="ID",
        help="Rename a task by its ID (prompts for new name)"
    )

    parser.add_argument(
        "--copy-task",
        type=int,
        metavar="ID",
        help="Copy a task by its ID (creates a duplicate with ' (copy)' suffix)"
    )

    parser.add_argument(
        "--list",
        nargs='?',
        const='',
        default=None,
        metavar="FILTER",
        help="List scheduled tasks and exit (optional name filter)"
    )

    parser.add_argument(
        "--history",
        type=int,
        nargs='?',
        const=10,
        metavar="N",
        help="Show the last N task executions (default: 10)"
    )

    parser.add_argument(
        "--delete",
        type=int,
        metavar="ID",
        help="Delete a task by its database ID"
    )

    parser.add_argument(
        "--log-level",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help="Set the logging level"
    )

    parser.add_argument(
        "--detailed-logs",
        type=str,
        choices=['true', 'false'],
        help="Enable or disable detailed argument logging"
    )

    parser.add_argument(
        "--run_id",
        type=int,
        metavar="ID",
        help="Run a specific task by its database ID"
    )

    parser.add_argument(
        "--run-name",
        nargs="?",
        const="",
        default=None,
        metavar="FILTER",
        help="Select and run a task by a partial name match"
    )

    parser.add_argument(
        "--launch-new-process",
        action="store_true",
        help="Launch task in a new console window (only for manual tasks with interval 0)"
    )

    parser.add_argument(
        "--ftp-sync",
        action="store_true",
        help="Manually trigger FTP sync of the status page"
    )

    # Collect remaining arguments after --
    parser.add_argument(
        'script_args',
        nargs=argparse.REMAINDER,
        help="Arguments to pass to the script (everything after --)"
    )

    return parser.parse_args()


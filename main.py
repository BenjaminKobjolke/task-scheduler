#!/usr/bin/env python3
import argparse
import signal
import sys
import time

from bot_commander import BotManager

from src.scheduler import TaskScheduler
from src.logger import Logger
from src.config import Config
from src.formatters import format_task_list
from src.bot.command_processor import TaskCommandProcessor
from src.commands import (
    handle_list,
    handle_history,
    handle_delete,
    handle_set_start_time,
    handle_set_interval,
    handle_set_arguments,
    handle_copy_task,
    handle_edit,
    handle_add,
    handle_script,
    handle_run_id,
    handle_ftp_sync,
    handle_uv_command,
)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Task Scheduler for Python Scripts and Batch Files",
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
    - Batch files will run from their own directory.
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
        help="Path to the Python script or batch file to schedule"
    )

    group.add_argument(
        "--uv-command",
        nargs=2,
        metavar=("PROJECT_DIR", "COMMAND"),
        help="Add a uv command task: PROJECT_DIR is the uv project path, COMMAND is the uv command to run"
    )

    parser.add_argument(
        "--name",
        type=str,
        help="Descriptive name for the task"
    )

    parser.add_argument(
        "--interval",
        type=int,
        help="Interval in minutes between script executions"
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
        metavar=("ID", "MINUTES"),
        help="Set interval for a task"
    )

    parser.add_argument(
        "--set-arguments",
        type=int,
        metavar="ID",
        help="Set arguments for a task interactively"
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


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info("Shutdown signal received")
    bot_manager.shutdown()
    scheduler.shutdown()
    sys.exit(0)


if __name__ == "__main__":
    try:
        # Parse arguments
        args = parse_arguments()

        # Update logging configuration if specified
        config = Config()
        if args.log_level:
            config.set_logging_level(args.log_level)
        if args.detailed_logs:
            config.set_detailed_logging(args.detailed_logs.lower() == 'true')

        # Initialize logger and scheduler
        logger = Logger("Main")
        scheduler = TaskScheduler()

        if args.list is not None:
            handle_list(scheduler, logger, args.list)
            sys.exit(0)

        elif args.history is not None:
            handle_history(scheduler, logger, args.history)
            sys.exit(0)

        elif args.delete is not None:
            handle_delete(scheduler, logger, args.delete)
            sys.exit(0)

        elif args.set_start_time:
            task_id_str, time_value = args.set_start_time
            handle_set_start_time(scheduler, logger, task_id_str, time_value)
            sys.exit(0)

        elif args.set_interval:
            task_id_str, interval_str = args.set_interval
            handle_set_interval(scheduler, logger, task_id_str, interval_str)
            sys.exit(0)

        elif args.set_arguments is not None:
            handle_set_arguments(scheduler, logger, args.set_arguments)
            sys.exit(0)

        elif args.copy_task is not None:
            handle_copy_task(scheduler, logger, args.copy_task)
            sys.exit(0)

        elif args.edit is not None:
            handle_edit(scheduler, logger, args.edit)
            sys.exit(0)

        elif args.add:
            handle_add(scheduler, logger)
            sys.exit(0)

        elif args.script:
            handle_script(scheduler, logger, args)
            sys.exit(0)

        elif args.uv_command:
            handle_uv_command(scheduler, logger, args)
            sys.exit(0)

        elif args.run_id:
            handle_run_id(scheduler, logger, args.run_id)
            sys.exit(0)

        elif args.ftp_sync:
            handle_ftp_sync(logger, config)
            sys.exit(0)

        # If no specific action was requested, run the scheduler
        bot_config_dto = config.get_bot_config()
        processor = TaskCommandProcessor(scheduler, bot_config_dto)
        bot_manager = BotManager(
            message_handler=processor,
            config_provider=config,
            bot_type=config.get_bot_type(),
        )

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        scheduler.start()

        # Initialize bot if configured
        bot_started = bot_manager.start()
        if bot_started:
            logger.info("Bot integration started")

        tasks = scheduler.list_tasks()
        logger.info("Current tasks:" + format_task_list(tasks, show_next_run=True))
        logger.info("\nPress Ctrl+C to exit")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            bot_manager.shutdown()
            scheduler.shutdown()
            sys.exit(0)

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)

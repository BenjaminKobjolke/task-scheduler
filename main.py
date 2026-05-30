#!/usr/bin/env python3
import argparse
import logging
import os
import signal
import sys
import time

from src.scheduler import TaskScheduler
from src.logger import Logger, setup_bot_library_logging
from src.cli_output import CliOutput
from src.config import Config
from src.constants import Bot, Defaults, Messages, Paths
from src.instance_controller import InstanceController
from src.formatters import format_task_list, parse_interval
from src.commands import (
    handle_list,
    handle_history,
    handle_delete,
    handle_set_start_time,
    handle_set_interval,
    handle_set_arguments,
    handle_rename,
    handle_copy_task,
    handle_edit,
    handle_add,
    handle_script,
    handle_run_id,
    handle_ftp_sync,
    handle_uv_command,
    handle_shutdown,
)


def _interval_arg(value: str) -> int:
    """Argparse adapter for parse_interval that surfaces friendly errors."""
    try:
        return parse_interval(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


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


def perform_shutdown():
    """Stop bot and scheduler, release the lock, then exit immediately.

    Uses os._exit after releasing the lock so a job already running in an
    APScheduler worker thread (e.g. blocked in subprocess) cannot stall the
    interpreter's exit. Already-launched external scripts keep running as
    independent OS processes.
    """
    if bot_manager is not None:
        bot_logger.info("Bot shutting down")
        bot_manager.shutdown()
    scheduler.shutdown()  # wait=False: do not block on running jobs
    instance.clear_request()
    instance.release()
    logger.info("Scheduler stopped")
    logging.shutdown()  # flush log handlers before the hard exit
    os._exit(0)


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info("Shutdown signal received")
    perform_shutdown()
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
        cli = CliOutput()
        scheduler = TaskScheduler()

        if args.list is not None:
            handle_list(scheduler, cli, args.list)
            sys.exit(0)

        elif args.history is not None:
            handle_history(scheduler, cli, args.history)
            sys.exit(0)

        elif args.delete is not None:
            handle_delete(scheduler, cli, args.delete)
            sys.exit(0)

        elif args.set_start_time:
            task_id_str, time_value = args.set_start_time
            handle_set_start_time(scheduler, cli, task_id_str, time_value)
            sys.exit(0)

        elif args.set_interval:
            task_id_str, interval_str = args.set_interval
            handle_set_interval(scheduler, cli, task_id_str, interval_str)
            sys.exit(0)

        elif args.set_arguments is not None:
            handle_set_arguments(scheduler, cli, args.set_arguments)
            sys.exit(0)

        elif args.rename is not None:
            handle_rename(scheduler, cli, args.rename)
            sys.exit(0)

        elif args.copy_task is not None:
            handle_copy_task(scheduler, cli, args.copy_task)
            sys.exit(0)

        elif args.edit is not None:
            handle_edit(scheduler, cli, args.edit)
            sys.exit(0)

        elif args.add:
            handle_add(scheduler, cli)
            sys.exit(0)

        elif args.script:
            handle_script(scheduler, cli, args)
            sys.exit(0)

        elif args.uv_command:
            handle_uv_command(scheduler, cli, args)
            sys.exit(0)

        elif args.run_id:
            handle_run_id(scheduler, cli, args.run_id)
            sys.exit(0)

        elif args.ftp_sync:
            handle_ftp_sync(cli, config)
            sys.exit(0)

        elif args.shutdown:
            handle_shutdown(cli)
            sys.exit(0)

        # If no specific action was requested, run the scheduler.
        # Guard against a second continuous instance firing every task twice;
        # offer to shut down an already-running instance and take over.
        instance = InstanceController()
        if not instance.try_acquire():
            answer = input(Messages.RESTART_PROMPT).strip().lower()
            if answer not in ("y", "yes"):
                cli.info(Messages.RESTART_ABORTED)
                sys.exit(0)
            cli.info(Messages.TAKEOVER_STOPPING)
            instance.request_shutdown()
            if not instance.wait_until_stopped(Defaults.SHUTDOWN_WAIT_SECONDS):
                cli.error(
                    Messages.SHUTDOWN_TIMEOUT.format(
                        seconds=Defaults.SHUTDOWN_WAIT_SECONDS
                    )
                )
                sys.exit(1)
            cli.info(Messages.TAKEOVER_STOPPED)
            if not instance.try_acquire():
                cli.error(Messages.ALREADY_RUNNING)
                sys.exit(1)
        instance.clear_request()
        cli.info(Messages.STARTING_INSTANCE)

        bot_logger = Logger("Bot", log_file_prefix=Paths.LOG_FILE_PREFIX_BOT)
        setup_bot_library_logging()

        bot_manager = None
        processor = None
        health_monitor = None
        bot_type = config.get_bot_type()

        if bot_type and bot_type.lower() != "none":
            try:
                from bot_commander import BotManager
                from src.bot.command_processor import TaskCommandProcessor
                from src.bot_health import BotHealthMonitor
            except ImportError as exc:
                bot_logger.warning(
                    f"Bot type '{bot_type}' configured but bot-commander not installed "
                    f"({exc}). Run `uv sync --extra bot` (telegram) or "
                    f"`uv sync --extra xmpp` (xmpp) to enable bot support. "
                    f"Continuing without bot."
                )
            else:
                bot_config_dto = config.get_bot_config()
                processor = TaskCommandProcessor(scheduler, bot_config_dto)
                bot_manager = BotManager(
                    message_handler=processor,
                    config_provider=config,
                    bot_type=bot_type,
                )

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        scheduler.start()

        # Initialize bot if configured
        if bot_manager is not None:
            try:
                bot_started = bot_manager.start()
                if bot_started:
                    processor.set_notifier(bot_manager.send_message)
                    bot_logger.info("Bot integration started")
                    health_monitor = BotHealthMonitor(bot_manager, bot_logger)
            except Exception as e:
                bot_logger.error(f"Bot failed to start: {e}", exc_info=True)

        tasks = scheduler.list_tasks()
        logger.info("Current tasks:" + format_task_list(tasks, show_next_run=True))
        logger.info("\nPress Ctrl+C to exit")

        try:
            last_health_check = time.time()
            while True:
                time.sleep(1)
                if instance.shutdown_requested():
                    logger.info("Shutdown request received")
                    break
                now = time.time()
                if (
                    health_monitor is not None
                    and now - last_health_check >= Bot.HEALTH_CHECK_INTERVAL_SECONDS
                ):
                    health_monitor.check_health()
                    last_health_check = now
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")

        perform_shutdown()
        sys.exit(0)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if "cli" in dir():
            cli.error(f"Error: {e}")
        elif "logger" in dir():
            logger.error(f"Error: {str(e)}", exc_info=True)
        sys.exit(1)

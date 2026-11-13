#!/usr/bin/env python3
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
from src.formatters import format_task_list
from src.cli_arguments import parse_arguments
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
    handle_run_name,
    handle_ftp_sync,
    handle_uv_command,
    handle_shutdown,
)


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

        elif args.run_name is not None:
            handle_run_name(scheduler, cli, args.run_name)
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
            if not instance.stop_running():
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

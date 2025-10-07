#!/usr/bin/env python3
import argparse
import os
import shlex
import signal
import sys
import time
from datetime import datetime
from typing import Dict, Any
from prompt_toolkit import prompt, PromptSession
from prompt_toolkit.completion import PathCompleter, FuzzyCompleter
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.filters import has_completions
from src.scheduler import TaskScheduler
from src.logger import Logger
from src.config import Config

def get_task_input(existing_task: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Get task details interactively from user.
    
    Args:
        existing_task: Optional dictionary containing current task values for editing
    """
    print("\nAdding new task interactively:")
    
    # Setup key bindings for path input
    kb = KeyBindings()

    @kb.add('enter')
    def _(event):
        # If completion menu is showing
        if event.app.current_buffer.complete_state:
            # Get the current text
            current_text = event.app.current_buffer.text
            
            # If it's a directory, append backslash and move cursor
            if os.path.isdir(current_text):
                new_text = current_text.rstrip('\\') + '\\'
                event.app.current_buffer.text = new_text
                event.app.current_buffer.cursor_position = len(new_text)
            
            # Clear completion state
            event.app.current_buffer.complete_state = None
        else:
            # No suggestions shown, complete the input
            event.app.current_buffer.validate_and_handle()

    # Get script path with validation and tab completion
    path_completer = PathCompleter(
        get_paths=lambda: ['.'],
        expanduser=True
    )
    completer = FuzzyCompleter(path_completer)
    session = PromptSession()
    
    # If editing, show current values
    if existing_task:
        print("\nEditing task (press Enter to keep current value):")
        print(f"Current values:")
        print(f"Name: {existing_task['name']}")
        print(f"Script: {existing_task['script_path']}")
        print(f"Interval: {existing_task['interval']} minute(s)")
        print(f"Arguments: {' '.join(existing_task['arguments']) if existing_task['arguments'] else 'None'}")
    
    while True:
        prompt_text = "\nScript path (Use Tab for suggestions)"
        if existing_task:
            prompt_text += f" [{existing_task['script_path']}]"
        prompt_text += ":"
        print(prompt_text)
        
        script_path = session.prompt(
            "Path: ",
            completer=completer,
            key_bindings=kb,
            default=existing_task['script_path'] if existing_task else ""
        ).strip()
        
        # Keep existing value if empty input
        if existing_task and not script_path:
            script_path = existing_task['script_path']
        
        if os.path.isfile(script_path):
            break
        print("Error: Not a valid file. Please enter a valid path.")
    
    # Get task name
    prompt_text = "\nTask name"
    if existing_task:
        prompt_text += f" [{existing_task['name']}]"
    prompt_text += ": "
    
    name = input(prompt_text).strip()
    # Keep existing value if empty input
    if existing_task and not name:
        name = existing_task['name']
    while not name:
        print("Error: Name cannot be empty.")
        name = input(prompt_text).strip()
    
    # Get interval with validation
    while True:
        prompt_text = "\nInterval in minutes"
        if existing_task:
            prompt_text += f" [{existing_task['interval']}]"
        prompt_text += ": "
        
        interval_input = input(prompt_text).strip()
        # Keep existing value if empty input
        if existing_task and not interval_input:
            interval = existing_task['interval']
            break
            
        try:
            interval = int(interval_input)
            if interval < 1:
                print("Error: Interval must be at least 1 minute.")
                continue
            break
        except ValueError:
            print("Error: Please enter a valid number.")
    
    # Get arguments (optional) with path completion
    print("\nEnter arguments (press Enter twice to finish):")
    print("Example: --source \"path/to/source\" --target \"path/to/target\"")
    if existing_task and existing_task['arguments']:
        print(f"Current arguments: {' '.join(existing_task['arguments'])}")
    
    args = None
    arg_lines = []
    while True:
        arg = session.prompt("> ", key_bindings=kb).strip()
        
        if not arg:
            if not arg_lines and existing_task:  # No new arguments entered, keep existing
                # Re-parse existing arguments to ensure proper format
                args = shlex.split(' '.join(existing_task['arguments']))
            elif arg_lines:
                # Parse all entered arguments properly
                args = shlex.split(' '.join(arg_lines))
            break
        arg_lines.append(arg)
    
    return {
        "script_path": script_path,
        "name": name,
        "interval": interval,
        "arguments": args if args else None
    }

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
        "--list",
        action="store_true",
        help="List all scheduled tasks and exit"
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
    scheduler.shutdown()
    sys.exit(0)

def format_task_list(tasks, show_next_run: bool = True):
    """Format task list for display."""
    if not tasks:
        return "No tasks scheduled."
    
    output = []
    for task in tasks:
        lines = [
            f"\n{task['id']}. {task['name']}",
            f"   Script: {task['script_path']}",
            f"   Interval: {task['interval']} minute(s)",
            f"   Arguments: {' '.join(task['arguments']) if task['arguments'] else 'None'}"
        ]
        if show_next_run:
            next_run = task['next_run_time'].strftime('%Y-%m-%d %H:%M:%S') if task['next_run_time'] else 'Not scheduled'
            lines.append(f"   Next run: {next_run}")
        output.extend(lines)
    return '\n'.join(output)

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
        
        if args.list:
            # Just list tasks and exit
            tasks = scheduler.list_tasks()
            logger.info("Scheduled tasks:" + format_task_list(tasks, show_next_run=False))
            sys.exit(0)
            
        elif args.delete is not None:
            # Get task info before deletion
            tasks = scheduler.list_tasks()
            task = next((t for t in tasks if t['id'] == args.delete), None)
            
            if not task:
                logger.error(f"No task found with ID {args.delete}")
                sys.exit(1)
            
            # Show task info and ask for confirmation
            logger.info(f"\nTask to delete:")
            logger.info(format_task_list([task], show_next_run=False))
            
            confirmation = input("\nAre you sure you want to delete this task? (y/N): ")
            if confirmation.lower() == 'y':
                try:
                    scheduler.remove_task(args.delete)
                    logger.info("Task deleted successfully")
                except ValueError as e:
                    logger.error(str(e))
                    sys.exit(1)
            else:
                logger.info("Deletion cancelled")
            sys.exit(0)
            
        elif args.edit is not None:
            # Get task info before editing
            tasks = scheduler.list_tasks()
            task = next((t for t in tasks if t['id'] == args.edit), None)
            
            if not task:
                logger.error(f"No task found with ID {args.edit}")
                sys.exit(1)
            
            # Show current task info
            logger.info(f"\nEditing task:")
            logger.info(format_task_list([task], show_next_run=False))
            
            # Get updated task details interactively
            task_details = get_task_input(task)
            
            try:
                # Update the task
                scheduler.edit_task(
                    task_id=args.edit,
                    name=task_details["name"],
                    script_path=os.path.abspath(task_details["script_path"]),
                    interval=task_details["interval"],
                    arguments=task_details["arguments"]
                )
                logger.info("Task updated successfully:")
                logger.info(f"Name: {task_details['name']}")
                logger.info(f"Script: {task_details['script_path']}")
                logger.info(f"Interval: {task_details['interval']} minute(s)")
                if task_details["arguments"]:
                    logger.info(f"Arguments: {' '.join(task_details['arguments'])}")
            except ValueError as e:
                logger.error(str(e))
                sys.exit(1)
            sys.exit(0)
            
        elif args.add:
            # Get task details interactively
            task_details = get_task_input()
            
            # Add the task
            scheduler.add_task(
                name=task_details["name"],
                script_path=os.path.abspath(task_details["script_path"]),
                interval=task_details["interval"],
                arguments=task_details["arguments"]
            )
            
            # Show the added task and exit
            logger.info("Task added successfully:")
            logger.info(f"Name: {task_details['name']}")
            logger.info(f"Script: {task_details['script_path']}")
            logger.info(f"Interval: {task_details['interval']} minute(s)")
            if task_details["arguments"]:
                logger.info(f"Arguments: {' '.join(task_details['arguments'])}")
            sys.exit(0)
            
        elif args.script:
            # Adding a new task via command line
            if not args.name:
                logger.error("--name is required when adding a new task")
                sys.exit(1)
            
            if not args.interval:
                logger.error("--interval is required when adding a new task")
                sys.exit(1)
            
            if args.interval < 1:
                logger.error("Interval must be at least 1 minute")
                sys.exit(1)
            
            # Convert relative script path to absolute
            script_path = os.path.abspath(args.script)
            
            # Remove the -- separator if present and get remaining args
            script_args = args.script_args[1:] if args.script_args and args.script_args[0] == '--' else args.script_args
            
            # Add the task
            scheduler.add_task(args.name, script_path, args.interval, script_args)
            
            # Show the added task and exit
            logger.info("Task added successfully:")
            logger.info(f"Name: {args.name}")
            logger.info(f"Script: {script_path}")
            logger.info(f"Interval: {args.interval} minute(s)")
            if script_args:
                logger.info(f"Arguments: {' '.join(script_args)}")
            sys.exit(0)

        elif args.run_id:
            # Run a specific task by its ID
            tasks = scheduler.list_tasks()
            task = next((t for t in tasks if t['id'] == args.run_id), None)

            if not task:
                logger.error(f"No task found with ID {args.run_id}")
                sys.exit(1)

            logger.info(f"Running task {task['name']} (ID: {task['id']})")
            try:
                scheduler.run_task(task['id'])
            except Exception as e:
                logger.error(f"Error running task {task['name']} (ID: {task['id']}): {str(e)}")
                sys.exit(1)
            sys.exit(0)
        
        # If no specific action was requested, run the scheduler
        if not (args.script or args.list or args.delete or args.run_id):
            # Register signal handlers for graceful shutdown
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            # Start the scheduler
            scheduler.start()
            
            # Display current tasks
            tasks = scheduler.list_tasks()
            logger.info("Current tasks:" + format_task_list(tasks, show_next_run=True))
            logger.info("\nPress Ctrl+C to exit")
            
            # Keep the main thread alive with a more graceful sleep
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                scheduler.shutdown()
                sys.exit(0)
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)

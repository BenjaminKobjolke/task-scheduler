#!/usr/bin/env python3
import argparse
import os
import shlex
import signal
import sys
import time
from datetime import datetime
from typing import Dict, Any
from src.scheduler import TaskScheduler
from src.logger import Logger

def get_task_input() -> Dict[str, Any]:
    """Get task details interactively from user."""
    print("\nAdding new task interactively:")
    
    # Get script path with validation
    while True:
        script_path = input("\nScript path: ").strip()
        if os.path.exists(script_path):
            break
        print("Error: Script not found. Please enter a valid path.")
    
    # Get task name
    name = input("\nTask name: ").strip()
    while not name:
        print("Error: Name cannot be empty.")
        name = input("Task name: ").strip()
    
    # Get interval with validation
    while True:
        try:
            interval = int(input("\nInterval in minutes: ").strip())
            if interval < 1:
                print("Error: Interval must be at least 1 minute.")
                continue
            break
        except ValueError:
            print("Error: Please enter a valid number.")
    
    # Get arguments (optional)
    print("\nEnter arguments (press Enter twice to finish):")
    print("Example: --source \"path/to/source\" --target \"path/to/target\"")
    args = []
    while True:
        arg = input("> ").strip()
        if not arg and not args:  # No arguments entered
            break
        if not arg and args:  # Double Enter to finish
            break
        args.append(arg)
    
    return {
        "script_path": script_path,
        "name": name,
        "interval": interval,
        "arguments": shlex.split(' '.join(args)) if args else None
    }

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Task Scheduler for Python Scripts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Add a new task with arguments (use -- to separate scheduler args from script args)
    python main.py --script "script.py" --name "task" --interval 5 -- --source "path with spaces" --target "another path"
                                                                    ^^ Everything after this is passed to the script

    # Add a task using relative path
    python main.py --script "script.py" --name "local script" --interval 1

    # Add a task interactively
    python main.py --add

    # List and run existing tasks
    python main.py
    
Note: Each script should have its own venv in its directory.
        """
    )
    
    group = parser.add_mutually_exclusive_group()
    
    group.add_argument(
        "--add",
        action="store_true",
        help="Interactive mode to add a new task"
    )
    
    group.add_argument(
        "--script",
        type=str,
        help="Path to the Python script to schedule"
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
    # Initialize logger
    logger = Logger("Main")
    
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Initialize scheduler
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
        
        # If no specific action was requested, run the scheduler
        if not (args.script or args.list or args.delete):
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

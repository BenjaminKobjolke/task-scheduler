#!/usr/bin/env python3
import argparse
import signal
import sys
import time
from datetime import datetime
from src.scheduler import TaskScheduler
from src.logger import Logger

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Task Scheduler for Python Scripts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Add a new task
    python main.py --script "path/to/script.py" --name "daily backup" --arguments "--arg1 value1" --interval 5

    # List and run existing tasks
    python main.py
    
Note: Each script should have its own venv in its directory.
        """
    )
    
    parser.add_argument(
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
        "--arguments",
        type=str,
        help="Arguments to pass to the script (optional)"
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
    
    return parser.parse_args()

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info("Shutdown signal received")
    scheduler.shutdown()
    sys.exit(0)

def format_task_list(tasks):
    """Format task list for display."""
    if not tasks:
        return "No tasks scheduled."
    
    output = []
    for task in tasks:
        next_run = task['next_run_time'].strftime('%Y-%m-%d %H:%M:%S') if task['next_run_time'] else 'Not scheduled'
        output.extend([
            f"\n{task['id']}. {task['name']}",
            f"   Script: {task['script_path']}",
            f"   Interval: {task['interval']} minute(s)",
            f"   Arguments: {' '.join(task['arguments']) if task['arguments'] else 'None'}",
            f"   Next run: {next_run}"
        ])
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
            logger.info("Scheduled tasks:" + format_task_list(tasks))
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
            logger.info(format_task_list([task]))
            
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
            
        elif args.script:
            # Adding a new task
            if not args.name:
                logger.error("--name is required when adding a new task")
                sys.exit(1)
            
            if not args.interval:
                logger.error("--interval is required when adding a new task")
                sys.exit(1)
            
            if args.interval < 1:
                logger.error("Interval must be at least 1 minute")
                sys.exit(1)
            
            # Parse script arguments if provided
            script_args = args.arguments.split() if args.arguments else None
            
            # Add the task
            scheduler.add_task(args.name, args.script, args.interval, script_args)
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start the scheduler
        scheduler.start()
        
        # Display current tasks
        tasks = scheduler.list_tasks()
        logger.info("Current tasks:" + format_task_list(tasks))
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

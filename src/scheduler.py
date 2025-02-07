from typing import Dict, List, Optional
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from .logger import Logger
from .script_runner import ScriptRunner
from .database import Database
from .status_page import StatusPage

class TaskScheduler:
    """Manages scheduled tasks using APScheduler."""
    
    def __init__(self):
        """Initialize the task scheduler."""
        self.logger = Logger("TaskScheduler")
        self.script_runner = ScriptRunner()
        self.db = Database()
        
        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)
        
        # Initialize scheduler without persistent job store
        self.scheduler = BackgroundScheduler()
        self.status_page = StatusPage()
        
    def start(self):
        """Start the scheduler and load tasks from database."""
        # Load all tasks from database
        tasks = self.db.get_all_tasks()
        for task in tasks:
            self._schedule_task(
                task['id'],
                task['name'],
                task['script_path'],
                task['interval'],
                task['arguments']
            )
        
        self.scheduler.start()
        self.logger.info(f"Scheduler started with {len(tasks)} tasks")
        
    def shutdown(self):
        """Shutdown the scheduler."""
        self.scheduler.shutdown()
        self.logger.info("Scheduler shutdown")
        
    def _update_status_page(self):
        """Update the status.html page with current task information."""
        recent = self.db.get_recent_executions(10)
        jobs = self.scheduler.get_jobs()
        # Sort jobs by next run time
        next_jobs = sorted(jobs, key=lambda x: x.next_run_time) if jobs else []
        self.status_page.update(recent, next_jobs)

    def _process_job(self, task_id: int, name: str, script_path: str, arguments: List[str]):
        """
        Process a single job.
        
        Args:
            task_id: ID of the task
            name: Name of the task
            script_path: Path to the script to run
            arguments: Arguments for the script
        """
        success = self.script_runner.run_script(script_path, arguments)
        if success:
            self.logger.info(f"Successfully executed task '{name}': {script_path}")
        else:
            self.logger.error(f"Failed to execute task '{name}': {script_path}")
        
        # Record the execution
        self.db.add_task_execution(task_id, success)
        
        # Update the status page
        self._update_status_page()
    
    def _schedule_task(self, task_id: int, name: str, script_path: str, interval: int, arguments: Optional[List[str]] = None):
        """
        Schedule a task in the APScheduler.
        
        Args:
            task_id: ID of the task
            name: Name of the task
            script_path: Path to the Python script
            interval: Interval in minutes
            arguments: List of command line arguments for the script
        """
        # Create unique job ID using task ID
        job_id = f"job_{task_id}"
        
        # Add the job to the scheduler
        self.scheduler.add_job(
            func=self._process_job,
            trigger=IntervalTrigger(minutes=interval),
            args=[task_id, name, script_path, arguments or []],
            next_run_time=datetime.now(),  # Start immediately
            id=job_id,  # Use script path as unique ID
            replace_existing=True,  # Replace if job exists
            name=name  # Store task name
        )
    
    def add_task(self, name: str, script_path: str, interval: int, arguments: Optional[List[str]] = None):
        """
        Add a new task to both database and scheduler.
        
        Args:
            name: Name of the task
            script_path: Path to the Python script
            interval: Interval in minutes
            arguments: List of command line arguments for the script
        """
        try:
            # Add to database first and get the task ID
            task_id = self.db.add_task(name, script_path, interval, arguments)
            
            # Schedule the task with the ID
            self._schedule_task(task_id, name, script_path, interval, arguments)
            
            self.logger.info(
                f"Added task '{name}': {script_path} with interval {interval} minutes"
                f"{' and arguments: ' + ' '.join(arguments) if arguments else ''}"
            )
            
        except Exception as e:
            self.logger.error(f"Error adding task '{name}' ({script_path}): {str(e)}")
            raise
    
    def remove_task(self, task_id: int):
        """
        Remove a task from both database and scheduler.
        
        Args:
            task_id: ID of the task to remove
        """
        try:
            # Get task details before removal
            tasks = self.db.get_all_tasks()
            task = next((t for t in tasks if t['id'] == task_id), None)
            
            if task:
                # Remove from database first
                self.db.remove_task(task_id)
                
                # Only try to remove from scheduler if it's running
                if self.scheduler.running:
                    try:
                        job_id = f"job_{task_id}"
                        self.scheduler.remove_job(job_id)
                    except Exception as e:
                        # Log but don't fail if job removal fails
                        self.logger.warning(f"Could not remove job from scheduler: {str(e)}")
                
                self.logger.info(f"Removed task '{task['name']}' (ID: {task_id})")
            else:
                self.logger.error(f"Task with ID {task_id} not found")
                raise ValueError(f"Task with ID {task_id} not found")
                
        except ValueError:
            # Re-raise ValueError for task not found
            raise
        except Exception as e:
            self.logger.error(f"Error removing task {task_id}: {str(e)}")
            raise
    
    def list_tasks(self) -> List[Dict]:
        """
        Get a list of all tasks with their next run times.
        
        Returns:
            List of task dictionaries with additional scheduler information
        """
        tasks = self.db.get_all_tasks()
        scheduler_jobs = {job.id: job for job in self.scheduler.get_jobs()}
        
        for task in tasks:
            job_id = f"job_{task['id']}"
            if job_id in scheduler_jobs:
                task['next_run_time'] = scheduler_jobs[job_id].next_run_time
            else:
                task['next_run_time'] = None
        
        return tasks

import json
import os
import sqlite3
from typing import List, Optional, Dict
from datetime import datetime

class Database:
    """Handle SQLite database operations for task storage."""
    
    def __init__(self, db_path: str = None):
        """Initialize database connection and create tables if needed."""
        if db_path is None:
            # Get the directory where the script is located
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(script_dir, "data")
            # Create data directory if it doesn't exist
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "tasks.sqlite")
        self.db_path = db_path
        self._create_tables()
    
    def _create_tables(self):
        """Create the necessary database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            # Create tasks table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    script_path TEXT NOT NULL,
                    arguments TEXT,
                    interval INTEGER NOT NULL
                )
            """)
            
            # Create task history table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    execution_time DATETIME NOT NULL,
                    success BOOLEAN NOT NULL,
                    FOREIGN KEY (task_id) REFERENCES tasks(id)
                )
            """)
    
    def add_task(self, name: str, script_path: str, interval: int, arguments: Optional[List[str]] = None) -> int:
        """
        Add a new task to the database.
        
        Args:
            name: Descriptive name of the task
            script_path: Path to the Python script
            interval: Interval in minutes
            arguments: Optional list of command line arguments
            
        Returns:
            int: ID of the newly added task
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO tasks (name, script_path, arguments, interval) VALUES (?, ?, ?, ?)",
                (name, script_path, json.dumps(arguments or []), interval)
            )
            return cursor.lastrowid
    
    def get_all_tasks(self) -> List[Dict]:
        """
        Get all tasks from the database.
        
        Returns:
            List of task dictionaries containing id, name, script_path, arguments, and interval
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM tasks")
            tasks = []
            for row in cursor:
                task = dict(row)
                task['arguments'] = json.loads(task['arguments'])
                tasks.append(task)
            return tasks
    
    def remove_task(self, task_id: int):
        """
        Remove a task from the database.
        
        Args:
            task_id: ID of the task to remove
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    
    def add_task_execution(self, task_id: int, success: bool):
        """
        Record a task execution in the history.
        
        Args:
            task_id: ID of the executed task
            success: Whether the execution was successful
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO task_history (task_id, execution_time, success) VALUES (?, datetime('now'), ?)",
                (task_id, success)
            )
    
    def get_recent_executions(self, limit: int = 10) -> List[Dict]:
        """
        Get the most recent task executions.
        
        Args:
            limit: Maximum number of executions to return
            
        Returns:
            List of execution records with task details
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT 
                    h.id as execution_id,
                    h.execution_time,
                    h.success,
                    t.id as task_id,
                    t.name,
                    t.script_path,
                    t.arguments
                FROM task_history h
                JOIN tasks t ON h.task_id = t.id
                ORDER BY h.execution_time DESC
                LIMIT ?
            """, (limit,))
            
            executions = []
            for row in cursor:
                execution = dict(row)
                execution['arguments'] = json.loads(execution['arguments'])
                executions.append(execution)
            return executions
    
    def clear_all_tasks(self):
        """Remove all tasks and their history from the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM task_history")
            conn.execute("DELETE FROM tasks")

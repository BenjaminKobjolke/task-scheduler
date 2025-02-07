import json
import sqlite3
from typing import List, Optional, Dict
from datetime import datetime

class Database:
    """Handle SQLite database operations for task storage."""
    
    def __init__(self, db_path: str = "data/tasks.sqlite"):
        """Initialize database connection and create tables if needed."""
        self.db_path = db_path
        self._create_tables()
    
    def _create_tables(self):
        """Create the necessary database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    script_path TEXT NOT NULL,
                    arguments TEXT,
                    interval INTEGER NOT NULL
                )
            """)
    
    def add_task(self, name: str, script_path: str, interval: int, arguments: Optional[List[str]] = None):
        """
        Add a new task to the database.
        
        Args:
            name: Descriptive name of the task
            script_path: Path to the Python script
            interval: Interval in minutes
            arguments: Optional list of command line arguments
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO tasks (name, script_path, arguments, interval) VALUES (?, ?, ?, ?)",
                (name, script_path, json.dumps(arguments or []), interval)
            )
    
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
    
    def clear_all_tasks(self):
        """Remove all tasks from the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM tasks")

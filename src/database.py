import json
import os
import sqlite3
from typing import List, Optional, Dict
from datetime import datetime
from .logger import Logger
from .constants import Paths, Database as DbConstants, Defaults, TaskTypes

class Database:
    """Handle SQLite database operations for task storage."""
    
    def __init__(self, db_path: str = None):
        """Initialize database connection and create tables if needed."""
        self.logger = Logger("Database")
        if db_path is None:
            # Get the directory where the script is located
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(script_dir, Paths.DATA_DIR)
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
                    interval INTEGER NOT NULL,
                    task_type TEXT DEFAULT 'script',
                    command TEXT
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

            # Migration: Add columns if they don't exist (for existing databases)
            self._migrate_add_column(conn, DbConstants.TABLE_TASKS, DbConstants.COL_TASK_TYPE, "TEXT DEFAULT 'script'")
            self._migrate_add_column(conn, DbConstants.TABLE_TASKS, DbConstants.COL_COMMAND, "TEXT")

    def _migrate_add_column(self, conn, table: str, column: str, definition: str):
        """Add a column to a table if it doesn't exist."""
        cursor = conn.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            self.logger.info(f"Migrated database: added column '{column}' to table '{table}'")
    
    def add_task(
        self,
        name: str,
        script_path: str,
        interval: int,
        arguments: Optional[List[str]] = None,
        task_type: str = TaskTypes.SCRIPT,
        command: Optional[str] = None
    ) -> int:
        """
        Add a new task to the database.

        Args:
            name: Descriptive name of the task
            script_path: Path to the Python script (or project directory for uv_command)
            interval: Interval in minutes
            arguments: Optional list of command line arguments
            task_type: Type of task ('script' or 'uv_command')
            command: Command name for uv_command tasks

        Returns:
            int: ID of the newly added task
        """
        with sqlite3.connect(self.db_path) as conn:
            # Store arguments exactly as provided
            json_args = json.dumps(arguments, ensure_ascii=False) if arguments else "[]"

            # Log argument details if enabled
            if self.logger.is_detailed_logging_enabled():
                self.logger.log_arguments(arguments, "Database Add Task Arguments")
                self.logger.debug(f"JSON stored in database: {json_args}")

            cursor = conn.execute(
                "INSERT INTO tasks (name, script_path, arguments, interval, task_type, command) VALUES (?, ?, ?, ?, ?, ?)",
                (name, script_path, json_args, interval, task_type, command)
            )
            return cursor.lastrowid
    
    def get_all_tasks(self) -> List[Dict]:
        """
        Get all tasks from the database.

        Returns:
            List of task dictionaries containing id, name, script_path, arguments, interval, task_type, command
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM tasks")
            tasks = []
            for row in cursor:
                task = dict(row)
                raw_args = task['arguments']
                task['arguments'] = json.loads(raw_args)

                # Ensure backwards compatibility: default task_type to 'script' if None
                if task.get('task_type') is None:
                    task['task_type'] = TaskTypes.SCRIPT

                # Log argument details if enabled
                if self.logger.is_detailed_logging_enabled():
                    self.logger.debug(f"Raw JSON from database: {raw_args}")
                    self.logger.log_arguments(task['arguments'], f"Loading Task {task['id']} Arguments")

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
                "INSERT INTO task_history (task_id, execution_time, success) VALUES (?, datetime('now', 'localtime'), ?)",
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
                    t.arguments,
                    t.task_type,
                    t.command
                FROM task_history h
                JOIN tasks t ON h.task_id = t.id
                ORDER BY h.execution_time DESC
                LIMIT ?
            """, (limit,))

            executions = []
            for row in cursor:
                execution = dict(row)
                raw_args = execution['arguments']
                execution['arguments'] = json.loads(raw_args)

                # Ensure backwards compatibility: default task_type to 'script' if None
                if execution.get('task_type') is None:
                    execution['task_type'] = TaskTypes.SCRIPT

                # Log argument details if enabled
                if self.logger.is_detailed_logging_enabled():
                    self.logger.debug(f"Raw JSON from database: {raw_args}")
                    self.logger.log_arguments(
                        execution['arguments'],
                        f"Loading Execution {execution['execution_id']} Arguments"
                    )

                executions.append(execution)
            return executions
    
    def edit_task(
        self,
        task_id: int,
        name: str,
        script_path: str,
        interval: int,
        arguments: Optional[List[str]] = None,
        task_type: str = TaskTypes.SCRIPT,
        command: Optional[str] = None
    ) -> bool:
        """
        Edit an existing task in the database.

        Args:
            task_id: ID of the task to edit
            name: New name for the task
            script_path: New path to the Python script (or project directory for uv_command)
            interval: New interval in minutes
            arguments: New list of command line arguments
            task_type: Type of task ('script' or 'uv_command')
            command: Command name for uv_command tasks

        Returns:
            bool: True if task was found and updated, False otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            # Store arguments exactly as provided
            json_args = json.dumps(arguments, ensure_ascii=False) if arguments else "[]"

            # Log argument details if enabled
            if self.logger.is_detailed_logging_enabled():
                self.logger.log_arguments(arguments, "Database Edit Task Arguments")
                self.logger.debug(f"JSON stored in database: {json_args}")

            cursor = conn.execute(
                """
                UPDATE tasks
                SET name = ?, script_path = ?, arguments = ?, interval = ?, task_type = ?, command = ?
                WHERE id = ?
                """,
                (name, script_path, json_args, interval, task_type, command, task_id)
            )
            return cursor.rowcount > 0
            
    def clear_all_tasks(self):
        """Remove all tasks and their history from the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM task_history")
            conn.execute("DELETE FROM tasks")

"""Read execution history from the scheduler's SQLite database."""

import json
import sqlite3
from typing import Dict, List

from .constants import TaskTypes
from .logger import Logger


class ExecutionHistoryQueries:
    """Provide execution-history queries used by the database facade."""

    def __init__(self, db_path: str, logger: Logger):
        self.db_path = db_path
        self.logger = logger

    def get_recent_executions(self, limit: int = 10) -> List[Dict]:
        """Return recent executions with their task details."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
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
            """,
                (limit,),
            )

            executions = []
            for row in cursor:
                execution = dict(row)
                raw_args = execution["arguments"]
                execution["arguments"] = json.loads(raw_args)

                if execution.get("task_type") is None:
                    execution["task_type"] = TaskTypes.SCRIPT

                if self.logger.is_detailed_logging_enabled():
                    self.logger.debug(f"Raw JSON from database: {raw_args}")
                    self.logger.log_arguments(
                        execution["arguments"],
                        f"Loading Execution {execution['execution_id']} Arguments",
                    )

                executions.append(execution)
            return executions

    def get_last_execution_per_task(self) -> Dict[int, Dict]:
        """Return the most recent execution time and result for each task."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT h.task_id, h.execution_time, h.success
                FROM task_history h
                INNER JOIN (
                    SELECT task_id, MAX(execution_time) as max_time
                    FROM task_history
                    GROUP BY task_id
                ) latest ON h.task_id = latest.task_id AND h.execution_time = latest.max_time
            """)

            result = {}
            for row in cursor:
                result[row["task_id"]] = {
                    "execution_time": row["execution_time"],
                    "success": bool(row["success"]),
                }
            return result

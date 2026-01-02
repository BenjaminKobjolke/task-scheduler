"""Constants used throughout the task-scheduler application."""


class Paths:
    """File and directory path constants."""
    VENV_DIR = "venv"
    SCRIPTS_DIR = "Scripts"
    ACTIVATE_SCRIPT = "activate"
    PYTHON_EXE = "python.exe"
    DATA_DIR = "data"
    LOGS_DIR = "logs"
    PYPROJECT_TOML = "pyproject.toml"
    UV_LOCK = "uv.lock"
    BAT_EXTENSION = ".bat"


class Database:
    """Database table and column name constants."""
    TABLE_TASKS = "tasks"
    TABLE_HISTORY = "task_history"
    COL_ID = "id"
    COL_NAME = "name"
    COL_SCRIPT_PATH = "script_path"
    COL_ARGUMENTS = "arguments"
    COL_INTERVAL = "interval"
    COL_TASK_TYPE = "task_type"
    COL_COMMAND = "command"
    COL_TASK_ID = "task_id"
    COL_EXECUTION_TIME = "execution_time"
    COL_SUCCESS = "success"


class Config:
    """Configuration section and key constants."""
    SECTION_LOGGING = "Logging"
    KEY_LEVEL = "level"
    KEY_DETAILED_ARGS = "detailed_args_logging"
    DEFAULT_LEVEL = "INFO"
    DEFAULT_DETAILED = "false"


class TaskTypes:
    """Task type constants."""
    SCRIPT = "script"
    UV_COMMAND = "uv_command"


class Defaults:
    """Default values used throughout the application."""
    HISTORY_LIMIT = 10
    MISFIRE_GRACE_TIME = 60
    MIN_INTERVAL = 1

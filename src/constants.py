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
    COL_START_TIME = "start_time"


class Config:
    """Configuration section and key constants."""
    # Logging section
    SECTION_LOGGING = "Logging"
    KEY_LEVEL = "level"
    KEY_DETAILED_ARGS = "detailed_args_logging"
    DEFAULT_LEVEL = "INFO"
    DEFAULT_DETAILED = "false"

    # StatusPage section
    SECTION_STATUS_PAGE = "StatusPage"
    KEY_OUTPUT_TYPE = "output_type"
    KEY_OUTPUT_PATH = "output_path"
    KEY_PHP_PASSWORD = "php_password"
    KEY_PHP_LOGIN_LIBRARY_PATH = "php_login_library_path"
    DEFAULT_OUTPUT_TYPE = "html"
    DEFAULT_OUTPUT_PATH = "web"
    DEFAULT_PHP_PASSWORD = "changeme"
    DEFAULT_PHP_LOGIN_LIBRARY_PATH = ""

    # FTP section
    SECTION_FTP = "FTP"
    KEY_FTP_ENABLED = "enabled"
    KEY_FTP_HOST = "host"
    KEY_FTP_PORT = "port"
    KEY_FTP_USERNAME = "username"
    KEY_FTP_PASSWORD = "password"
    KEY_FTP_REMOTE_PATH = "remote_path"
    KEY_FTP_PASSIVE_MODE = "passive_mode"
    KEY_FTP_TIMEOUT = "timeout"
    KEY_FTP_SYNC_INTERVAL = "sync_interval"
    DEFAULT_FTP_ENABLED = "false"
    DEFAULT_FTP_HOST = ""
    DEFAULT_FTP_PORT = "21"
    DEFAULT_FTP_USERNAME = ""
    DEFAULT_FTP_PASSWORD = ""
    DEFAULT_FTP_REMOTE_PATH = "/"
    DEFAULT_FTP_PASSIVE_MODE = "true"
    DEFAULT_FTP_TIMEOUT = "30"
    DEFAULT_FTP_SYNC_INTERVAL = "5"


class TaskTypes:
    """Task type constants."""
    SCRIPT = "script"
    UV_COMMAND = "uv_command"


class Defaults:
    """Default values used throughout the application."""
    HISTORY_LIMIT = 10
    MISFIRE_GRACE_TIME = 60
    MIN_INTERVAL = 1
    RELOAD_INTERVAL = 60  # seconds between database checks for hot-reload

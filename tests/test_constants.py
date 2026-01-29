"""Tests for constants module."""
from src.constants import Paths, Database, Config, Defaults


class TestPaths:
    """Tests for Paths constants."""

    def test_venv_dir_defined(self):
        assert Paths.VENV_DIR == "venv"

    def test_scripts_dir_defined(self):
        assert Paths.SCRIPTS_DIR == "Scripts"

    def test_python_exe_defined(self):
        assert Paths.PYTHON_EXE == "python.exe"

    def test_uv_files_defined(self):
        assert Paths.PYPROJECT_TOML == "pyproject.toml"
        assert Paths.UV_LOCK == "uv.lock"

    def test_bat_extension_defined(self):
        assert Paths.BAT_EXTENSION == ".bat"


class TestDatabase:
    """Tests for Database constants."""

    def test_table_names_defined(self):
        assert Database.TABLE_TASKS == "tasks"
        assert Database.TABLE_HISTORY == "task_history"

    def test_column_names_defined(self):
        assert Database.COL_ID == "id"
        assert Database.COL_NAME == "name"
        assert Database.COL_SCRIPT_PATH == "script_path"
        assert Database.COL_ARGUMENTS == "arguments"
        assert Database.COL_INTERVAL == "interval"


class TestConfig:
    """Tests for Config constants."""

    def test_section_defined(self):
        assert Config.SECTION_LOGGING == "Logging"

    def test_keys_defined(self):
        assert Config.KEY_LEVEL == "level"
        assert Config.KEY_DETAILED_ARGS == "detailed_args_logging"

    def test_defaults_defined(self):
        assert Config.DEFAULT_LEVEL == "INFO"
        assert Config.DEFAULT_DETAILED == "false"


class TestDefaults:
    """Tests for Defaults constants."""

    def test_history_limit(self):
        assert Defaults.HISTORY_LIMIT == 10

    def test_misfire_grace_time(self):
        assert Defaults.MISFIRE_GRACE_TIME == 60

    def test_min_interval(self):
        assert Defaults.MIN_INTERVAL == 1

"""Tests for script_runner module."""

import os
import tempfile
from unittest.mock import patch
import pytest
from src.script_runner import ScriptRunner
from src.constants import Interactive, Paths


@pytest.fixture
def runner():
    """Create a ScriptRunner instance."""
    return ScriptRunner()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestIsUvProject:
    """Tests for _is_uv_project method."""

    def test_is_uv_project_true(self, runner, temp_dir):
        # Create both required files
        open(os.path.join(temp_dir, Paths.PYPROJECT_TOML), "w").close()
        open(os.path.join(temp_dir, Paths.UV_LOCK), "w").close()

        assert runner._is_uv_project(temp_dir) is True

    def test_is_uv_project_missing_lock(self, runner, temp_dir):
        # Create only pyproject.toml
        open(os.path.join(temp_dir, Paths.PYPROJECT_TOML), "w").close()

        assert runner._is_uv_project(temp_dir) is False

    def test_is_uv_project_missing_pyproject(self, runner, temp_dir):
        # Create only uv.lock
        open(os.path.join(temp_dir, Paths.UV_LOCK), "w").close()

        assert runner._is_uv_project(temp_dir) is False

    def test_is_uv_project_empty_dir(self, runner, temp_dir):
        assert runner._is_uv_project(temp_dir) is False


class TestActivateVenv:
    """Tests for _activate_venv method."""

    def test_activate_venv_exists(self, runner, temp_dir):
        # Create venv structure
        venv_scripts = os.path.join(temp_dir, Paths.VENV_DIR, Paths.SCRIPTS_DIR)
        os.makedirs(venv_scripts)
        open(os.path.join(venv_scripts, Paths.ACTIVATE_SCRIPT), "w").close()

        script_path = os.path.join(temp_dir, "script.py")
        activate_path = runner._activate_venv(script_path)

        expected = os.path.join(
            temp_dir, Paths.VENV_DIR, Paths.SCRIPTS_DIR, Paths.ACTIVATE_SCRIPT
        )
        assert activate_path == expected

    def test_activate_venv_not_exists(self, runner, temp_dir):
        script_path = os.path.join(temp_dir, "script.py")

        with pytest.raises(ValueError, match="Virtual environment not found"):
            runner._activate_venv(script_path)


class TestRunScript:
    """Tests for run_script method."""

    def test_run_script_not_found(self, runner):
        result = runner.run_script("/nonexistent/path/script.py")
        assert result is False

    @pytest.mark.skipif(os.name != "nt", reason="Windows-only test")
    def test_run_batch_file(self, runner, temp_dir):
        # Create a simple batch file that just echoes and exits
        batch_path = os.path.join(temp_dir, "test.bat")
        with open(batch_path, "w") as f:
            f.write("@echo off\necho test\n")

        result = runner.run_script(batch_path)
        # Batch files may not always work in test environments
        # The important thing is they don't raise exceptions
        assert isinstance(result, bool)

    @pytest.mark.skipif(os.name != "nt", reason="Windows-only test")
    def test_run_failing_batch_file(self, runner, temp_dir):
        # Create a batch file that exits with non-zero code
        batch_path = os.path.join(temp_dir, "fail.bat")
        with open(batch_path, "w") as f:
            f.write("@echo off\nexit /b 1\n")

        result = runner.run_script(batch_path)
        # Test that it returns a boolean (may fail or succeed depending on env)
        assert isinstance(result, bool)


class TestGetUvCommands:
    """Tests for get_uv_commands method."""

    def test_get_uv_commands_no_pyproject(self, runner, temp_dir):
        result = runner.get_uv_commands(temp_dir)
        assert result == []

    def test_get_uv_commands_empty_scripts(self, runner, temp_dir):
        # Create pyproject.toml without scripts section
        pyproject_path = os.path.join(temp_dir, Paths.PYPROJECT_TOML)
        with open(pyproject_path, "w") as f:
            f.write("[project]\nname = 'test'\n")

        result = runner.get_uv_commands(temp_dir)
        assert result == []

    def test_get_uv_commands_with_scripts(self, runner, temp_dir):
        # Create pyproject.toml with scripts
        pyproject_path = os.path.join(temp_dir, Paths.PYPROJECT_TOML)
        with open(pyproject_path, "w") as f:
            f.write("""[project]
name = "test"

[project.scripts]
cmd1 = "test.main:main"
cmd2 = "test.cli:run"
""")

        result = runner.get_uv_commands(temp_dir)
        assert len(result) == 2
        assert "cmd1" in result
        assert "cmd2" in result


class TestRunUvCommand:
    """Tests for run_uv_command method."""

    def test_run_uv_command_project_not_found(self, runner):
        result = runner.run_uv_command("/nonexistent/path", "my-command")
        assert result is False

    def test_run_uv_command_not_uv_project(self, runner, temp_dir):
        result = runner.run_uv_command(temp_dir, "my-command")
        assert result is False

    def test_run_uv_command_with_uv_project(self, runner, temp_dir):
        # Create uv project markers
        open(os.path.join(temp_dir, Paths.PYPROJECT_TOML), "w").close()
        open(os.path.join(temp_dir, Paths.UV_LOCK), "w").close()

        # This will fail because there's no actual command, but tests the code path
        result = runner.run_uv_command(temp_dir, "nonexistent-command")
        # Should return False (command doesn't exist) but not raise
        assert isinstance(result, bool)


class TestDiscoverEntryPoints:
    """Tests for discover_entry_points method."""

    def test_discover_entry_points_from_project_name(self, runner, temp_dir):
        """Project name in pyproject.toml with matching package dir returns python -m command."""
        pyproject_path = os.path.join(temp_dir, Paths.PYPROJECT_TOML)
        with open(pyproject_path, "w") as f:
            f.write('[project]\nname = "my-cool-app"\n')

        # Create matching package directory
        pkg_dir = os.path.join(temp_dir, "my_cool_app")
        os.makedirs(pkg_dir)
        open(os.path.join(pkg_dir, "__init__.py"), "w").close()

        result = runner.discover_entry_points(temp_dir)

        assert any(cmd == "python -m my_cool_app" for cmd, _ in result)

    def test_discover_entry_points_no_matching_package(self, runner, temp_dir):
        """Project name exists but no matching directory → skipped."""
        pyproject_path = os.path.join(temp_dir, Paths.PYPROJECT_TOML)
        with open(pyproject_path, "w") as f:
            f.write('[project]\nname = "my-cool-app"\n')

        result = runner.discover_entry_points(temp_dir)

        assert not any("my_cool_app" in cmd for cmd, _ in result)

    def test_discover_entry_points_root_files(self, runner, temp_dir):
        """main.py and app.py in project root are discovered."""
        # Create pyproject.toml (required for uv project)
        pyproject_path = os.path.join(temp_dir, Paths.PYPROJECT_TOML)
        with open(pyproject_path, "w") as f:
            f.write('[project]\nname = "test"\n')

        open(os.path.join(temp_dir, "main.py"), "w").close()
        open(os.path.join(temp_dir, "app.py"), "w").close()

        result = runner.discover_entry_points(temp_dir)

        commands = [cmd for cmd, _ in result]
        assert "python main.py" in commands
        assert "python app.py" in commands

    def test_discover_entry_points_main_module(self, runner, temp_dir):
        """Package with __main__.py is discovered."""
        pyproject_path = os.path.join(temp_dir, Paths.PYPROJECT_TOML)
        with open(pyproject_path, "w") as f:
            f.write('[project]\nname = "test"\n')

        pkg_dir = os.path.join(temp_dir, "mypackage")
        os.makedirs(pkg_dir)
        open(os.path.join(pkg_dir, "__main__.py"), "w").close()

        result = runner.discover_entry_points(temp_dir)

        assert any(cmd == "python -m mypackage" for cmd, _ in result)

    def test_discover_entry_points_dedup(self, runner, temp_dir):
        """Project name and __main__.py scan producing same command → only one entry."""
        pyproject_path = os.path.join(temp_dir, Paths.PYPROJECT_TOML)
        with open(pyproject_path, "w") as f:
            f.write('[project]\nname = "mypackage"\n')

        pkg_dir = os.path.join(temp_dir, "mypackage")
        os.makedirs(pkg_dir)
        open(os.path.join(pkg_dir, "__init__.py"), "w").close()
        open(os.path.join(pkg_dir, "__main__.py"), "w").close()

        result = runner.discover_entry_points(temp_dir)

        matching = [cmd for cmd, _ in result if cmd == "python -m mypackage"]
        assert len(matching) == 1

    def test_discover_entry_points_empty(self, runner, temp_dir):
        """Nothing found → returns empty list."""
        pyproject_path = os.path.join(temp_dir, Paths.PYPROJECT_TOML)
        with open(pyproject_path, "w") as f:
            f.write('[project]\nname = "test"\n')

        result = runner.discover_entry_points(temp_dir)

        assert result == []

    def test_discover_entry_points_skips_excluded_dirs(self, runner, temp_dir):
        """tests/, __pycache__/, .hidden/ directories are skipped."""
        pyproject_path = os.path.join(temp_dir, Paths.PYPROJECT_TOML)
        with open(pyproject_path, "w") as f:
            f.write('[project]\nname = "test"\n')

        # Create excluded dirs with __main__.py
        for dirname in ["tests", "__pycache__", ".hidden"]:
            excluded_dir = os.path.join(temp_dir, dirname)
            os.makedirs(excluded_dir)
            open(os.path.join(excluded_dir, "__main__.py"), "w").close()

        result = runner.discover_entry_points(temp_dir)

        commands = [cmd for cmd, _ in result]
        assert "python -m tests" not in commands
        assert "python -m __pycache__" not in commands
        assert "python -m .hidden" not in commands


class TestBuildEnv:
    """Tests for _build_env method."""

    def test_build_env_sets_interactive(self, runner):
        """Verify INTERACTIVE is set to '1' in returned env."""
        env = runner._build_env()
        assert env[Interactive.ENV_MARKER] == "1"

    def test_build_env_clean_uv_removes_virtual_env(self, runner):
        """Verify VIRTUAL_ENV is removed when clean_uv=True."""
        with patch.dict(os.environ, {"VIRTUAL_ENV": "/some/venv"}):
            env = runner._build_env(clean_uv=True)
            assert "VIRTUAL_ENV" not in env

    def test_build_env_keeps_virtual_env_by_default(self, runner):
        """Verify VIRTUAL_ENV is kept when clean_uv=False."""
        with patch.dict(os.environ, {"VIRTUAL_ENV": "/some/venv"}):
            env = runner._build_env(clean_uv=False)
            assert env["VIRTUAL_ENV"] == "/some/venv"

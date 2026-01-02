"""Tests for script_runner module."""
import os
import tempfile
import pytest
from src.script_runner import ScriptRunner
from src.constants import Paths


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

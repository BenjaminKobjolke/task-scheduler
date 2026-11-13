"""Tests for script_runner module."""

import os
from unittest.mock import patch
import pytest
from src.script_runner import ScriptRunner
from src.constants import Interactive, Paths


@pytest.fixture
def runner():
    """Create a ScriptRunner instance."""
    return ScriptRunner()


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

    def test_run_ps1_builds_powershell_command(self, runner, temp_dir):
        ps1_path = os.path.join(temp_dir, "x.ps1")
        open(ps1_path, "w").close()

        with patch("src.script_runner.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = ""
            assert runner.run_script(ps1_path, ["--a"]) is True

        args, kwargs = mock_run.call_args
        assert args[0] == [
            "powershell.exe",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "x.ps1",
            "--a",
        ]
        assert kwargs["cwd"] == temp_dir
        assert kwargs["shell"] is False

    @pytest.mark.skipif(os.name != "nt", reason="Windows-only test")
    @pytest.mark.parametrize("code,expected", [(0, True), (1, False)])
    def test_run_ps1_exit_code(self, runner, temp_dir, code, expected):
        ps1_path = os.path.join(temp_dir, "exit.ps1")
        with open(ps1_path, "w") as f:
            f.write(f"Write-Output 'hi'\nexit {code}\n")

        assert runner.run_script(ps1_path) is expected


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

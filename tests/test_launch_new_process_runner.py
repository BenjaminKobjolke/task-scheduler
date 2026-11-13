"""Tests for launch_new_process feature."""

import os
import subprocess
from unittest.mock import MagicMock, patch



from src.constants import TaskTypes
from src.script_runner import ScriptRunner


# ---------------------------------------------------------------------------
# Database tests
# ---------------------------------------------------------------------------




class TestScriptRunnerLaunchInNewConsole:
    """Tests for launch_in_new_console method."""

    def test_launch_script_uses_popen_with_create_new_console(self):
        """launch_in_new_console should use Popen with CREATE_NEW_CONSOLE."""
        runner = ScriptRunner()
        script_path = os.path.abspath("C:/scripts/test.py")
        script_dir = os.path.dirname(script_path)

        with patch.object(runner, "_is_uv_project", return_value=False):
            with patch.object(runner, "_activate_venv") as mock_venv:
                mock_venv.return_value = os.path.join(
                    script_dir, "venv", "Scripts", "activate"
                )
                with patch("os.path.exists", return_value=True):
                    with patch("subprocess.Popen") as mock_popen:
                        mock_popen.return_value = MagicMock()
                        result = runner.launch_in_new_console(
                            script_path, [], TaskTypes.SCRIPT, None
                        )

                        assert result is True
                        mock_popen.assert_called_once()
                        call_kwargs = mock_popen.call_args
                        assert (
                            call_kwargs.kwargs.get("creationflags")
                            == subprocess.CREATE_NEW_CONSOLE
                        )

    def test_launch_batch_file_uses_create_new_console(self):
        """launch_in_new_console should handle batch files."""
        runner = ScriptRunner()
        script_path = "C:/scripts/test.bat"

        with patch("os.path.exists", return_value=True):
            with patch("subprocess.Popen") as mock_popen:
                mock_popen.return_value = MagicMock()
                result = runner.launch_in_new_console(
                    script_path, [], TaskTypes.SCRIPT, None
                )

                assert result is True
                mock_popen.assert_called_once()
                call_kwargs = mock_popen.call_args
                assert (
                    call_kwargs.kwargs.get("creationflags")
                    == subprocess.CREATE_NEW_CONSOLE
                )

    def test_launch_ps1_uses_powershell(self):
        """launch_in_new_console should run .ps1 files via powershell.exe."""
        runner = ScriptRunner()
        script_path = "C:/scripts/renew.ps1"

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            result = runner.launch_in_new_console(
                script_path, ["-Force"], TaskTypes.SCRIPT, None
            )

            assert result is True
            assert mock_popen.call_args.args[0] == [
                "powershell.exe",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                "renew.ps1",
                "-Force",
            ]
            assert (
                mock_popen.call_args.kwargs.get("creationflags")
                == subprocess.CREATE_NEW_CONSOLE
            )

    def test_launch_uv_command_uses_create_new_console(self):
        """launch_in_new_console should handle uv commands."""
        runner = ScriptRunner()
        project_dir = "C:/projects/myproject"

        with patch("os.path.isdir", return_value=True):
            with patch.object(runner, "_is_uv_project", return_value=True):
                with patch("subprocess.Popen") as mock_popen:
                    mock_popen.return_value = MagicMock()
                    result = runner.launch_in_new_console(
                        project_dir, ["--verbose"], TaskTypes.UV_COMMAND, "my-command"
                    )

                    assert result is True
                    mock_popen.assert_called_once()
                    call_kwargs = mock_popen.call_args
                    assert (
                        call_kwargs.kwargs.get("creationflags")
                        == subprocess.CREATE_NEW_CONSOLE
                    )

    def test_launch_returns_false_on_exception(self):
        """launch_in_new_console should return False on errors."""
        runner = ScriptRunner()

        with patch("os.path.exists", return_value=True):
            with patch("subprocess.Popen", side_effect=OSError("fail")):
                result = runner.launch_in_new_console(
                    "C:/scripts/test.bat", [], TaskTypes.SCRIPT, None
                )
                assert result is False

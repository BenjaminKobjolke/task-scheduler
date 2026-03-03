"""Tests for ScriptRunner interactive execution via _run_interactive()."""

import os
import tempfile

import pytest
from unittest.mock import MagicMock, patch

from src.interaction import (
    InteractionHandler,
    InteractionResponse,
    InteractionType,
)
from src.script_runner import ScriptRunner


@pytest.fixture
def runner():
    """Create a ScriptRunner instance."""
    return ScriptRunner()


@pytest.fixture
def mock_handler():
    """Create a mock InteractionHandler."""
    handler = MagicMock(spec=InteractionHandler)
    return handler


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestRunInteractiveMethod:
    """Tests for the _run_interactive() private method."""

    def test_interactive_confirm_roundtrip(self, runner, mock_handler, temp_dir):
        """Script sends confirm prompt, receives response, prints result."""
        # Create a script that sends a confirm prompt and prints the response
        script_path = os.path.join(temp_dir, "interactive_test.py")
        with open(script_path, "w") as f:
            f.write(
                'import json, sys\n'
                'prompt = {"_interactive": True, "type": "confirm", "id": "q1", "message": "Continue?"}\n'
                'print(json.dumps(prompt), flush=True)\n'
                'response = json.loads(input())\n'
                'if response["value"]:\n'
                '    print("confirmed")\n'
                'else:\n'
                '    print("denied")\n'
            )

        mock_handler.handle_prompt.return_value = InteractionResponse(
            id="q1", value=True
        )

        success = runner._run_interactive(
            cmd=["python", "interactive_test.py"],
            cwd=temp_dir,
            env=None,
            shell=False,
            interaction_handler=mock_handler,
        )

        assert success is True
        mock_handler.handle_prompt.assert_called_once()
        call_arg = mock_handler.handle_prompt.call_args[0][0]
        assert call_arg.type == InteractionType.CONFIRM
        assert call_arg.id == "q1"

    def test_interactive_normal_output_logged(self, runner, mock_handler, temp_dir):
        """Non-interactive stdout lines are logged, not parsed as prompts."""
        script_path = os.path.join(temp_dir, "normal_output.py")
        with open(script_path, "w") as f:
            f.write('print("Hello from script")\n')

        success = runner._run_interactive(
            cmd=["python", "normal_output.py"],
            cwd=temp_dir,
            env=None,
            shell=False,
            interaction_handler=mock_handler,
        )

        assert success is True
        mock_handler.handle_prompt.assert_not_called()

    def test_interactive_script_failure(self, runner, mock_handler, temp_dir):
        """Script exits with non-zero code returns False."""
        script_path = os.path.join(temp_dir, "fail.py")
        with open(script_path, "w") as f:
            f.write('import sys; sys.exit(1)\n')

        success = runner._run_interactive(
            cmd=["python", "fail.py"],
            cwd=temp_dir,
            env=None,
            shell=False,
            interaction_handler=mock_handler,
        )

        assert success is False

    def test_interactive_multiple_prompts(self, runner, mock_handler, temp_dir):
        """Script sends multiple prompts, all handled correctly."""
        script_path = os.path.join(temp_dir, "multi.py")
        with open(script_path, "w") as f:
            f.write(
                'import json, sys\n'
                'p1 = {"_interactive": True, "type": "confirm", "id": "q1", "message": "Go?"}\n'
                'print(json.dumps(p1), flush=True)\n'
                'r1 = json.loads(input())\n'
                'p2 = {"_interactive": True, "type": "input", "id": "q2", "message": "Name?"}\n'
                'print(json.dumps(p2), flush=True)\n'
                'r2 = json.loads(input())\n'
                'print(f"Done: {r2[\'value\']}")\n'
            )

        mock_handler.handle_prompt.side_effect = [
            InteractionResponse(id="q1", value=True),
            InteractionResponse(id="q2", value="test-name"),
        ]

        success = runner._run_interactive(
            cmd=["python", "multi.py"],
            cwd=temp_dir,
            env=None,
            shell=False,
            interaction_handler=mock_handler,
        )

        assert success is True
        assert mock_handler.handle_prompt.call_count == 2


class TestRunScriptWithHandler:
    """Tests that run_script passes interaction_handler correctly."""

    def test_run_script_without_handler_uses_subprocess_run(self, runner):
        """When no handler, existing subprocess.run code path is used."""
        result = runner.run_script("/nonexistent/path/script.py")
        assert result is False  # Script not found

    def test_run_script_with_handler_calls_interactive(self, runner, mock_handler, temp_dir):
        """When handler provided, uses _run_interactive path for venv script."""
        # Create venv structure so the venv branch is taken
        venv_scripts = os.path.join(temp_dir, "venv", "Scripts")
        os.makedirs(venv_scripts)
        open(os.path.join(venv_scripts, "activate"), "w").close()
        open(os.path.join(venv_scripts, "python.exe"), "w").close()

        script_path = os.path.join(temp_dir, "ok.py")
        with open(script_path, "w") as f:
            f.write('print("hello")\n')

        with patch.object(runner, "_run_interactive", return_value=True) as mock_interactive:
            result = runner.run_script(script_path, interaction_handler=mock_handler)

        assert result is True
        mock_interactive.assert_called_once()


class TestRunUvCommandWithHandler:
    """Tests that run_uv_command passes interaction_handler correctly."""

    def test_run_uv_command_without_handler(self, runner, temp_dir):
        """No handler → existing code path."""
        result = runner.run_uv_command(temp_dir, "my-command")
        assert result is False  # Not a uv project

    def test_run_uv_command_with_handler_calls_interactive(self, runner, mock_handler, temp_dir):
        """When handler provided, uses _run_interactive path."""
        # Create uv project markers
        open(os.path.join(temp_dir, "pyproject.toml"), "w").close()
        open(os.path.join(temp_dir, "uv.lock"), "w").close()

        with patch.object(runner, "_run_interactive", return_value=True) as mock_interactive:
            result = runner.run_uv_command(
                temp_dir, "my-command", interaction_handler=mock_handler
            )

        assert result is True
        mock_interactive.assert_called_once()

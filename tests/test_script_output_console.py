"""Tests for ScriptOutput protocol and ConsoleScriptOutput implementation."""

import os

import pytest
from unittest.mock import patch

from src.interaction import (
    ConsoleScriptOutput,
    InteractionResponse,
)
from src.script_runner import ScriptRunner


@pytest.fixture
def runner():
    """Create a ScriptRunner instance."""
    return ScriptRunner()


class TestConsoleScriptOutput:
    """Tests for ConsoleScriptOutput."""

    def test_write_line_prints_to_stdout(self, capsys):
        """write_line() prints the line to stdout."""
        output = ConsoleScriptOutput()
        output.write_line("Hello from script")

        captured = capsys.readouterr()
        assert captured.out == "Hello from script\n"

    def test_write_line_empty_string(self, capsys):
        """write_line() handles empty strings."""
        output = ConsoleScriptOutput()
        output.write_line("")

        captured = capsys.readouterr()
        assert captured.out == "\n"


class TestRunInteractiveWithScriptOutput:
    """Tests for _run_interactive() with script_output parameter."""

    def test_output_goes_to_script_output_when_provided(
        self, runner, mock_handler, mock_output, temp_dir
    ):
        """Non-JSON lines go to script_output.write_line() when provided."""
        script_path = os.path.join(temp_dir, "output_test.py")
        with open(script_path, "w") as f:
            f.write('print("line one")\nprint("line two")\n')

        success = runner._run_interactive(
            cmd=["python", "output_test.py"],
            cwd=temp_dir,
            env=None,
            shell=False,
            interaction_handler=mock_handler,
            script_output=mock_output,
        )

        assert success is True
        assert mock_output.write_line.call_count == 2
        mock_output.write_line.assert_any_call("line one")
        mock_output.write_line.assert_any_call("line two")

    def test_falls_back_to_logger_when_no_script_output(
        self, runner, mock_handler, temp_dir
    ):
        """Non-JSON lines go to logger when script_output is None."""
        script_path = os.path.join(temp_dir, "logger_test.py")
        with open(script_path, "w") as f:
            f.write('print("logged line")\n')

        with patch.object(runner.logger, "info") as mock_info:
            success = runner._run_interactive(
                cmd=["python", "logger_test.py"],
                cwd=temp_dir,
                env=None,
                shell=False,
                interaction_handler=mock_handler,
                script_output=None,
            )

        assert success is True
        mock_info.assert_any_call("logged line")

    def test_interactive_prompts_still_work_with_script_output(
        self, runner, mock_handler, mock_output, temp_dir
    ):
        """Interactive JSON prompts are handled normally even with script_output."""
        script_path = os.path.join(temp_dir, "interactive_with_output.py")
        with open(script_path, "w") as f:
            f.write(
                'import json, sys\n'
                'print("before prompt")\n'
                'prompt = {"_interactive": True, "type": "confirm", "id": "q1", "message": "Go?"}\n'
                'print(json.dumps(prompt), flush=True)\n'
                'response = json.loads(input())\n'
                'print("after prompt")\n'
            )

        mock_handler.handle_prompt.return_value = InteractionResponse(
            id="q1", value=True
        )

        success = runner._run_interactive(
            cmd=["python", "interactive_with_output.py"],
            cwd=temp_dir,
            env=None,
            shell=False,
            interaction_handler=mock_handler,
            script_output=mock_output,
        )

        assert success is True
        mock_handler.handle_prompt.assert_called_once()
        # Non-JSON lines should go to script_output
        mock_output.write_line.assert_any_call("before prompt")
        mock_output.write_line.assert_any_call("after prompt")

    def test_stderr_goes_to_script_output_when_provided(
        self, runner, mock_handler, mock_output, temp_dir
    ):
        """stderr lines go to script_output.write_line() when provided."""
        script_path = os.path.join(temp_dir, "stderr_test.py")
        with open(script_path, "w") as f:
            f.write(
                'import sys\n'
                'print("stderr line", file=sys.stderr, flush=True)\n'
                'print("stdout line", flush=True)\n'
            )

        success = runner._run_interactive(
            cmd=["python", "stderr_test.py"],
            cwd=temp_dir,
            env=None,
            shell=False,
            interaction_handler=mock_handler,
            script_output=mock_output,
        )

        assert success is True
        mock_output.write_line.assert_any_call("stderr line")
        mock_output.write_line.assert_any_call("stdout line")

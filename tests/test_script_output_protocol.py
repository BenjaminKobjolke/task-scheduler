"""Tests for ScriptOutput protocol and ConsoleScriptOutput implementation."""

import json
import os

import pytest
from unittest.mock import patch

from src.interaction import (
    InteractionRequest,
    InteractionResponse,
    InteractionType,
)
from src.script_runner import ScriptRunner


@pytest.fixture
def runner():
    """Create a ScriptRunner instance."""
    return ScriptRunner()


class TestInteractionRequestParseOutput:
    """Tests for InteractionRequest.parse() with output type."""

    def test_parse_output_message(self):
        """parse() returns OUTPUT type for valid output messages."""
        line = json.dumps({
            "_interactive": True,
            "type": "output",
            "id": "",
            "message": "Processing item 5",
        })
        result = InteractionRequest.parse(line)
        assert result is not None
        assert result.type == InteractionType.OUTPUT
        assert result.message == "Processing item 5"
        assert result.id == ""

    def test_parse_output_with_id(self):
        """parse() accepts output messages with a non-empty id too."""
        line = json.dumps({
            "_interactive": True,
            "type": "output",
            "id": "some-id",
            "message": "Status update",
        })
        result = InteractionRequest.parse(line)
        assert result is not None
        assert result.type == InteractionType.OUTPUT
        assert result.id == "some-id"

    def test_parse_output_empty_message_returns_request(self):
        """parse() returns a valid OUTPUT request for empty message (not None).

        Returning None would cause the raw JSON to fall through as plain text,
        leaking protocol messages to the user.
        """
        line = json.dumps({
            "_interactive": True,
            "type": "output",
            "id": "",
            "message": "",
        })
        result = InteractionRequest.parse(line)
        assert result is not None
        assert result.type == InteractionType.OUTPUT
        assert result.message == ""


class TestRunInteractiveOutputProtocol:
    """Tests for _run_interactive() handling output protocol messages."""

    def test_output_message_displayed_via_script_output(
        self, runner, mock_handler, mock_output, temp_dir
    ):
        """Output protocol messages are displayed via script_output without stdin response."""
        script_path = os.path.join(temp_dir, "output_protocol.py")
        with open(script_path, "w") as f:
            f.write(
                'import json\n'
                'msg = {"_interactive": True, "type": "output", "id": "", "message": "Step 1 done"}\n'
                'print(json.dumps(msg), flush=True)\n'
                'print("plain line", flush=True)\n'
            )

        success = runner._run_interactive(
            cmd=["python", "output_protocol.py"],
            cwd=temp_dir,
            env=None,
            shell=False,
            interaction_handler=mock_handler,
            script_output=mock_output,
        )

        assert success is True
        mock_output.write_line.assert_any_call("Step 1 done")
        mock_output.write_line.assert_any_call("plain line")
        # No interaction prompt should have been handled
        mock_handler.handle_prompt.assert_not_called()

    def test_output_message_logged_when_no_script_output(
        self, runner, mock_handler, temp_dir
    ):
        """Output protocol messages go to logger when script_output is None."""
        script_path = os.path.join(temp_dir, "output_logger.py")
        with open(script_path, "w") as f:
            f.write(
                'import json\n'
                'msg = {"_interactive": True, "type": "output", "id": "", "message": "Logged output"}\n'
                'print(json.dumps(msg), flush=True)\n'
            )

        with patch.object(runner.logger, "info") as mock_info:
            success = runner._run_interactive(
                cmd=["python", "output_logger.py"],
                cwd=temp_dir,
                env=None,
                shell=False,
                interaction_handler=mock_handler,
                script_output=None,
            )

        assert success is True
        mock_info.assert_any_call("Logged output")
        mock_handler.handle_prompt.assert_not_called()

    def test_empty_output_message_silently_consumed(
        self, runner, mock_handler, mock_output, temp_dir
    ):
        """Empty output protocol messages are consumed without forwarding to script_output."""
        script_path = os.path.join(temp_dir, "empty_output.py")
        with open(script_path, "w") as f:
            f.write(
                'import json\n'
                'msg = {"_interactive": True, "type": "output", "id": "", "message": ""}\n'
                'print(json.dumps(msg), flush=True)\n'
                'print("real line", flush=True)\n'
            )

        success = runner._run_interactive(
            cmd=["python", "empty_output.py"],
            cwd=temp_dir,
            env=None,
            shell=False,
            interaction_handler=mock_handler,
            script_output=mock_output,
        )

        assert success is True
        # Only "real line" should be forwarded, not the empty output or raw JSON
        assert mock_output.write_line.call_count == 1
        mock_output.write_line.assert_called_once_with("real line")

    def test_output_mixed_with_interactive_prompts(
        self, runner, mock_handler, mock_output, temp_dir
    ):
        """Output messages and interactive prompts can be mixed correctly."""
        script_path = os.path.join(temp_dir, "mixed_output.py")
        with open(script_path, "w") as f:
            f.write(
                'import json, sys\n'
                'out_msg = {"_interactive": True, "type": "output", "id": "", "message": "Starting..."}\n'
                'print(json.dumps(out_msg), flush=True)\n'
                'prompt = {"_interactive": True, "type": "confirm", "id": "q1", "message": "Continue?"}\n'
                'print(json.dumps(prompt), flush=True)\n'
                'response = json.loads(input())\n'
                'done_msg = {"_interactive": True, "type": "output", "id": "", "message": "Done!"}\n'
                'print(json.dumps(done_msg), flush=True)\n'
            )

        mock_handler.handle_prompt.return_value = InteractionResponse(
            id="q1", value=True
        )

        success = runner._run_interactive(
            cmd=["python", "mixed_output.py"],
            cwd=temp_dir,
            env=None,
            shell=False,
            interaction_handler=mock_handler,
            script_output=mock_output,
        )

        assert success is True
        mock_output.write_line.assert_any_call("Starting...")
        mock_output.write_line.assert_any_call("Done!")
        mock_handler.handle_prompt.assert_called_once()

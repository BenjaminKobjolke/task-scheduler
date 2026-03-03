"""Tests for interaction module — protocol types, parsing, and CLI handler."""

import json
from unittest.mock import patch


from src.interaction import (
    CliInteractionHandler,
    InteractionRequest,
    InteractionResponse,
    InteractionTimeoutError,
    InteractionType,
)


class TestInteractionType:
    """Tests for InteractionType enum."""

    def test_confirm_value(self):
        assert InteractionType.CONFIRM == "confirm"

    def test_input_value(self):
        assert InteractionType.INPUT == "input"

    def test_choice_value(self):
        assert InteractionType.CHOICE == "choice"


class TestInteractionRequestParse:
    """Tests for InteractionRequest.parse()."""

    def test_parse_confirm(self):
        line = json.dumps(
            {"_interactive": True, "type": "confirm", "id": "q1", "message": "Deploy?"}
        )
        req = InteractionRequest.parse(line)
        assert req is not None
        assert req.type == InteractionType.CONFIRM
        assert req.id == "q1"
        assert req.message == "Deploy?"
        assert req.default is None
        assert req.options is None

    def test_parse_input_with_default(self):
        line = json.dumps(
            {
                "_interactive": True,
                "type": "input",
                "id": "q2",
                "message": "Version:",
                "default": "1.0.0",
            }
        )
        req = InteractionRequest.parse(line)
        assert req is not None
        assert req.type == InteractionType.INPUT
        assert req.default == "1.0.0"

    def test_parse_choice_with_options(self):
        line = json.dumps(
            {
                "_interactive": True,
                "type": "choice",
                "id": "q3",
                "message": "Select env:",
                "options": ["staging", "production"],
                "default": 0,
            }
        )
        req = InteractionRequest.parse(line)
        assert req is not None
        assert req.type == InteractionType.CHOICE
        assert req.options == ["staging", "production"]
        assert req.default == 0

    def test_parse_non_interactive_line(self):
        line = "Just a regular log line"
        req = InteractionRequest.parse(line)
        assert req is None

    def test_parse_json_without_marker(self):
        line = json.dumps({"type": "confirm", "id": "q1", "message": "Deploy?"})
        req = InteractionRequest.parse(line)
        assert req is None

    def test_parse_interactive_false(self):
        line = json.dumps(
            {"_interactive": False, "type": "confirm", "id": "q1", "message": "Deploy?"}
        )
        req = InteractionRequest.parse(line)
        assert req is None

    def test_parse_missing_required_field(self):
        line = json.dumps({"_interactive": True, "type": "confirm", "id": "q1"})
        req = InteractionRequest.parse(line)
        assert req is None

    def test_parse_invalid_json(self):
        line = "{not valid json"
        req = InteractionRequest.parse(line)
        assert req is None

    def test_parse_empty_string(self):
        req = InteractionRequest.parse("")
        assert req is None

    def test_parse_invalid_type(self):
        line = json.dumps(
            {"_interactive": True, "type": "unknown", "id": "q1", "message": "?"}
        )
        req = InteractionRequest.parse(line)
        assert req is None


class TestInteractionResponse:
    """Tests for InteractionResponse."""

    def test_to_json_line_simple(self):
        resp = InteractionResponse(id="q1", value=True)
        result = json.loads(resp.to_json_line())
        assert result == {"id": "q1", "value": True}

    def test_to_json_line_with_timed_out(self):
        resp = InteractionResponse(id="q1", value=True, timed_out=True)
        result = json.loads(resp.to_json_line())
        assert result == {"id": "q1", "value": True, "timed_out": True}

    def test_to_json_line_with_error(self):
        resp = InteractionResponse(id="q1", value=None, error="Timeout: no response")
        result = json.loads(resp.to_json_line())
        assert result == {"id": "q1", "value": None, "error": "Timeout: no response"}

    def test_to_json_line_no_optional_fields(self):
        resp = InteractionResponse(id="q1", value="hello")
        result = json.loads(resp.to_json_line())
        assert "timed_out" not in result
        assert "error" not in result


class TestCliInteractionHandler:
    """Tests for CliInteractionHandler."""

    def test_confirm_yes(self):
        handler = CliInteractionHandler()
        req = InteractionRequest(
            type=InteractionType.CONFIRM, id="q1", message="Deploy?"
        )
        with patch("builtins.input", return_value="y"):
            resp = handler.handle_prompt(req)
        assert resp.id == "q1"
        assert resp.value is True

    def test_confirm_no(self):
        handler = CliInteractionHandler()
        req = InteractionRequest(
            type=InteractionType.CONFIRM, id="q1", message="Deploy?"
        )
        with patch("builtins.input", return_value="n"):
            resp = handler.handle_prompt(req)
        assert resp.value is False

    def test_confirm_default_on_empty(self):
        handler = CliInteractionHandler()
        req = InteractionRequest(
            type=InteractionType.CONFIRM, id="q1", message="Deploy?", default=True
        )
        with patch("builtins.input", return_value=""):
            resp = handler.handle_prompt(req)
        assert resp.value is True

    def test_input_text(self):
        handler = CliInteractionHandler()
        req = InteractionRequest(
            type=InteractionType.INPUT, id="q2", message="Version:"
        )
        with patch("builtins.input", return_value="2.0.0"):
            resp = handler.handle_prompt(req)
        assert resp.value == "2.0.0"

    def test_input_default_on_empty(self):
        handler = CliInteractionHandler()
        req = InteractionRequest(
            type=InteractionType.INPUT,
            id="q2",
            message="Version:",
            default="1.0.0",
        )
        with patch("builtins.input", return_value=""):
            resp = handler.handle_prompt(req)
        assert resp.value == "1.0.0"

    def test_choice_valid_index(self):
        handler = CliInteractionHandler()
        req = InteractionRequest(
            type=InteractionType.CHOICE,
            id="q3",
            message="Select env:",
            options=["staging", "production"],
        )
        with patch("builtins.input", return_value="2"):
            resp = handler.handle_prompt(req)
        assert resp.value == 1  # 0-based index

    def test_choice_default_on_empty(self):
        handler = CliInteractionHandler()
        req = InteractionRequest(
            type=InteractionType.CHOICE,
            id="q3",
            message="Select env:",
            options=["staging", "production"],
            default=0,
        )
        with patch("builtins.input", return_value=""):
            resp = handler.handle_prompt(req)
        assert resp.value == 0


class TestInteractionTimeoutError:
    """Tests for InteractionTimeoutError."""

    def test_is_exception(self):
        err = InteractionTimeoutError("q1")
        assert isinstance(err, Exception)
        assert "q1" in str(err)

"""Interactive script communication protocol — types, parsing, and handlers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

from .constants import Interactive


class InteractionType(str, Enum):
    """Types of interactive prompts a script can send."""

    CONFIRM = "confirm"
    INPUT = "input"
    CHOICE = "choice"


_VALID_TYPES = {t.value for t in InteractionType}


@dataclass
class InteractionRequest:
    """A prompt sent from a script to the scheduler via stdout JSON."""

    type: InteractionType
    id: str
    message: str
    default: Any | None = None
    options: list[str] | None = None

    @staticmethod
    def parse(line: str) -> InteractionRequest | None:
        """Parse a stdout line into an InteractionRequest.

        Returns None if the line is not a valid interactive protocol message.
        """
        if not line.strip():
            return None
        try:
            data = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            return None

        if not isinstance(data, dict):
            return None
        if data.get(Interactive.MARKER_FIELD) is not True:
            return None

        raw_type = data.get("type")
        msg_id = data.get("id")
        message = data.get("message")

        if not raw_type or not msg_id or not message:
            return None
        if raw_type not in _VALID_TYPES:
            return None

        return InteractionRequest(
            type=InteractionType(raw_type),
            id=msg_id,
            message=message,
            default=data.get("default"),
            options=data.get("options"),
        )


@dataclass
class InteractionResponse:
    """A response sent from the scheduler back to the script via stdin JSON."""

    id: str
    value: Any
    timed_out: bool = False
    error: str | None = None

    def to_json_line(self) -> str:
        """Serialize to a single JSON line for writing to stdin."""
        result: dict[str, Any] = {"id": self.id, "value": self.value}
        if self.timed_out:
            result["timed_out"] = True
        if self.error is not None:
            result["error"] = self.error
        return json.dumps(result)


class InteractionHandler(Protocol):
    """Protocol for handling interactive prompts from scripts."""

    def handle_prompt(self, request: InteractionRequest) -> InteractionResponse: ...


class InteractionTimeoutError(Exception):
    """Raised when no response is received and no default is available."""

    def __init__(self, prompt_id: str) -> None:
        super().__init__(f"Timeout: no response and no default value for prompt '{prompt_id}'")
        self.prompt_id = prompt_id


class CliInteractionHandler:
    """Interactive handler for terminal/CLI use — reads from stdin."""

    def handle_prompt(self, request: InteractionRequest) -> InteractionResponse:
        """Display a prompt in the terminal and collect user response."""
        if request.type == InteractionType.CONFIRM:
            return self._handle_confirm(request)
        if request.type == InteractionType.INPUT:
            return self._handle_input(request)
        if request.type == InteractionType.CHOICE:
            return self._handle_choice(request)
        raise ValueError(f"Unknown interaction type: {request.type}")

    def _handle_confirm(self, request: InteractionRequest) -> InteractionResponse:
        default_hint = ""
        if request.default is True:
            default_hint = " [Y/n]"
        elif request.default is False:
            default_hint = " [y/N]"
        else:
            default_hint = " [y/n]"

        reply = input(f"{request.message}{default_hint}: ").strip().lower()

        if not reply and request.default is not None:
            return InteractionResponse(id=request.id, value=request.default)

        return InteractionResponse(id=request.id, value=reply in ("y", "yes"))

    def _handle_input(self, request: InteractionRequest) -> InteractionResponse:
        default_hint = f" [{request.default}]" if request.default is not None else ""
        reply = input(f"{request.message}{default_hint}: ").strip()

        if not reply and request.default is not None:
            return InteractionResponse(id=request.id, value=request.default)

        return InteractionResponse(id=request.id, value=reply)

    def _handle_choice(self, request: InteractionRequest) -> InteractionResponse:
        options = request.options or []
        print(request.message)
        for i, option in enumerate(options):
            default_marker = " (default)" if request.default == i else ""
            print(f"  {i + 1}. {option}{default_marker}")

        reply = input("Enter number: ").strip()

        if not reply and request.default is not None:
            return InteractionResponse(id=request.id, value=request.default)

        try:
            idx = int(reply) - 1
            if 0 <= idx < len(options):
                return InteractionResponse(id=request.id, value=idx)
        except ValueError:
            pass

        # Invalid input — fall back to default or 0
        if request.default is not None:
            return InteractionResponse(id=request.id, value=request.default)
        return InteractionResponse(id=request.id, value=0)

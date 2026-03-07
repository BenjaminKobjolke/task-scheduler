"""Bot interaction handler — relays interactive prompts via chat."""

from __future__ import annotations

import threading
from collections.abc import Callable

from src.interaction import InteractionRequest, InteractionResponse, InteractionType


class BotScriptOutput:
    """Sends script output lines to the chat user."""

    def __init__(self, user_id: str, notifier: Callable[[str, str], None]) -> None:
        self._user_id = user_id
        self._notifier = notifier

    def write_line(self, line: str) -> None:
        self._notifier(self._user_id, line)


class BotInteractionHandler:
    """Handles interactive prompts by sending them to a chat user and waiting for replies."""

    def __init__(
        self,
        user_id: str,
        notifier: Callable[[str, str], None],
        timeout: int | float,
    ) -> None:
        self._user_id = user_id
        self._notifier = notifier
        self._timeout = timeout
        self._pending_event: threading.Event = threading.Event()
        self._pending_response: str | None = None
        self._lock = threading.Lock()
        self._cancelled: bool = False

    def cancel(self) -> None:
        """Cancel the interaction, unblocking any waiting handle_prompt."""
        self._cancelled = True
        self._pending_event.set()

    def handle_prompt(self, request: InteractionRequest) -> InteractionResponse:
        """Send prompt to user via chat, wait for reply, return parsed response."""
        if self._cancelled:
            return InteractionResponse(
                id=request.id, value=None, error="Cancelled by user"
            )

        text = self._format_for_chat(request)
        self._notifier(self._user_id, text)

        with self._lock:
            self._pending_event = threading.Event()
            self._pending_response = None

        got_reply = self._pending_event.wait(timeout=self._timeout)

        if self._cancelled:
            return InteractionResponse(
                id=request.id, value=None, error="Cancelled by user"
            )

        if got_reply and self._pending_response is not None:
            return self._parse_user_reply(request, self._pending_response)
        elif request.default is not None:
            return InteractionResponse(
                id=request.id, value=request.default, timed_out=True
            )
        else:
            return InteractionResponse(
                id=request.id,
                value=None,
                error="Timeout: no response and no default value",
            )

    def resolve(self, text: str) -> None:
        """Called by command processor when user sends a reply."""
        with self._lock:
            self._pending_response = text
            self._pending_event.set()

    def _format_for_chat(self, request: InteractionRequest) -> str:
        """Format a prompt for chat display."""
        if request.type == InteractionType.CONFIRM:
            default_hint = ""
            if request.default is True:
                default_hint = " (default: yes)"
            elif request.default is False:
                default_hint = " (default: no)"
            return f"{request.message}{default_hint}\nReply 'yes' or 'no'."

        if request.type == InteractionType.INPUT:
            default_hint = ""
            if request.default is not None:
                default_hint = f" (default: {request.default})"
            return f"{request.message}{default_hint}"

        if request.type == InteractionType.CHOICE:
            lines = [request.message]
            for i, option in enumerate(request.options or []):
                default_marker = " (default)" if request.default == i else ""
                lines.append(f"  {i + 1}. {option}{default_marker}")
            lines.append("Reply with the number of your choice.")
            return "\n".join(lines)

        return request.message

    def _parse_user_reply(
        self, request: InteractionRequest, reply: str
    ) -> InteractionResponse:
        """Parse a user's text reply into a typed response."""
        reply = reply.strip()

        if request.type == InteractionType.CONFIRM:
            value = reply.lower() in ("y", "yes", "true", "1")
            return InteractionResponse(id=request.id, value=value)

        if request.type == InteractionType.INPUT:
            return InteractionResponse(id=request.id, value=reply)

        if request.type == InteractionType.CHOICE:
            try:
                idx = int(reply) - 1
                options = request.options or []
                if 0 <= idx < len(options):
                    return InteractionResponse(id=request.id, value=idx)
            except ValueError:
                pass
            # Fall back to default or 0
            if request.default is not None:
                return InteractionResponse(id=request.id, value=request.default)
            return InteractionResponse(id=request.id, value=0)

        return InteractionResponse(id=request.id, value=reply)

"""Bot conversation flow state machines."""

from typing import Optional

from bot_commander import BotResponse, CONFIRMED_SENTINEL, ConversationState

from .constants import Messages


class DeleteConfirmation:
    """Simple yes/no confirmation for deleting a task."""

    @staticmethod
    def start(task_id: int, task_name: str) -> tuple[ConversationState, BotResponse]:
        """Start a delete confirmation flow."""
        state = ConversationState(
            kind="confirm_delete",
            data={"task_id": task_id, "task_name": task_name},
        )
        text = Messages.CONFIRM_DELETE.format(task_name, task_id)
        return state, BotResponse(text=text)

    @staticmethod
    def handle_response(
        state: ConversationState, user_input: str
    ) -> tuple[Optional[ConversationState], BotResponse]:
        """Handle the user's yes/no response.

        Returns (None, empty BotResponse) on 'yes' so the caller can perform
        the actual deletion. Returns cancel message otherwise.
        """
        if user_input.strip().lower() in ("yes", "y"):
            return None, BotResponse(text=CONFIRMED_SENTINEL)
        return None, BotResponse(text=Messages.DELETE_CANCELLED)


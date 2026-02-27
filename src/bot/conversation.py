"""Conversation state machines for bot wizards and confirmations."""

import shlex
from typing import Optional

from bot_commander import (
    BotResponse,
    CONFIRMED_SENTINEL,
    ConversationState,
    is_skip,
    is_valid_time,
)

from .constants import Messages
from .formatters import format_add_summary, format_edit_changes


class AddWizard:
    """Stateless wizard for adding a task step-by-step.

    Steps:
        0 - script_path (prefix with 'uv:' for uv command)
        1 - uv command name (only for uv_command type)
        2 - task name
        3 - interval in minutes
        4 - start time (HH:MM or skip)
        5 - arguments (space-separated or skip)
        6 - confirmation (yes / anything else)
    """

    @staticmethod
    def start() -> tuple[ConversationState, BotResponse]:
        """Start the add wizard. Returns initial state and first prompt."""
        state = ConversationState(kind="add_wizard", step=0)
        return state, BotResponse(text=Messages.WIZARD_ADD_START)

    @staticmethod
    def advance(
        state: ConversationState, user_input: str
    ) -> tuple[Optional[ConversationState], BotResponse]:
        """Advance one step. Returns (new_state, response).

        new_state is None when the wizard completes or is cancelled.
        """
        step = state.step
        text = user_input.strip()

        if step == 0:
            return _add_step_script_path(state, text)
        if step == 1:
            return _add_step_command(state, text)
        if step == 2:
            return _add_step_name(state, text)
        if step == 3:
            return _add_step_interval(state, text)
        if step == 4:
            return _add_step_start_time(state, text)
        if step == 5:
            return _add_step_arguments(state, text)
        if step == 6:
            return _add_step_confirm(state, text)

        return None, BotResponse(text=Messages.OPERATION_CANCELLED)


class EditWizard:
    """Stateless wizard for editing an existing task step-by-step.

    Steps:
        0 - script_path
        1 - command (only for uv_command type)
        2 - task name
        3 - interval in minutes
        4 - start time
        5 - arguments
        6 - confirmation
    """

    @staticmethod
    def start(task: dict) -> tuple[ConversationState, BotResponse]:
        """Start the edit wizard for *task*. Returns initial state and prompt."""
        from .formatters import format_task_detail

        state = ConversationState(
            kind="edit_wizard",
            step=0,
            data={"original": task, "changes": {}},
        )
        detail = format_task_detail(task)
        intro = Messages.WIZARD_EDIT_START.format(task["name"], task["id"], detail)
        first_prompt = Messages.WIZARD_EDIT_SCRIPT.format(
            task.get("script_path", "")
        )
        return state, BotResponse(text=f"{intro}\n\n{first_prompt}")

    @staticmethod
    def advance(
        state: ConversationState, user_input: str
    ) -> tuple[Optional[ConversationState], BotResponse]:
        """Advance one step. Returns (new_state, response).

        new_state is None when the wizard completes or is cancelled.
        """
        step = state.step
        text = user_input.strip()

        if step == 0:
            return _edit_step_script_path(state, text)
        if step == 1:
            return _edit_step_command(state, text)
        if step == 2:
            return _edit_step_name(state, text)
        if step == 3:
            return _edit_step_interval(state, text)
        if step == 4:
            return _edit_step_start_time(state, text)
        if step == 5:
            return _edit_step_arguments(state, text)
        if step == 6:
            return _edit_step_confirm(state, text)

        return None, BotResponse(text=Messages.OPERATION_CANCELLED)


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


# ---------------------------------------------------------------------------
# AddWizard step handlers (private)
# ---------------------------------------------------------------------------

_UV_PREFIX = "uv:"


def _add_step_script_path(
    state: ConversationState, text: str
) -> tuple[ConversationState, BotResponse]:
    if text.startswith(_UV_PREFIX):
        state.data["task_type"] = "uv_command"
        state.data["script_path"] = text[len(_UV_PREFIX) :].strip()
        state.step = 1
        return state, BotResponse(text=Messages.WIZARD_ADD_COMMAND)

    state.data["task_type"] = "script"
    state.data["script_path"] = text
    state.step = 2
    return state, BotResponse(text=Messages.WIZARD_ADD_NAME)


def _add_step_command(
    state: ConversationState, text: str
) -> tuple[ConversationState, BotResponse]:
    state.data["command"] = text
    state.step = 2
    return state, BotResponse(text=Messages.WIZARD_ADD_NAME)


def _add_step_name(
    state: ConversationState, text: str
) -> tuple[ConversationState, BotResponse]:
    state.data["name"] = text
    state.step = 3
    return state, BotResponse(text=Messages.WIZARD_ADD_INTERVAL)


def _add_step_interval(
    state: ConversationState, text: str
) -> tuple[ConversationState, BotResponse]:
    try:
        interval = int(text)
        if interval < 0:
            return state, BotResponse(text=Messages.WIZARD_INVALID_INTERVAL)
        state.data["interval"] = interval
        if interval == 0:
            # Manual-only: skip start_time, go straight to arguments
            state.data["start_time"] = None
            state.step = 5
            return state, BotResponse(text=Messages.WIZARD_ADD_ARGUMENTS)
        state.step = 4
        return state, BotResponse(text=Messages.WIZARD_ADD_START_TIME)
    except ValueError:
        return state, BotResponse(text=Messages.WIZARD_INVALID_INTERVAL)


def _add_step_start_time(
    state: ConversationState, text: str
) -> tuple[ConversationState, BotResponse]:
    if is_skip(text):
        state.data["start_time"] = None
    else:
        if not is_valid_time(text):
            return state, BotResponse(text=Messages.WIZARD_INVALID_TIME)
        state.data["start_time"] = text
    state.step = 5
    return state, BotResponse(text=Messages.WIZARD_ADD_ARGUMENTS)


def _add_step_arguments(
    state: ConversationState, text: str
) -> tuple[ConversationState, BotResponse]:
    if is_skip(text):
        state.data["arguments"] = None
    else:
        state.data["arguments"] = shlex.split(text)
    state.step = 6
    summary = format_add_summary(state.data)
    return state, BotResponse(text=Messages.WIZARD_ADD_CONFIRM.format(summary))


def _add_step_confirm(
    state: ConversationState, text: str
) -> tuple[Optional[ConversationState], BotResponse]:
    if text.lower() in ("yes", "y"):
        return None, BotResponse(text=CONFIRMED_SENTINEL)
    return None, BotResponse(text=Messages.OPERATION_CANCELLED)


# ---------------------------------------------------------------------------
# EditWizard step handlers (private)
# ---------------------------------------------------------------------------


def _edit_step_script_path(
    state: ConversationState, text: str
) -> tuple[ConversationState, BotResponse]:
    original = state.data["original"]
    if not is_skip(text):
        state.data["changes"]["script_path"] = text

    task_type = original.get("task_type", "script")
    if task_type == "uv_command":
        state.step = 1
        return state, BotResponse(
            text=Messages.WIZARD_EDIT_COMMAND.format(original.get("command", ""))
        )

    state.step = 2
    return state, BotResponse(text=Messages.WIZARD_EDIT_NAME.format(original["name"]))


def _edit_step_command(
    state: ConversationState, text: str
) -> tuple[ConversationState, BotResponse]:
    original = state.data["original"]
    if not is_skip(text):
        state.data["changes"]["command"] = text
    state.step = 2
    return state, BotResponse(text=Messages.WIZARD_EDIT_NAME.format(original["name"]))


def _edit_step_name(
    state: ConversationState, text: str
) -> tuple[ConversationState, BotResponse]:
    original = state.data["original"]
    if not is_skip(text):
        state.data["changes"]["name"] = text
    state.step = 3
    return state, BotResponse(
        text=Messages.WIZARD_EDIT_INTERVAL.format(original["interval"])
    )


def _edit_step_interval(
    state: ConversationState, text: str
) -> tuple[ConversationState, BotResponse]:
    original = state.data["original"]
    if is_skip(text):
        # Check effective interval (changed or original) for start_time skip
        effective_interval = state.data["changes"].get("interval", original["interval"])
        if effective_interval == 0:
            state.step = 5
            args = original.get("arguments", [])
            args_display = " ".join(args) if args else ""
            return state, BotResponse(text=Messages.WIZARD_EDIT_ARGUMENTS.format(args_display))
        state.step = 4
        return state, BotResponse(
            text=Messages.WIZARD_EDIT_START_TIME.format(original.get("start_time", ""))
        )

    try:
        interval = int(text)
        if interval < 0:
            return state, BotResponse(text=Messages.WIZARD_INVALID_INTERVAL)
        state.data["changes"]["interval"] = interval
        if interval == 0:
            # Manual-only: clear start_time and skip to arguments
            state.data["changes"]["start_time"] = None
            state.step = 5
            args = original.get("arguments", [])
            args_display = " ".join(args) if args else ""
            return state, BotResponse(text=Messages.WIZARD_EDIT_ARGUMENTS.format(args_display))
        state.step = 4
        return state, BotResponse(
            text=Messages.WIZARD_EDIT_START_TIME.format(original.get("start_time", ""))
        )
    except ValueError:
        return state, BotResponse(text=Messages.WIZARD_INVALID_INTERVAL)


def _edit_step_start_time(
    state: ConversationState, text: str
) -> tuple[ConversationState, BotResponse]:
    original = state.data["original"]
    if text.lower() in ("skip", "s"):
        pass  # no change
    elif text.lower() in ("none", ""):
        state.data["changes"]["start_time"] = None
    else:
        if not is_valid_time(text):
            return state, BotResponse(text=Messages.WIZARD_INVALID_TIME)
        state.data["changes"]["start_time"] = text

    state.step = 5
    args = original.get("arguments", [])
    args_display = " ".join(args) if args else ""
    return state, BotResponse(text=Messages.WIZARD_EDIT_ARGUMENTS.format(args_display))


def _edit_step_arguments(
    state: ConversationState, text: str
) -> tuple[ConversationState, BotResponse]:
    original = state.data["original"]
    changes = state.data["changes"]

    if text.lower() in ("skip", "s"):
        pass  # no change
    elif text.lower() in ("none", ""):
        changes["arguments"] = None
    else:
        changes["arguments"] = shlex.split(text)

    state.step = 6
    if not changes:
        return state, BotResponse(text=Messages.WIZARD_EDIT_NO_CHANGES)

    diff = format_edit_changes(original, changes)
    return state, BotResponse(text=Messages.WIZARD_EDIT_CONFIRM.format(diff))


def _edit_step_confirm(
    state: ConversationState, text: str
) -> tuple[Optional[ConversationState], BotResponse]:
    if text.lower() in ("yes", "y"):
        return None, BotResponse(text=CONFIRMED_SENTINEL)
    return None, BotResponse(text=Messages.OPERATION_CANCELLED)

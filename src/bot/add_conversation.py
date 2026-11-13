"""Bot conversation flow state machines."""

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
from .formatters import format_add_summary


class AddWizard:
    """Stateless wizard for adding a task step-by-step.

    Steps:
        0 - script_path (prefix with 'uv:' for uv command)
        1 - uv command name (only for uv_command type)
        2 - task name
        3 - interval in minutes
        4 - start time (HH:MM or skip)
        5 - launch_new_process (only when interval == 0)
        6 - arguments (space-separated or skip)
        7 - confirmation (yes / anything else)
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
            return _add_step_launch_new_process(state, text)
        if step == 6:
            return _add_step_arguments(state, text)
        if step == 7:
            return _add_step_confirm(state, text)

        return None, BotResponse(text=Messages.OPERATION_CANCELLED)


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
            # Manual-only: skip start_time, go to launch_new_process
            state.data["start_time"] = None
            state.step = 5
            return state, BotResponse(text=Messages.WIZARD_ADD_LAUNCH_NEW_PROCESS)
        state.data["launch_new_process"] = False
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
    state.step = 6
    return state, BotResponse(text=Messages.WIZARD_ADD_ARGUMENTS)
def _add_step_launch_new_process(
    state: ConversationState, text: str
) -> tuple[ConversationState, BotResponse]:
    if text.lower() in ("yes", "y"):
        state.data["launch_new_process"] = True
    else:
        state.data["launch_new_process"] = False
    state.step = 6
    return state, BotResponse(text=Messages.WIZARD_ADD_ARGUMENTS)
def _add_step_arguments(
    state: ConversationState, text: str
) -> tuple[ConversationState, BotResponse]:
    if is_skip(text):
        state.data["arguments"] = None
    else:
        state.data["arguments"] = shlex.split(text)
    state.step = 7
    summary = format_add_summary(state.data)
    return state, BotResponse(text=Messages.WIZARD_ADD_CONFIRM.format(summary))
def _add_step_confirm(
    state: ConversationState, text: str
) -> tuple[Optional[ConversationState], BotResponse]:
    if text.lower() in ("yes", "y"):
        return None, BotResponse(text=CONFIRMED_SENTINEL)
    return None, BotResponse(text=Messages.OPERATION_CANCELLED)

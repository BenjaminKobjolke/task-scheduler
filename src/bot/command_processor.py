"""Bot command processor - handles all bot commands."""
from typing import Dict

from .types import BotMessage, BotResponse, BotConfig
from .constants import Commands, Messages
from .formatters import (
    format_task_list_compact,
    format_execution_history_compact,
)
from .conversation import (
    ConversationState,
    AddWizard,
    EditWizard,
    DeleteConfirmation,
)
from src.scheduler import TaskScheduler
from src.logger import Logger


class CommandProcessor:
    """Processes bot commands. Pure synchronous, no bot dependencies."""

    def __init__(self, scheduler: TaskScheduler, bot_config: BotConfig) -> None:
        self._scheduler = scheduler
        self._bot_config = bot_config
        self._conversations: Dict[str, ConversationState] = {}
        self._logger = Logger("CommandProcessor")
        self._command_map: Dict[str, object] = {
            Commands.LIST: self._cmd_list,
            Commands.RUN: self._cmd_run,
            Commands.HISTORY: self._cmd_history,
            Commands.ADD: self._cmd_add,
            Commands.EDIT: self._cmd_edit,
            Commands.DELETE: self._cmd_delete,
            Commands.HELP: self._cmd_help,
            Commands.CANCEL: self._cmd_cancel,
        }

    def process(self, message: BotMessage) -> BotResponse:
        """Process an incoming message and return a response."""
        user_id = message.user_id

        # Clean up expired conversations
        self._cleanup_expired(user_id)

        # Check for active conversation first
        if user_id in self._conversations:
            if message.text.strip().lower() == Commands.CANCEL:
                return self._cmd_cancel(user_id, "")
            return self._continue_conversation(user_id, message.text)

        # Parse command
        parts = message.text.strip().split(maxsplit=1)
        command = parts[0].lower() if parts else ""
        args = parts[1].strip() if len(parts) > 1 else ""

        handler = self._command_map.get(command)
        if handler is None:
            return BotResponse(text=Messages.UNKNOWN_COMMAND)

        # Check if command is allowed
        if not self._is_command_allowed(command):
            return BotResponse(text=Messages.COMMAND_DISABLED.format(command))

        return handler(user_id, args)

    def _is_command_allowed(self, command: str) -> bool:
        """Check if a command is allowed by config."""
        if command == Commands.ADD:
            return self._bot_config.allow_add
        elif command == Commands.EDIT:
            return self._bot_config.allow_edit
        elif command == Commands.DELETE:
            return self._bot_config.allow_delete
        return True  # All other commands always allowed

    def _cleanup_expired(self, user_id: str) -> None:
        """Remove expired conversation for a user."""
        if user_id in self._conversations and self._conversations[user_id].is_expired():
            del self._conversations[user_id]

    def _continue_conversation(self, user_id: str, text: str) -> BotResponse:
        """Continue an active conversation (wizard or confirmation)."""
        state = self._conversations[user_id]

        if state.kind == "add_wizard":
            new_state, response = AddWizard.advance(state, text)
            if new_state is None:
                del self._conversations[user_id]
                if response.text == "":
                    # Wizard completed with "yes" - create the task
                    return self._execute_add(state.data)
                return response
            self._conversations[user_id] = new_state
            return response

        elif state.kind == "edit_wizard":
            new_state, response = EditWizard.advance(state, text)
            if new_state is None:
                del self._conversations[user_id]
                if response.text == "":
                    # Wizard completed with "yes" - apply edit
                    return self._execute_edit(state.data)
                return response
            self._conversations[user_id] = new_state
            return response

        elif state.kind == "confirm_delete":
            new_state, response = DeleteConfirmation.handle_response(state, text)
            del self._conversations[user_id]
            if response.text == "":
                # Confirmed - execute delete
                return self._execute_delete(
                    state.data["task_id"], state.data["task_name"]
                )
            return response

        # Unknown conversation kind
        del self._conversations[user_id]
        return BotResponse(text=Messages.UNKNOWN_COMMAND)

    def _cmd_help(self, user_id: str, args: str) -> BotResponse:
        """Handle the /help command."""
        return BotResponse(text=Messages.HELP)

    def _cmd_list(self, user_id: str, args: str) -> BotResponse:
        """Handle the /list command with optional filter."""
        tasks = self._scheduler.list_tasks()
        if args:
            filter_lower = args.lower()
            tasks = [t for t in tasks if filter_lower in t["name"].lower()]
        return BotResponse(text=format_task_list_compact(tasks))

    def _cmd_run(self, user_id: str, args: str) -> BotResponse:
        """Handle the /run command."""
        try:
            task_id = int(args.strip())
        except (ValueError, AttributeError):
            return BotResponse(text=Messages.INVALID_TASK_ID.format(Commands.RUN))

        try:
            # Get task name for response message
            tasks = self._scheduler.list_tasks()
            task = next((t for t in tasks if t["id"] == task_id), None)
            task_name = task["name"] if task else f"Task {task_id}"

            success = self._scheduler.run_task(task_id)
            if success:
                return BotResponse(
                    text=Messages.TASK_EXECUTED_SUCCESS.format(task_name, task_id)
                )
            else:
                return BotResponse(
                    text=Messages.TASK_EXECUTED_FAILURE.format(task_name, task_id)
                )
        except ValueError as e:
            return BotResponse(text=str(e))
        except Exception as e:
            return BotResponse(
                text=Messages.TASK_EXECUTION_ERROR.format(task_id, str(e))
            )

    def _cmd_history(self, user_id: str, args: str) -> BotResponse:
        """Handle the /history command."""
        try:
            limit = int(args.strip()) if args.strip() else 10
        except ValueError:
            limit = 10
        executions = self._scheduler.db.get_recent_executions(limit)
        return BotResponse(text=format_execution_history_compact(executions))

    def _cmd_add(self, user_id: str, args: str) -> BotResponse:
        """Handle the /add command - starts the add wizard."""
        state, response = AddWizard.start()
        self._conversations[user_id] = state
        return response

    def _cmd_edit(self, user_id: str, args: str) -> BotResponse:
        """Handle the /edit command - starts the edit wizard."""
        try:
            task_id = int(args.strip())
        except (ValueError, AttributeError):
            return BotResponse(text=Messages.INVALID_TASK_ID.format(Commands.EDIT))

        tasks = self._scheduler.list_tasks()
        task = next((t for t in tasks if t["id"] == task_id), None)
        if not task:
            return BotResponse(text=Messages.TASK_NOT_FOUND.format(task_id))

        state, response = EditWizard.start(task)
        self._conversations[user_id] = state
        return response

    def _cmd_delete(self, user_id: str, args: str) -> BotResponse:
        """Handle the /delete command - starts delete confirmation."""
        try:
            task_id = int(args.strip())
        except (ValueError, AttributeError):
            return BotResponse(text=Messages.INVALID_TASK_ID.format(Commands.DELETE))

        tasks = self._scheduler.list_tasks()
        task = next((t for t in tasks if t["id"] == task_id), None)
        if not task:
            return BotResponse(text=Messages.TASK_NOT_FOUND.format(task_id))

        state, response = DeleteConfirmation.start(task_id, task["name"])
        self._conversations[user_id] = state
        return response

    def _cmd_cancel(self, user_id: str, args: str) -> BotResponse:
        """Handle the /cancel command - clears active conversation."""
        if user_id in self._conversations:
            del self._conversations[user_id]
        return BotResponse(text=Messages.OPERATION_CANCELLED)

    def _execute_add(self, data: dict) -> BotResponse:
        """Execute task addition from wizard data."""
        try:
            task_id = self._scheduler.add_task(
                name=data["name"],
                script_path=data["script_path"],
                interval=data["interval"],
                arguments=data.get("arguments"),
                task_type=data.get("task_type", "script"),
                command=data.get("command"),
                start_time=data.get("start_time"),
            )
            return BotResponse(
                text=Messages.WIZARD_ADD_SUCCESS.format(data["name"], task_id)
            )
        except Exception as e:
            return BotResponse(text=f"Error adding task: {e}")

    def _execute_edit(self, data: dict) -> BotResponse:
        """Execute task edit from wizard data."""
        try:
            original = data["original"]
            task_id = original["id"]
            changes = data.get("changes", {})

            # Merge changes with original values
            self._scheduler.edit_task(
                task_id=task_id,
                name=changes.get("name", original["name"]),
                script_path=changes.get("script_path", original["script_path"]),
                interval=changes.get("interval", original["interval"]),
                arguments=changes.get("arguments", original.get("arguments")),
                task_type=original.get("task_type", "script"),
                command=changes.get("command", original.get("command")),
                start_time=changes.get("start_time", original.get("start_time")),
            )
            return BotResponse(
                text=Messages.WIZARD_EDIT_SUCCESS.format(
                    changes.get("name", original["name"]), task_id
                )
            )
        except Exception as e:
            return BotResponse(text=f"Error editing task: {e}")

    def _execute_delete(self, task_id: int, task_name: str) -> BotResponse:
        """Execute task deletion."""
        try:
            self._scheduler.remove_task(task_id)
            return BotResponse(
                text=Messages.TASK_DELETED.format(task_name, task_id)
            )
        except Exception as e:
            return BotResponse(text=f"Error deleting task: {e}")

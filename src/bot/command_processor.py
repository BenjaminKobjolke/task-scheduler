"""Task-scheduler command processor - subclasses bot_commander.Commander."""

from dataclasses import dataclass

from bot_commander import BotResponse, Commander

from .constants import Commands, Messages
from .conversation import AddWizard, DeleteConfirmation, EditWizard
from .formatters import format_execution_history_compact, format_task_list_compact
from src.logger import Logger
from src.scheduler import TaskScheduler


@dataclass(frozen=True)
class BotConfig:
    """Bot permission configuration."""

    allow_add: bool
    allow_edit: bool
    allow_delete: bool


class TaskCommandProcessor(Commander):
    """Task-scheduler specific command processor."""

    def __init__(self, scheduler: TaskScheduler, bot_config: BotConfig) -> None:
        super().__init__(
            unknown_command_text=Messages.UNKNOWN_COMMAND,
            command_disabled_text=Messages.COMMAND_DISABLED,
            expired_text=Messages.CONVERSATION_EXPIRED,
            cancelled_text=Messages.OPERATION_CANCELLED,
        )
        self._scheduler = scheduler
        self._bot_config = bot_config
        self._logger = Logger("TaskCommandProcessor")

        # Register commands
        self.register_command(Commands.HELP, self._cmd_help)
        self.register_command(Commands.LIST, self._cmd_list)
        self.register_command(Commands.RUN, self._cmd_run)
        self.register_command(Commands.HISTORY, self._cmd_history)
        self.register_command(
            Commands.ADD, self._cmd_add, requires_permission="allow_add"
        )
        self.register_command(
            Commands.EDIT, self._cmd_edit, requires_permission="allow_edit"
        )
        self.register_command(
            Commands.DELETE, self._cmd_delete, requires_permission="allow_delete"
        )

        # Register conversations with on_confirmed callbacks
        self.register_conversation(
            "add_wizard", AddWizard.advance, on_confirmed=self._execute_add
        )
        self.register_conversation(
            "edit_wizard", EditWizard.advance, on_confirmed=self._execute_edit
        )
        self.register_conversation(
            "confirm_delete",
            DeleteConfirmation.handle_response,
            on_confirmed=self._execute_delete,
        )

        # Set permission checker
        self.set_permission_checker(self._check_permission)

    def _check_permission(self, permission: str, user_id: str) -> bool:
        """Check if a permission is allowed."""
        if permission == "allow_add":
            return self._bot_config.allow_add
        if permission == "allow_edit":
            return self._bot_config.allow_edit
        if permission == "allow_delete":
            return self._bot_config.allow_delete
        return True

    # -- Command handlers --

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
        self.start_conversation(user_id, state)
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
        self.start_conversation(user_id, state)
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
        self.start_conversation(user_id, state)
        return response

    # -- on_confirmed callbacks (receive state.data dict) --

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

    def _execute_delete(self, data: dict) -> BotResponse:
        """Execute task deletion."""
        try:
            task_id = data["task_id"]
            task_name = data["task_name"]
            self._scheduler.remove_task(task_id)
            return BotResponse(text=Messages.TASK_DELETED.format(task_name, task_id))
        except Exception as e:
            return BotResponse(text=f"Error deleting task: {e}")

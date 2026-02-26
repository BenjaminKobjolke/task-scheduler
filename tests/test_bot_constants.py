"""Tests for bot constants module."""

from src.bot.constants import Commands, Messages


class TestCommands:
    """Tests for Commands constants."""

    def test_list_command(self) -> None:
        assert Commands.LIST == "/list"

    def test_run_command(self) -> None:
        assert Commands.RUN == "/run"

    def test_history_command(self) -> None:
        assert Commands.HISTORY == "/history"

    def test_add_command(self) -> None:
        assert Commands.ADD == "/add"

    def test_edit_command(self) -> None:
        assert Commands.EDIT == "/edit"

    def test_delete_command(self) -> None:
        assert Commands.DELETE == "/delete"

    def test_help_command(self) -> None:
        assert Commands.HELP == "/help"

    def test_cancel_command(self) -> None:
        assert Commands.CANCEL == "/cancel"

    def test_all_commands_start_with_slash(self) -> None:
        command_values = [
            Commands.LIST,
            Commands.RUN,
            Commands.HISTORY,
            Commands.ADD,
            Commands.EDIT,
            Commands.DELETE,
            Commands.HELP,
            Commands.CANCEL,
        ]
        for cmd in command_values:
            assert cmd.startswith("/"), f"Command {cmd} does not start with /"


class TestMessages:
    """Tests for Messages constants."""

    def test_help_message_contains_all_commands(self) -> None:
        assert "/list" in Messages.HELP
        assert "/run" in Messages.HELP
        assert "/history" in Messages.HELP
        assert "/add" in Messages.HELP
        assert "/edit" in Messages.HELP
        assert "/delete" in Messages.HELP
        assert "/cancel" in Messages.HELP
        assert "/help" in Messages.HELP

    def test_unknown_command_message(self) -> None:
        assert "/help" in Messages.UNKNOWN_COMMAND

    def test_command_disabled_is_template(self) -> None:
        result = Messages.COMMAND_DISABLED.format("/add")
        assert "/add" in result

    def test_task_not_found_is_template(self) -> None:
        result = Messages.TASK_NOT_FOUND.format(42)
        assert "42" in result

    def test_task_executed_success_is_template(self) -> None:
        result = Messages.TASK_EXECUTED_SUCCESS.format("Backup", 1)
        assert "Backup" in result
        assert "1" in result

    def test_task_executed_failure_is_template(self) -> None:
        result = Messages.TASK_EXECUTED_FAILURE.format("Backup", 1)
        assert "Backup" in result
        assert "1" in result

    def test_task_execution_error_is_template(self) -> None:
        result = Messages.TASK_EXECUTION_ERROR.format(1, "timeout")
        assert "1" in result
        assert "timeout" in result

    def test_confirm_delete_is_template(self) -> None:
        result = Messages.CONFIRM_DELETE.format("Backup", 1)
        assert "Backup" in result
        assert "1" in result

    def test_task_deleted_is_template(self) -> None:
        result = Messages.TASK_DELETED.format("Backup", 1)
        assert "Backup" in result
        assert "1" in result

    def test_no_tasks_message(self) -> None:
        assert Messages.NO_TASKS == "No tasks scheduled."

    def test_no_history_message(self) -> None:
        assert Messages.NO_HISTORY == "No execution history found."

    def test_invalid_task_id_is_template(self) -> None:
        result = Messages.INVALID_TASK_ID.format("/run")
        assert "/run" in result

    def test_conversation_expired_message(self) -> None:
        assert "expired" in Messages.CONVERSATION_EXPIRED.lower()

    def test_wizard_add_start_message(self) -> None:
        assert "script path" in Messages.WIZARD_ADD_START.lower()

    def test_wizard_add_command_message(self) -> None:
        assert "command" in Messages.WIZARD_ADD_COMMAND.lower()

    def test_wizard_add_name_message(self) -> None:
        assert "name" in Messages.WIZARD_ADD_NAME.lower()

    def test_wizard_add_interval_message(self) -> None:
        assert "interval" in Messages.WIZARD_ADD_INTERVAL.lower()

    def test_wizard_add_start_time_message(self) -> None:
        assert "time" in Messages.WIZARD_ADD_START_TIME.lower()

    def test_wizard_add_arguments_message(self) -> None:
        assert "argument" in Messages.WIZARD_ADD_ARGUMENTS.lower()

    def test_wizard_add_confirm_is_template(self) -> None:
        result = Messages.WIZARD_ADD_CONFIRM.format("Task info")
        assert "Task info" in result

    def test_wizard_add_success_is_template(self) -> None:
        result = Messages.WIZARD_ADD_SUCCESS.format("Backup", 5)
        assert "Backup" in result
        assert "5" in result

    def test_wizard_invalid_interval_message(self) -> None:
        assert "number" in Messages.WIZARD_INVALID_INTERVAL.lower()

    def test_wizard_invalid_time_message(self) -> None:
        assert "HH:MM" in Messages.WIZARD_INVALID_TIME

    def test_wizard_edit_start_is_template(self) -> None:
        result = Messages.WIZARD_EDIT_START.format("Backup", 1, "details")
        assert "Backup" in result
        assert "1" in result

    def test_wizard_edit_field_templates(self) -> None:
        assert Messages.WIZARD_EDIT_SCRIPT.format("path/to/script.py")
        assert Messages.WIZARD_EDIT_COMMAND.format("serve")
        assert Messages.WIZARD_EDIT_NAME.format("My Task")
        assert Messages.WIZARD_EDIT_INTERVAL.format(30)
        assert Messages.WIZARD_EDIT_START_TIME.format("09:00")
        assert Messages.WIZARD_EDIT_ARGUMENTS.format("--verbose")

    def test_wizard_edit_confirm_is_template(self) -> None:
        result = Messages.WIZARD_EDIT_CONFIRM.format("Name: old -> new")
        assert "Name: old -> new" in result

    def test_wizard_edit_success_is_template(self) -> None:
        result = Messages.WIZARD_EDIT_SUCCESS.format("Backup", 1)
        assert "Backup" in result
        assert "1" in result

    def test_wizard_edit_no_changes_message(self) -> None:
        assert "no changes" in Messages.WIZARD_EDIT_NO_CHANGES.lower()

    def test_delete_cancelled_message(self) -> None:
        assert "cancel" in Messages.DELETE_CANCELLED.lower()

    def test_operation_cancelled_message(self) -> None:
        assert "cancel" in Messages.OPERATION_CANCELLED.lower()

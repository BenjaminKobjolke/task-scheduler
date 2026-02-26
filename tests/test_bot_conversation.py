"""Tests for bot conversation state machines."""
import time

from src.bot.constants import Messages
from src.bot.conversation import (
    CONVERSATION_TIMEOUT,
    AddWizard,
    ConversationState,
    DeleteConfirmation,
    EditWizard,
)
from src.bot.types import BotResponse


class TestConversationState:
    """Tests for ConversationState dataclass."""

    def test_create_with_defaults(self) -> None:
        state = ConversationState(kind="add_wizard")
        assert state.kind == "add_wizard"
        assert state.step == 0
        assert state.data == {}
        assert state.expires_at > time.time()

    def test_create_with_custom_values(self) -> None:
        data = {"task_id": 5}
        state = ConversationState(kind="confirm_delete", step=1, data=data)
        assert state.kind == "confirm_delete"
        assert state.step == 1
        assert state.data == {"task_id": 5}

    def test_is_expired_returns_false_when_fresh(self) -> None:
        state = ConversationState(kind="add_wizard")
        assert state.is_expired() is False

    def test_is_expired_returns_true_when_past(self) -> None:
        state = ConversationState(kind="add_wizard")
        state.expires_at = time.time() - 1
        assert state.is_expired() is True

    def test_default_expiry_uses_timeout_constant(self) -> None:
        before = time.time()
        state = ConversationState(kind="add_wizard")
        after = time.time()
        assert before + CONVERSATION_TIMEOUT <= state.expires_at <= after + CONVERSATION_TIMEOUT

    def test_timeout_constant_is_300_seconds(self) -> None:
        assert CONVERSATION_TIMEOUT == 300

    def test_data_is_independent_between_instances(self) -> None:
        state1 = ConversationState(kind="add_wizard")
        state2 = ConversationState(kind="add_wizard")
        state1.data["key"] = "value"
        assert "key" not in state2.data


class TestAddWizardStart:
    """Tests for AddWizard.start()."""

    def test_start_returns_state_and_response(self) -> None:
        state, response = AddWizard.start()
        assert isinstance(state, ConversationState)
        assert isinstance(response, BotResponse)

    def test_start_state_kind_is_add_wizard(self) -> None:
        state, _ = AddWizard.start()
        assert state.kind == "add_wizard"

    def test_start_state_step_is_zero(self) -> None:
        state, _ = AddWizard.start()
        assert state.step == 0

    def test_start_response_text_is_wizard_start(self) -> None:
        _, response = AddWizard.start()
        assert response.text == Messages.WIZARD_ADD_START


class TestAddWizardScriptFlow:
    """Tests for AddWizard full flow with a script task."""

    def test_step0_script_path_sets_type_script(self) -> None:
        state, _ = AddWizard.start()
        new_state, response = AddWizard.advance(state, "C:/scripts/backup.py")
        assert new_state is not None
        assert new_state.data["task_type"] == "script"
        assert new_state.data["script_path"] == "C:/scripts/backup.py"

    def test_step0_script_path_skips_to_name_step(self) -> None:
        state, _ = AddWizard.start()
        new_state, response = AddWizard.advance(state, "C:/scripts/backup.py")
        assert new_state is not None
        assert new_state.step == 2
        assert response.text == Messages.WIZARD_ADD_NAME

    def test_step2_name(self) -> None:
        state, _ = AddWizard.start()
        state, _ = AddWizard.advance(state, "C:/scripts/backup.py")
        assert state is not None
        new_state, response = AddWizard.advance(state, "Backup Task")
        assert new_state is not None
        assert new_state.data["name"] == "Backup Task"
        assert new_state.step == 3
        assert response.text == Messages.WIZARD_ADD_INTERVAL

    def test_step3_valid_interval(self) -> None:
        state, _ = AddWizard.start()
        state, _ = AddWizard.advance(state, "backup.py")
        assert state is not None
        state, _ = AddWizard.advance(state, "Backup")
        assert state is not None
        new_state, response = AddWizard.advance(state, "60")
        assert new_state is not None
        assert new_state.data["interval"] == 60
        assert new_state.step == 4
        assert response.text == Messages.WIZARD_ADD_START_TIME

    def test_step3_invalid_interval_not_number(self) -> None:
        state, _ = AddWizard.start()
        state, _ = AddWizard.advance(state, "backup.py")
        assert state is not None
        state, _ = AddWizard.advance(state, "Backup")
        assert state is not None
        new_state, response = AddWizard.advance(state, "abc")
        assert new_state is not None
        assert new_state.step == 3  # stays on same step
        assert response.text == Messages.WIZARD_INVALID_INTERVAL

    def test_step3_invalid_interval_zero(self) -> None:
        state, _ = AddWizard.start()
        state, _ = AddWizard.advance(state, "backup.py")
        assert state is not None
        state, _ = AddWizard.advance(state, "Backup")
        assert state is not None
        new_state, response = AddWizard.advance(state, "0")
        assert new_state is not None
        assert new_state.step == 3
        assert response.text == Messages.WIZARD_INVALID_INTERVAL

    def test_step3_invalid_interval_negative(self) -> None:
        state, _ = AddWizard.start()
        state, _ = AddWizard.advance(state, "backup.py")
        assert state is not None
        state, _ = AddWizard.advance(state, "Backup")
        assert state is not None
        new_state, response = AddWizard.advance(state, "-5")
        assert new_state is not None
        assert new_state.step == 3
        assert response.text == Messages.WIZARD_INVALID_INTERVAL

    def test_step4_valid_start_time(self) -> None:
        state = _build_add_state_at_step4()
        new_state, response = AddWizard.advance(state, "09:00")
        assert new_state is not None
        assert new_state.data["start_time"] == "09:00"
        assert new_state.step == 5
        assert response.text == Messages.WIZARD_ADD_ARGUMENTS

    def test_step4_skip_start_time(self) -> None:
        state = _build_add_state_at_step4()
        new_state, response = AddWizard.advance(state, "skip")
        assert new_state is not None
        assert new_state.data["start_time"] is None
        assert new_state.step == 5

    def test_step4_none_start_time(self) -> None:
        state = _build_add_state_at_step4()
        new_state, response = AddWizard.advance(state, "none")
        assert new_state is not None
        assert new_state.data["start_time"] is None

    def test_step4_empty_start_time(self) -> None:
        state = _build_add_state_at_step4()
        new_state, response = AddWizard.advance(state, "")
        assert new_state is not None
        assert new_state.data["start_time"] is None

    def test_step4_invalid_time_format(self) -> None:
        state = _build_add_state_at_step4()
        new_state, response = AddWizard.advance(state, "9am")
        assert new_state is not None
        assert new_state.step == 4  # stays on same step
        assert response.text == Messages.WIZARD_INVALID_TIME

    def test_step4_invalid_time_single_digit(self) -> None:
        state = _build_add_state_at_step4()
        new_state, response = AddWizard.advance(state, "9:00")
        assert new_state is not None
        assert new_state.step == 4
        assert response.text == Messages.WIZARD_INVALID_TIME

    def test_step5_arguments(self) -> None:
        state = _build_add_state_at_step5()
        new_state, response = AddWizard.advance(state, "--verbose --dry-run")
        assert new_state is not None
        assert new_state.data["arguments"] == ["--verbose", "--dry-run"]
        assert new_state.step == 6

    def test_step5_skip_arguments(self) -> None:
        state = _build_add_state_at_step5()
        new_state, response = AddWizard.advance(state, "skip")
        assert new_state is not None
        assert new_state.data["arguments"] is None
        assert new_state.step == 6

    def test_step5_empty_arguments(self) -> None:
        state = _build_add_state_at_step5()
        new_state, response = AddWizard.advance(state, "")
        assert new_state is not None
        assert new_state.data["arguments"] is None

    def test_step5_shows_confirmation_summary(self) -> None:
        state = _build_add_state_at_step5()
        new_state, response = AddWizard.advance(state, "skip")
        assert new_state is not None
        assert "confirm" in response.text.lower() or "yes" in response.text.lower()

    def test_step6_confirm_yes_returns_none_state(self) -> None:
        state = _build_add_state_at_step6()
        new_state, response = AddWizard.advance(state, "yes")
        assert new_state is None
        assert response.text == ""

    def test_step6_confirm_no_cancels(self) -> None:
        state = _build_add_state_at_step6()
        new_state, response = AddWizard.advance(state, "no")
        assert new_state is None
        assert response.text == Messages.OPERATION_CANCELLED

    def test_step6_confirm_other_cancels(self) -> None:
        state = _build_add_state_at_step6()
        new_state, response = AddWizard.advance(state, "maybe")
        assert new_state is None
        assert response.text == Messages.OPERATION_CANCELLED

    def test_full_script_flow_preserves_all_data(self) -> None:
        """Full flow: script path -> name -> interval -> start_time -> args -> confirm."""
        state, _ = AddWizard.start()
        state, _ = AddWizard.advance(state, "C:/scripts/backup.py")
        assert state is not None
        state, _ = AddWizard.advance(state, "Backup Task")
        assert state is not None
        state, _ = AddWizard.advance(state, "60")
        assert state is not None
        state, _ = AddWizard.advance(state, "09:00")
        assert state is not None
        state, _ = AddWizard.advance(state, "--verbose")
        assert state is not None

        assert state.data["task_type"] == "script"
        assert state.data["script_path"] == "C:/scripts/backup.py"
        assert state.data["name"] == "Backup Task"
        assert state.data["interval"] == 60
        assert state.data["start_time"] == "09:00"
        assert state.data["arguments"] == ["--verbose"]

        # Confirm
        result_state, response = AddWizard.advance(state, "yes")
        assert result_state is None
        assert response.text == ""


class TestAddWizardUvCommandFlow:
    """Tests for AddWizard with uv command task type."""

    def test_step0_uv_prefix_sets_type_uv_command(self) -> None:
        state, _ = AddWizard.start()
        new_state, response = AddWizard.advance(state, "uv:C:/projects/myapp")
        assert new_state is not None
        assert new_state.data["task_type"] == "uv_command"
        assert new_state.data["script_path"] == "C:/projects/myapp"

    def test_step0_uv_prefix_goes_to_command_step(self) -> None:
        state, _ = AddWizard.start()
        new_state, response = AddWizard.advance(state, "uv:C:/projects/myapp")
        assert new_state is not None
        assert new_state.step == 1
        assert response.text == Messages.WIZARD_ADD_COMMAND

    def test_step1_command_name(self) -> None:
        state, _ = AddWizard.start()
        state, _ = AddWizard.advance(state, "uv:C:/projects/myapp")
        assert state is not None
        new_state, response = AddWizard.advance(state, "serve")
        assert new_state is not None
        assert new_state.data["command"] == "serve"
        assert new_state.step == 2
        assert response.text == Messages.WIZARD_ADD_NAME

    def test_full_uv_command_flow(self) -> None:
        """Full flow: uv:path -> command -> name -> interval -> start_time -> args -> confirm."""
        state, _ = AddWizard.start()
        state, _ = AddWizard.advance(state, "uv:C:/projects/myapp")
        assert state is not None
        state, _ = AddWizard.advance(state, "serve")
        assert state is not None
        state, _ = AddWizard.advance(state, "My UV Task")
        assert state is not None
        state, _ = AddWizard.advance(state, "5")
        assert state is not None
        state, _ = AddWizard.advance(state, "skip")
        assert state is not None
        state, _ = AddWizard.advance(state, "skip")
        assert state is not None

        assert state.data["task_type"] == "uv_command"
        assert state.data["script_path"] == "C:/projects/myapp"
        assert state.data["command"] == "serve"
        assert state.data["name"] == "My UV Task"
        assert state.data["interval"] == 5
        assert state.data["start_time"] is None
        assert state.data["arguments"] is None

        result_state, response = AddWizard.advance(state, "yes")
        assert result_state is None
        assert response.text == ""

    def test_uv_prefix_strips_whitespace(self) -> None:
        state, _ = AddWizard.start()
        new_state, response = AddWizard.advance(state, "uv:  C:/projects/myapp  ")
        assert new_state is not None
        assert new_state.data["script_path"] == "C:/projects/myapp"


class TestAddWizardEdgeCases:
    """Edge case tests for AddWizard."""

    def test_whitespace_only_input_for_script_path(self) -> None:
        state, _ = AddWizard.start()
        new_state, response = AddWizard.advance(state, "   ")
        assert new_state is not None
        # Whitespace-only is treated as empty script path
        assert new_state.data["script_path"] == ""

    def test_step5_quoted_arguments_parsed(self) -> None:
        state = _build_add_state_at_step5()
        new_state, response = AddWizard.advance(state, '--name "my task" --verbose')
        assert new_state is not None
        assert new_state.data["arguments"] == ["--name", "my task", "--verbose"]

    def test_step4_case_insensitive_skip(self) -> None:
        state = _build_add_state_at_step4()
        new_state, _ = AddWizard.advance(state, "Skip")
        assert new_state is not None
        assert new_state.data["start_time"] is None

    def test_step4_case_insensitive_none(self) -> None:
        state = _build_add_state_at_step4()
        new_state, _ = AddWizard.advance(state, "None")
        assert new_state is not None
        assert new_state.data["start_time"] is None

    def test_step5_case_insensitive_skip(self) -> None:
        state = _build_add_state_at_step5()
        new_state, _ = AddWizard.advance(state, "SKIP")
        assert new_state is not None
        assert new_state.data["arguments"] is None

    def test_step6_case_insensitive_yes(self) -> None:
        state = _build_add_state_at_step6()
        new_state, _ = AddWizard.advance(state, "Yes")
        assert new_state is None

    def test_input_stripped_of_whitespace(self) -> None:
        state, _ = AddWizard.start()
        state, _ = AddWizard.advance(state, "  backup.py  ")
        assert state is not None
        assert state.data["script_path"] == "backup.py"


class TestEditWizardStart:
    """Tests for EditWizard.start()."""

    def test_start_returns_state_and_response(self) -> None:
        task = _make_sample_task()
        state, response = EditWizard.start(task)
        assert isinstance(state, ConversationState)
        assert isinstance(response, BotResponse)

    def test_start_state_kind_is_edit_wizard(self) -> None:
        task = _make_sample_task()
        state, _ = EditWizard.start(task)
        assert state.kind == "edit_wizard"

    def test_start_state_stores_original_task(self) -> None:
        task = _make_sample_task()
        state, _ = EditWizard.start(task)
        assert state.data["original"] == task

    def test_start_state_step_is_zero(self) -> None:
        task = _make_sample_task()
        state, _ = EditWizard.start(task)
        assert state.step == 0

    def test_start_response_contains_task_name(self) -> None:
        task = _make_sample_task()
        _, response = EditWizard.start(task)
        assert task["name"] in response.text

    def test_start_response_contains_task_id(self) -> None:
        task = _make_sample_task()
        _, response = EditWizard.start(task)
        assert str(task["id"]) in response.text


class TestEditWizardScriptFlow:
    """Tests for EditWizard full flow with a script task."""

    def test_step0_change_script_path(self) -> None:
        task = _make_sample_task()
        state, _ = EditWizard.start(task)
        new_state, response = EditWizard.advance(state, "new_script.py")
        assert new_state is not None
        assert new_state.data["changes"]["script_path"] == "new_script.py"

    def test_step0_skip_keeps_original(self) -> None:
        task = _make_sample_task()
        state, _ = EditWizard.start(task)
        new_state, response = EditWizard.advance(state, "skip")
        assert new_state is not None
        assert "script_path" not in new_state.data.get("changes", {})

    def test_step0_prompts_script_path_with_current(self) -> None:
        task = _make_sample_task()
        state, response = EditWizard.start(task)
        # The start response should show current values
        # Then advancing to step 0 should ask for script path
        assert state.step == 0

    def test_step1_skipped_for_script_type(self) -> None:
        """For script type tasks, command step (1) should be skipped."""
        task = _make_sample_task()
        state, _ = EditWizard.start(task)
        new_state, response = EditWizard.advance(state, "skip")
        assert new_state is not None
        # Should go to step 2 (name), not step 1 (command)
        assert new_state.step == 2
        assert response.text == Messages.WIZARD_EDIT_NAME.format(task["name"])

    def test_step2_change_name(self) -> None:
        task = _make_sample_task()
        state, _ = EditWizard.start(task)
        state, _ = EditWizard.advance(state, "skip")  # script_path
        assert state is not None
        new_state, response = EditWizard.advance(state, "New Name")
        assert new_state is not None
        assert new_state.data["changes"]["name"] == "New Name"
        assert new_state.step == 3

    def test_step2_skip_name(self) -> None:
        task = _make_sample_task()
        state, _ = EditWizard.start(task)
        state, _ = EditWizard.advance(state, "skip")
        assert state is not None
        new_state, _ = EditWizard.advance(state, "skip")
        assert new_state is not None
        assert "name" not in new_state.data.get("changes", {})

    def test_step3_change_interval(self) -> None:
        state = _build_edit_state_at_step3()
        new_state, response = EditWizard.advance(state, "30")
        assert new_state is not None
        assert new_state.data["changes"]["interval"] == 30
        assert new_state.step == 4

    def test_step3_skip_interval(self) -> None:
        state = _build_edit_state_at_step3()
        new_state, _ = EditWizard.advance(state, "skip")
        assert new_state is not None
        assert "interval" not in new_state.data.get("changes", {})

    def test_step3_invalid_interval(self) -> None:
        state = _build_edit_state_at_step3()
        new_state, response = EditWizard.advance(state, "abc")
        assert new_state is not None
        assert new_state.step == 3
        assert response.text == Messages.WIZARD_INVALID_INTERVAL

    def test_step3_zero_interval(self) -> None:
        state = _build_edit_state_at_step3()
        new_state, response = EditWizard.advance(state, "0")
        assert new_state is not None
        assert new_state.step == 3
        assert response.text == Messages.WIZARD_INVALID_INTERVAL

    def test_step4_change_start_time(self) -> None:
        state = _build_edit_state_at_step4()
        new_state, response = EditWizard.advance(state, "10:30")
        assert new_state is not None
        assert new_state.data["changes"]["start_time"] == "10:30"
        assert new_state.step == 5

    def test_step4_skip_start_time(self) -> None:
        state = _build_edit_state_at_step4()
        new_state, _ = EditWizard.advance(state, "skip")
        assert new_state is not None
        assert "start_time" not in new_state.data.get("changes", {})

    def test_step4_clear_start_time_with_none(self) -> None:
        state = _build_edit_state_at_step4()
        new_state, _ = EditWizard.advance(state, "none")
        assert new_state is not None
        assert new_state.data["changes"]["start_time"] is None

    def test_step4_invalid_time(self) -> None:
        state = _build_edit_state_at_step4()
        new_state, response = EditWizard.advance(state, "bad")
        assert new_state is not None
        assert new_state.step == 4
        assert response.text == Messages.WIZARD_INVALID_TIME

    def test_step5_change_arguments(self) -> None:
        state = _build_edit_state_at_step5()
        new_state, response = EditWizard.advance(state, "--new-arg")
        assert new_state is not None
        assert new_state.data["changes"]["arguments"] == ["--new-arg"]
        assert new_state.step == 6

    def test_step5_skip_arguments(self) -> None:
        state = _build_edit_state_at_step5()
        new_state, _ = EditWizard.advance(state, "skip")
        assert new_state is not None
        assert "arguments" not in new_state.data.get("changes", {})

    def test_step5_clear_arguments_with_none(self) -> None:
        state = _build_edit_state_at_step5()
        new_state, _ = EditWizard.advance(state, "none")
        assert new_state is not None
        assert new_state.data["changes"]["arguments"] is None

    def test_step6_confirm_yes_returns_none(self) -> None:
        state = _build_edit_state_at_step6()
        new_state, response = EditWizard.advance(state, "yes")
        assert new_state is None
        assert response.text == ""

    def test_step6_confirm_no_cancels(self) -> None:
        state = _build_edit_state_at_step6()
        new_state, response = EditWizard.advance(state, "no")
        assert new_state is None
        assert response.text == Messages.OPERATION_CANCELLED

    def test_step6_no_changes_reports_no_changes(self) -> None:
        """When all fields are skipped, confirm step should show no changes."""
        task = _make_sample_task()
        state, _ = EditWizard.start(task)
        state, _ = EditWizard.advance(state, "skip")  # script_path
        assert state is not None
        state, _ = EditWizard.advance(state, "skip")  # name
        assert state is not None
        state, _ = EditWizard.advance(state, "skip")  # interval
        assert state is not None
        state, _ = EditWizard.advance(state, "skip")  # start_time
        assert state is not None
        state, response = EditWizard.advance(state, "skip")  # arguments
        assert state is not None
        # Should indicate no changes
        assert "no changes" in response.text.lower()

    def test_full_edit_flow_with_changes(self) -> None:
        """Full flow changing some fields."""
        task = _make_sample_task()
        state, _ = EditWizard.start(task)
        state, _ = EditWizard.advance(state, "new_backup.py")  # new script_path
        assert state is not None
        state, _ = EditWizard.advance(state, "skip")  # keep name
        assert state is not None
        state, _ = EditWizard.advance(state, "30")  # new interval
        assert state is not None
        state, _ = EditWizard.advance(state, "skip")  # keep start_time
        assert state is not None
        state, response = EditWizard.advance(state, "skip")  # keep arguments
        assert state is not None

        # Should show changes
        assert state.data["changes"]["script_path"] == "new_backup.py"
        assert state.data["changes"]["interval"] == 30
        assert "name" not in state.data["changes"]

        # Confirm
        result_state, result_response = EditWizard.advance(state, "yes")
        assert result_state is None
        assert result_response.text == ""


class TestEditWizardUvCommandFlow:
    """Tests for EditWizard with uv_command task type."""

    def test_step1_shown_for_uv_command_type(self) -> None:
        task = _make_sample_uv_task()
        state, _ = EditWizard.start(task)
        new_state, response = EditWizard.advance(state, "skip")  # script_path
        assert new_state is not None
        assert new_state.step == 1
        assert response.text == Messages.WIZARD_EDIT_COMMAND.format(task.get("command", ""))

    def test_step1_change_command(self) -> None:
        task = _make_sample_uv_task()
        state, _ = EditWizard.start(task)
        state, _ = EditWizard.advance(state, "skip")  # script_path
        assert state is not None
        new_state, response = EditWizard.advance(state, "new_command")
        assert new_state is not None
        assert new_state.data["changes"]["command"] == "new_command"
        assert new_state.step == 2

    def test_step1_skip_command(self) -> None:
        task = _make_sample_uv_task()
        state, _ = EditWizard.start(task)
        state, _ = EditWizard.advance(state, "skip")
        assert state is not None
        new_state, _ = EditWizard.advance(state, "skip")
        assert new_state is not None
        assert "command" not in new_state.data.get("changes", {})
        assert new_state.step == 2

    def test_full_uv_edit_flow(self) -> None:
        task = _make_sample_uv_task()
        state, _ = EditWizard.start(task)
        state, _ = EditWizard.advance(state, "new/path")  # script_path
        assert state is not None
        state, _ = EditWizard.advance(state, "new_cmd")  # command
        assert state is not None
        state, _ = EditWizard.advance(state, "New UV Task")  # name
        assert state is not None
        state, _ = EditWizard.advance(state, "10")  # interval
        assert state is not None
        state, _ = EditWizard.advance(state, "skip")  # start_time
        assert state is not None
        state, response = EditWizard.advance(state, "skip")  # arguments
        assert state is not None

        assert state.data["changes"]["script_path"] == "new/path"
        assert state.data["changes"]["command"] == "new_cmd"
        assert state.data["changes"]["name"] == "New UV Task"
        assert state.data["changes"]["interval"] == 10

        result_state, _ = EditWizard.advance(state, "yes")
        assert result_state is None


class TestEditWizardEdgeCases:
    """Edge case tests for EditWizard."""

    def test_input_stripped_of_whitespace(self) -> None:
        task = _make_sample_task()
        state, _ = EditWizard.start(task)
        state, _ = EditWizard.advance(state, "  new_script.py  ")
        assert state is not None
        assert state.data["changes"]["script_path"] == "new_script.py"

    def test_step3_interval_minimum_1(self) -> None:
        state = _build_edit_state_at_step3()
        new_state, _ = EditWizard.advance(state, "1")
        assert new_state is not None
        assert new_state.data["changes"]["interval"] == 1

    def test_case_insensitive_skip(self) -> None:
        task = _make_sample_task()
        state, _ = EditWizard.start(task)
        new_state, _ = EditWizard.advance(state, "SKIP")
        assert new_state is not None
        assert "script_path" not in new_state.data.get("changes", {})

    def test_case_insensitive_yes(self) -> None:
        state = _build_edit_state_at_step6()
        new_state, _ = EditWizard.advance(state, "Yes")
        assert new_state is None


class TestDeleteConfirmationStart:
    """Tests for DeleteConfirmation.start()."""

    def test_start_returns_state_and_response(self) -> None:
        state, response = DeleteConfirmation.start(task_id=5, task_name="Backup")
        assert isinstance(state, ConversationState)
        assert isinstance(response, BotResponse)

    def test_start_state_kind(self) -> None:
        state, _ = DeleteConfirmation.start(task_id=5, task_name="Backup")
        assert state.kind == "confirm_delete"

    def test_start_state_stores_task_id(self) -> None:
        state, _ = DeleteConfirmation.start(task_id=5, task_name="Backup")
        assert state.data["task_id"] == 5

    def test_start_state_stores_task_name(self) -> None:
        state, _ = DeleteConfirmation.start(task_id=5, task_name="Backup")
        assert state.data["task_name"] == "Backup"

    def test_start_response_contains_task_name(self) -> None:
        _, response = DeleteConfirmation.start(task_id=5, task_name="Backup")
        assert "Backup" in response.text

    def test_start_response_contains_task_id(self) -> None:
        _, response = DeleteConfirmation.start(task_id=5, task_name="Backup")
        assert "5" in response.text


class TestDeleteConfirmationHandleResponse:
    """Tests for DeleteConfirmation.handle_response()."""

    def test_confirm_yes_returns_none_state(self) -> None:
        state, _ = DeleteConfirmation.start(task_id=5, task_name="Backup")
        new_state, response = DeleteConfirmation.handle_response(state, "yes")
        assert new_state is None
        assert response.text == ""

    def test_confirm_no_cancels(self) -> None:
        state, _ = DeleteConfirmation.start(task_id=5, task_name="Backup")
        new_state, response = DeleteConfirmation.handle_response(state, "no")
        assert new_state is None
        assert response.text == Messages.DELETE_CANCELLED

    def test_confirm_other_cancels(self) -> None:
        state, _ = DeleteConfirmation.start(task_id=5, task_name="Backup")
        new_state, response = DeleteConfirmation.handle_response(state, "maybe")
        assert new_state is None
        assert response.text == Messages.DELETE_CANCELLED

    def test_confirm_yes_case_insensitive(self) -> None:
        state, _ = DeleteConfirmation.start(task_id=5, task_name="Backup")
        new_state, response = DeleteConfirmation.handle_response(state, "Yes")
        assert new_state is None
        assert response.text == ""

    def test_confirm_with_whitespace(self) -> None:
        state, _ = DeleteConfirmation.start(task_id=5, task_name="Backup")
        new_state, response = DeleteConfirmation.handle_response(state, "  yes  ")
        assert new_state is None
        assert response.text == ""

    def test_empty_input_cancels(self) -> None:
        state, _ = DeleteConfirmation.start(task_id=5, task_name="Backup")
        new_state, response = DeleteConfirmation.handle_response(state, "")
        assert new_state is None
        assert response.text == Messages.DELETE_CANCELLED


# -- Helper functions to build wizard states at various steps --


def _make_sample_task() -> dict:
    """Create a sample script task dict."""
    return {
        "id": 1,
        "name": "Backup Script",
        "script_path": "C:/scripts/backup.py",
        "arguments": ["--verbose"],
        "interval": 60,
        "task_type": "script",
        "command": None,
        "start_time": "09:00",
    }


def _make_sample_uv_task() -> dict:
    """Create a sample uv_command task dict."""
    return {
        "id": 2,
        "name": "Serve App",
        "script_path": "C:/projects/myapp",
        "arguments": [],
        "interval": 5,
        "task_type": "uv_command",
        "command": "serve",
        "start_time": None,
    }


def _build_add_state_at_step4() -> ConversationState:
    """Build an AddWizard state ready for step 4 (start_time)."""
    state, _ = AddWizard.start()
    state, _ = AddWizard.advance(state, "backup.py")
    assert state is not None
    state, _ = AddWizard.advance(state, "Backup")
    assert state is not None
    state, _ = AddWizard.advance(state, "60")
    assert state is not None
    return state


def _build_add_state_at_step5() -> ConversationState:
    """Build an AddWizard state ready for step 5 (arguments)."""
    state = _build_add_state_at_step4()
    state, _ = AddWizard.advance(state, "skip")
    assert state is not None
    return state


def _build_add_state_at_step6() -> ConversationState:
    """Build an AddWizard state ready for step 6 (confirm)."""
    state = _build_add_state_at_step5()
    state, _ = AddWizard.advance(state, "skip")
    assert state is not None
    return state


def _build_edit_state_at_step3() -> ConversationState:
    """Build an EditWizard state at step 3 (interval)."""
    task = _make_sample_task()
    state, _ = EditWizard.start(task)
    state, _ = EditWizard.advance(state, "skip")  # script_path
    assert state is not None
    state, _ = EditWizard.advance(state, "skip")  # name
    assert state is not None
    return state


def _build_edit_state_at_step4() -> ConversationState:
    """Build an EditWizard state at step 4 (start_time)."""
    state = _build_edit_state_at_step3()
    state, _ = EditWizard.advance(state, "skip")  # interval
    assert state is not None
    return state


def _build_edit_state_at_step5() -> ConversationState:
    """Build an EditWizard state at step 5 (arguments)."""
    state = _build_edit_state_at_step4()
    state, _ = EditWizard.advance(state, "skip")  # start_time
    assert state is not None
    return state


def _build_edit_state_at_step6() -> ConversationState:
    """Build an EditWizard state at step 6 (confirm) with at least one change."""
    task = _make_sample_task()
    state, _ = EditWizard.start(task)
    state, _ = EditWizard.advance(state, "new_script.py")  # change script_path
    assert state is not None
    state, _ = EditWizard.advance(state, "skip")  # name
    assert state is not None
    state, _ = EditWizard.advance(state, "skip")  # interval
    assert state is not None
    state, _ = EditWizard.advance(state, "skip")  # start_time
    assert state is not None
    state, _ = EditWizard.advance(state, "skip")  # arguments
    assert state is not None
    return state

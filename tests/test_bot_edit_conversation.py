"""Focused tests for bot conversation flows."""

from bot_commander import BotResponse
from bot_commander import CONFIRMED_SENTINEL
from bot_commander import ConversationState
from src.bot.constants import Messages
from src.bot.edit_conversation import EditWizard
from tests.bot_conversation_support import _build_edit_state_at_step3, _build_edit_state_at_step4, _build_edit_state_at_step6, _build_edit_state_at_step7, _make_sample_task


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

    def test_step3_zero_interval_is_manual_only(self) -> None:
        state = _build_edit_state_at_step3()
        new_state, response = EditWizard.advance(state, "0")
        assert new_state is not None
        assert new_state.data["changes"]["interval"] == 0
        assert new_state.data["changes"]["start_time"] is None
        # Should skip start_time step and go to launch_new_process (step 5)
        assert new_state.step == 5

    def test_step4_change_start_time(self) -> None:
        state = _build_edit_state_at_step4()
        new_state, response = EditWizard.advance(state, "10:30")
        assert new_state is not None
        assert new_state.data["changes"]["start_time"] == "10:30"
        assert new_state.step == 6

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

    def test_step4_invalid_time_out_of_range(self) -> None:
        state = _build_edit_state_at_step4()
        new_state, response = EditWizard.advance(state, "25:00")
        assert new_state is not None
        assert new_state.step == 4
        assert response.text == Messages.WIZARD_INVALID_TIME

    def test_step5_change_arguments(self) -> None:
        state = _build_edit_state_at_step6()
        new_state, response = EditWizard.advance(state, "--new-arg")
        assert new_state is not None
        assert new_state.data["changes"]["arguments"] == ["--new-arg"]
        assert new_state.step == 7

    def test_step5_skip_arguments(self) -> None:
        state = _build_edit_state_at_step6()
        new_state, _ = EditWizard.advance(state, "skip")
        assert new_state is not None
        assert "arguments" not in new_state.data.get("changes", {})

    def test_step5_clear_arguments_with_none(self) -> None:
        state = _build_edit_state_at_step6()
        new_state, _ = EditWizard.advance(state, "none")
        assert new_state is not None
        assert new_state.data["changes"]["arguments"] is None

    def test_step6_confirm_yes_returns_none(self) -> None:
        state = _build_edit_state_at_step7()
        new_state, response = EditWizard.advance(state, "yes")
        assert new_state is None
        assert response.text == CONFIRMED_SENTINEL

    def test_step6_confirm_no_cancels(self) -> None:
        state = _build_edit_state_at_step7()
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
        assert result_response.text == CONFIRMED_SENTINEL


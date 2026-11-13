"""Focused tests for bot conversation flows."""

from bot_commander import BotResponse
from bot_commander import CONFIRMED_SENTINEL
from bot_commander import ConversationState
from src.bot.add_conversation import AddWizard
from src.bot.constants import Messages
from tests.bot_conversation_support import _build_add_state_at_step4, _build_add_state_at_step6, _build_add_state_at_step7


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

    def test_step3_interval_zero_is_manual_only(self) -> None:
        state, _ = AddWizard.start()
        state, _ = AddWizard.advance(state, "backup.py")
        assert state is not None
        state, _ = AddWizard.advance(state, "Backup")
        assert state is not None
        new_state, response = AddWizard.advance(state, "0")
        assert new_state is not None
        assert new_state.data["interval"] == 0
        assert new_state.data["start_time"] is None
        # Should skip start_time step and go to launch_new_process (step 5)
        assert new_state.step == 5
        assert response.text == Messages.WIZARD_ADD_LAUNCH_NEW_PROCESS

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
        assert new_state.step == 6
        assert response.text == Messages.WIZARD_ADD_ARGUMENTS

    def test_step4_skip_start_time(self) -> None:
        state = _build_add_state_at_step4()
        new_state, response = AddWizard.advance(state, "skip")
        assert new_state is not None
        assert new_state.data["start_time"] is None
        assert new_state.step == 6

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

    def test_step4_invalid_time_out_of_range_hours(self) -> None:
        state = _build_add_state_at_step4()
        new_state, response = AddWizard.advance(state, "25:00")
        assert new_state is not None
        assert new_state.step == 4
        assert response.text == Messages.WIZARD_INVALID_TIME

    def test_step4_invalid_time_out_of_range_minutes(self) -> None:
        state = _build_add_state_at_step4()
        new_state, response = AddWizard.advance(state, "12:60")
        assert new_state is not None
        assert new_state.step == 4
        assert response.text == Messages.WIZARD_INVALID_TIME

    def test_step4_invalid_time_99_99(self) -> None:
        state = _build_add_state_at_step4()
        new_state, response = AddWizard.advance(state, "99:99")
        assert new_state is not None
        assert new_state.step == 4
        assert response.text == Messages.WIZARD_INVALID_TIME

    def test_step5_arguments(self) -> None:
        state = _build_add_state_at_step6()
        new_state, response = AddWizard.advance(state, "--verbose --dry-run")
        assert new_state is not None
        assert new_state.data["arguments"] == ["--verbose", "--dry-run"]
        assert new_state.step == 7

    def test_step5_skip_arguments(self) -> None:
        state = _build_add_state_at_step6()
        new_state, response = AddWizard.advance(state, "skip")
        assert new_state is not None
        assert new_state.data["arguments"] is None
        assert new_state.step == 7

    def test_step5_empty_arguments(self) -> None:
        state = _build_add_state_at_step6()
        new_state, response = AddWizard.advance(state, "")
        assert new_state is not None
        assert new_state.data["arguments"] is None

    def test_step5_shows_confirmation_summary(self) -> None:
        state = _build_add_state_at_step6()
        new_state, response = AddWizard.advance(state, "skip")
        assert new_state is not None
        assert "confirm" in response.text.lower() or "yes" in response.text.lower()

    def test_step6_confirm_yes_returns_none_state(self) -> None:
        state = _build_add_state_at_step7()
        new_state, response = AddWizard.advance(state, "yes")
        assert new_state is None
        assert response.text == CONFIRMED_SENTINEL

    def test_step6_confirm_no_cancels(self) -> None:
        state = _build_add_state_at_step7()
        new_state, response = AddWizard.advance(state, "no")
        assert new_state is None
        assert response.text == Messages.OPERATION_CANCELLED

    def test_step6_confirm_other_cancels(self) -> None:
        state = _build_add_state_at_step7()
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
        assert response.text == CONFIRMED_SENTINEL


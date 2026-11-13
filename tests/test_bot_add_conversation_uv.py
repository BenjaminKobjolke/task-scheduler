"""Focused tests for bot conversation flows."""

from bot_commander import CONFIRMED_SENTINEL
from src.bot.add_conversation import AddWizard
from src.bot.constants import Messages
from tests.bot_conversation_support import _build_add_state_at_step4, _build_add_state_at_step6, _build_add_state_at_step7


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
        assert response.text == CONFIRMED_SENTINEL

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
        state = _build_add_state_at_step6()
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
        state = _build_add_state_at_step6()
        new_state, _ = AddWizard.advance(state, "SKIP")
        assert new_state is not None
        assert new_state.data["arguments"] is None

    def test_step6_case_insensitive_yes(self) -> None:
        state = _build_add_state_at_step7()
        new_state, _ = AddWizard.advance(state, "Yes")
        assert new_state is None

    def test_input_stripped_of_whitespace(self) -> None:
        state, _ = AddWizard.start()
        state, _ = AddWizard.advance(state, "  backup.py  ")
        assert state is not None
        assert state.data["script_path"] == "backup.py"


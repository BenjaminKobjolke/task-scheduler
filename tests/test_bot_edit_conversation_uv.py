"""Focused tests for bot conversation flows."""

from src.bot.constants import Messages
from src.bot.edit_conversation import EditWizard
from tests.bot_conversation_support import _build_edit_state_at_step3, _build_edit_state_at_step7, _make_sample_task, _make_sample_uv_task


class TestEditWizardUvCommandFlow:
    """Tests for EditWizard with uv_command task type."""

    def test_step1_shown_for_uv_command_type(self) -> None:
        task = _make_sample_uv_task()
        state, _ = EditWizard.start(task)
        new_state, response = EditWizard.advance(state, "skip")  # script_path
        assert new_state is not None
        assert new_state.step == 1
        assert response.text == Messages.WIZARD_EDIT_COMMAND.format(
            task.get("command", "")
        )

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
        state = _build_edit_state_at_step7()
        new_state, _ = EditWizard.advance(state, "Yes")
        assert new_state is None


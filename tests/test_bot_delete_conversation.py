"""Focused tests for bot conversation flows."""

from bot_commander import BotResponse
from bot_commander import CONFIRMED_SENTINEL
from bot_commander import ConversationState
from src.bot.constants import Messages
from src.bot.delete_confirmation import DeleteConfirmation


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
        assert response.text == CONFIRMED_SENTINEL

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
        assert response.text == CONFIRMED_SENTINEL

    def test_confirm_with_whitespace(self) -> None:
        state, _ = DeleteConfirmation.start(task_id=5, task_name="Backup")
        new_state, response = DeleteConfirmation.handle_response(state, "  yes  ")
        assert new_state is None
        assert response.text == CONFIRMED_SENTINEL

    def test_empty_input_cancels(self) -> None:
        state, _ = DeleteConfirmation.start(task_id=5, task_name="Backup")
        new_state, response = DeleteConfirmation.handle_response(state, "")
        assert new_state is None
        assert response.text == Messages.DELETE_CANCELLED


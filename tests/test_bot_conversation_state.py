"""Focused tests for bot conversation flows."""

from bot_commander import ConversationState
from bot_commander.config.constants import DEFAULT_CONVERSATION_TIMEOUT
import time


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
        assert (
            before + DEFAULT_CONVERSATION_TIMEOUT
            <= state.expires_at
            <= after + DEFAULT_CONVERSATION_TIMEOUT
        )

    def test_timeout_constant_is_300_seconds(self) -> None:
        assert DEFAULT_CONVERSATION_TIMEOUT == 300

    def test_data_is_independent_between_instances(self) -> None:
        state1 = ConversationState(kind="add_wizard")
        state2 = ConversationState(kind="add_wizard")
        state1.data["key"] = "value"
        assert "key" not in state2.data


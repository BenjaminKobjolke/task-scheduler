"""Shared setup helpers for bot conversation tests."""

from bot_commander import ConversationState
from src.bot.add_conversation import AddWizard
from src.bot.edit_conversation import EditWizard


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



def _build_add_state_at_step6() -> ConversationState:
    """Build an AddWizard state ready for step 6 (arguments).

    Goes through: script -> name -> interval(60) -> start_time(skip) -> step 6.
    """
    state = _build_add_state_at_step4()
    state, _ = AddWizard.advance(state, "skip")  # start_time
    assert state is not None
    return state



def _build_add_state_at_step7() -> ConversationState:
    """Build an AddWizard state ready for step 7 (confirm)."""
    state = _build_add_state_at_step6()
    state, _ = AddWizard.advance(state, "skip")  # arguments
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



def _build_edit_state_at_step6() -> ConversationState:
    """Build an EditWizard state at step 6 (arguments).

    Goes through: script(skip) -> name(skip) -> interval(skip) -> start_time(skip) -> step 6.
    """
    state = _build_edit_state_at_step4()
    state, _ = EditWizard.advance(state, "skip")  # start_time
    assert state is not None
    return state



def _build_edit_state_at_step7() -> ConversationState:
    """Build an EditWizard state at step 7 (confirm) with at least one change."""
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


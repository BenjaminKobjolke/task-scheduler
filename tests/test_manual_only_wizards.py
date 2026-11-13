"""Tests for manual-only tasks (interval 0)."""



from bot_commander import CONFIRMED_SENTINEL

from src.bot.constants import Messages
from src.bot.conversation import AddWizard, EditWizard


# ---------------------------------------------------------------------------
# Scheduler tests
# ---------------------------------------------------------------------------




class TestAddWizardManualOnly:
    """Tests for AddWizard with interval 0 (manual-only)."""

    def test_interval_zero_skips_start_time(self):
        """Interval 0 should skip start_time step and go to launch_new_process."""
        state, _ = AddWizard.start()
        state, _ = AddWizard.advance(state, "backup.py")
        assert state is not None
        state, _ = AddWizard.advance(state, "Manual Backup")
        assert state is not None
        new_state, response = AddWizard.advance(state, "0")
        assert new_state is not None
        assert new_state.data["interval"] == 0
        assert new_state.data["start_time"] is None
        assert new_state.step == 5
        assert response.text == Messages.WIZARD_ADD_LAUNCH_NEW_PROCESS

    def test_full_manual_only_flow(self):
        """Full flow for manual-only task: path -> name -> interval(0) -> launch(no) -> args -> confirm."""
        state, _ = AddWizard.start()
        state, _ = AddWizard.advance(state, "backup.py")
        assert state is not None
        state, _ = AddWizard.advance(state, "Manual Backup")
        assert state is not None
        state, _ = AddWizard.advance(state, "0")
        assert state is not None
        state, _ = AddWizard.advance(state, "no")  # launch_new_process
        assert state is not None
        state, _ = AddWizard.advance(state, "skip")  # arguments
        assert state is not None

        assert state.data["interval"] == 0
        assert state.data["start_time"] is None
        assert state.data["arguments"] is None

        result_state, response = AddWizard.advance(state, "yes")
        assert result_state is None
        assert response.text == CONFIRMED_SENTINEL

    def test_negative_interval_still_invalid(self):
        """Negative intervals should still be rejected."""
        state, _ = AddWizard.start()
        state, _ = AddWizard.advance(state, "backup.py")
        assert state is not None
        state, _ = AddWizard.advance(state, "Backup")
        assert state is not None
        new_state, response = AddWizard.advance(state, "-1")
        assert new_state is not None
        assert new_state.step == 3
        assert response.text == Messages.WIZARD_INVALID_INTERVAL


class TestEditWizardManualOnly:
    """Tests for EditWizard with interval 0 (manual-only)."""

    def test_edit_interval_to_zero_skips_start_time(self):
        """Changing interval to 0 should skip start_time and clear it."""
        task = {
            "id": 1,
            "name": "Backup Script",
            "script_path": "C:/scripts/backup.py",
            "arguments": ["--verbose"],
            "interval": 60,
            "task_type": "script",
            "command": None,
            "start_time": "09:00",
            "launch_new_process": False,
        }
        state, _ = EditWizard.start(task)
        state, _ = EditWizard.advance(state, "skip")  # script_path
        assert state is not None
        state, _ = EditWizard.advance(state, "skip")  # name
        assert state is not None
        new_state, response = EditWizard.advance(state, "0")  # interval -> 0
        assert new_state is not None
        assert new_state.data["changes"]["interval"] == 0
        assert new_state.data["changes"]["start_time"] is None
        assert new_state.step == 5  # skipped start_time, went to launch_new_process

    def test_edit_skip_interval_when_original_zero(self):
        """Skipping interval on a manual-only task should skip start_time too."""
        task = {
            "id": 1,
            "name": "Manual Task",
            "script_path": "C:/scripts/manual.py",
            "arguments": [],
            "interval": 0,
            "task_type": "script",
            "command": None,
            "start_time": None,
            "launch_new_process": False,
        }
        state, _ = EditWizard.start(task)
        state, _ = EditWizard.advance(state, "skip")  # script_path
        assert state is not None
        state, _ = EditWizard.advance(state, "skip")  # name
        assert state is not None
        new_state, response = EditWizard.advance(state, "skip")  # interval (keep 0)
        assert new_state is not None
        # Should skip start_time since effective interval is still 0, go to launch_new_process
        assert new_state.step == 5

    def test_edit_negative_interval_still_invalid(self):
        """Negative intervals should still be rejected in edit wizard."""
        task = {
            "id": 1,
            "name": "Backup Script",
            "script_path": "C:/scripts/backup.py",
            "arguments": [],
            "interval": 60,
            "task_type": "script",
            "command": None,
            "start_time": None,
        }
        state, _ = EditWizard.start(task)
        state, _ = EditWizard.advance(state, "skip")  # script_path
        assert state is not None
        state, _ = EditWizard.advance(state, "skip")  # name
        assert state is not None
        new_state, response = EditWizard.advance(state, "-1")
        assert new_state is not None
        assert new_state.step == 3
        assert response.text == Messages.WIZARD_INVALID_INTERVAL

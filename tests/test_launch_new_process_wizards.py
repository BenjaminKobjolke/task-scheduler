"""Tests for launch_new_process feature."""



from bot_commander import CONFIRMED_SENTINEL

from src.bot.conversation import AddWizard, EditWizard


# ---------------------------------------------------------------------------
# Database tests
# ---------------------------------------------------------------------------




class TestAddWizardLaunchNewProcess:
    """Tests for AddWizard with launch_new_process prompt."""

    def test_interval_zero_prompts_launch_new_process(self):
        """After interval=0, wizard should prompt for launch_new_process."""
        state, _ = AddWizard.start()
        state, _ = AddWizard.advance(state, "backup.py")
        assert state is not None
        state, _ = AddWizard.advance(state, "Manual Backup")
        assert state is not None
        new_state, response = AddWizard.advance(state, "0")
        assert new_state is not None
        assert new_state.step == 5  # launch_new_process step
        assert "console" in response.text.lower() or "launch" in response.text.lower()

    def test_interval_nonzero_skips_launch_new_process(self):
        """After interval>0, wizard should skip launch_new_process."""
        state, _ = AddWizard.start()
        state, _ = AddWizard.advance(state, "backup.py")
        assert state is not None
        state, _ = AddWizard.advance(state, "Scheduled Backup")
        assert state is not None
        new_state, response = AddWizard.advance(state, "5")
        assert new_state is not None
        assert new_state.step == 4  # start_time step
        assert "start time" in response.text.lower() or "HH:MM" in response.text

    def test_launch_yes_stores_true(self):
        """Answering 'yes' to launch prompt should store True."""
        state, _ = AddWizard.start()
        state, _ = AddWizard.advance(state, "backup.py")
        assert state is not None
        state, _ = AddWizard.advance(state, "Manual Backup")
        assert state is not None
        state, _ = AddWizard.advance(state, "0")
        assert state is not None
        # Now at step 5 (launch_new_process)
        new_state, response = AddWizard.advance(state, "yes")
        assert new_state is not None
        assert new_state.data["launch_new_process"] is True
        assert new_state.step == 6  # arguments step

    def test_launch_no_stores_false(self):
        """Answering 'no' to launch prompt should store False."""
        state, _ = AddWizard.start()
        state, _ = AddWizard.advance(state, "backup.py")
        assert state is not None
        state, _ = AddWizard.advance(state, "Manual Backup")
        assert state is not None
        state, _ = AddWizard.advance(state, "0")
        assert state is not None
        new_state, response = AddWizard.advance(state, "no")
        assert new_state is not None
        assert new_state.data["launch_new_process"] is False
        assert new_state.step == 6  # arguments step

    def test_full_flow_with_launch_new_process(self):
        """Full add flow with launch_new_process=True."""
        state, _ = AddWizard.start()
        state, _ = AddWizard.advance(state, "backup.py")
        assert state is not None
        state, _ = AddWizard.advance(state, "Manual Backup")
        assert state is not None
        state, _ = AddWizard.advance(state, "0")  # interval
        assert state is not None
        state, _ = AddWizard.advance(state, "yes")  # launch_new_process
        assert state is not None
        state, _ = AddWizard.advance(state, "skip")  # arguments
        assert state is not None

        assert state.data["launch_new_process"] is True

        result_state, response = AddWizard.advance(state, "yes")  # confirm
        assert result_state is None
        assert response.text == CONFIRMED_SENTINEL


class TestEditWizardLaunchNewProcess:
    """Tests for EditWizard with launch_new_process."""

    def test_edit_interval_to_zero_prompts_launch(self):
        """Changing interval to 0 should prompt for launch_new_process."""
        task = {
            "id": 1,
            "name": "Backup Script",
            "script_path": "C:/scripts/backup.py",
            "arguments": [],
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
        assert new_state.step == 5  # launch_new_process step
        assert "console" in response.text.lower() or "launch" in response.text.lower()

    def test_edit_interval_nonzero_skips_launch(self):
        """Keeping interval > 0 should skip launch_new_process."""
        task = {
            "id": 1,
            "name": "Backup Script",
            "script_path": "C:/scripts/backup.py",
            "arguments": [],
            "interval": 60,
            "task_type": "script",
            "command": None,
            "start_time": "09:00",
            "launch_new_process": True,
        }
        state, _ = EditWizard.start(task)
        state, _ = EditWizard.advance(state, "skip")  # script_path
        assert state is not None
        state, _ = EditWizard.advance(state, "skip")  # name
        assert state is not None
        new_state, response = EditWizard.advance(state, "skip")  # keep interval 60
        assert new_state is not None
        assert new_state.step == 4  # start_time step (not launch)

    def test_edit_skip_launch_keeps_original(self):
        """Skipping launch prompt on a task with launch=True should keep True."""
        task = {
            "id": 1,
            "name": "Manual Task",
            "script_path": "C:/scripts/manual.py",
            "arguments": [],
            "interval": 0,
            "task_type": "script",
            "command": None,
            "start_time": None,
            "launch_new_process": True,
        }
        state, _ = EditWizard.start(task)
        state, _ = EditWizard.advance(state, "skip")  # script_path
        assert state is not None
        state, _ = EditWizard.advance(state, "skip")  # name
        assert state is not None
        state, _ = EditWizard.advance(state, "skip")  # interval (keep 0)
        assert state is not None
        # Now at step 5 (launch_new_process)
        new_state, response = EditWizard.advance(state, "skip")
        assert new_state is not None
        # skip means no change, should proceed to arguments
        assert new_state.step == 6
        assert "launch_new_process" not in new_state.data["changes"]

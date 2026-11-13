"""Tests for manual-only tasks (interval 0)."""




from src.bot.constants import Messages


# ---------------------------------------------------------------------------
# Scheduler tests
# ---------------------------------------------------------------------------




class TestBotConstantsManualOnly:
    """Tests for bot constants with manual-only references."""

    def test_wizard_add_interval_mentions_manual(self):
        """WIZARD_ADD_INTERVAL should mention 0 = manual only."""
        assert "0" in Messages.WIZARD_ADD_INTERVAL
        assert "manual" in Messages.WIZARD_ADD_INTERVAL.lower()

    def test_wizard_invalid_interval_mentions_zero(self):
        """WIZARD_INVALID_INTERVAL should mention 0 is valid."""
        assert "0" in Messages.WIZARD_INVALID_INTERVAL

"""Compatibility imports for bot conversation flows."""

from src.bot.add_conversation import AddWizard
from src.bot.conversation import AddWizard as FacadeAddWizard
from src.bot.conversation import DeleteConfirmation as FacadeDeleteConfirmation
from src.bot.conversation import EditWizard as FacadeEditWizard
from src.bot.delete_confirmation import DeleteConfirmation
from src.bot.edit_conversation import EditWizard


def test_conversation_facade_reexports_flow_classes() -> None:
    assert FacadeAddWizard is AddWizard
    assert FacadeEditWizard is EditWizard
    assert FacadeDeleteConfirmation is DeleteConfirmation

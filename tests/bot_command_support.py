"""Shared helpers for bot command tests."""

from bot_commander import BotMessage
from src.bot.command_processor import BotConfig, TaskCommandProcessor


def _make_config(
    allow_add: bool = True,
    allow_edit: bool = True,
    allow_delete: bool = True,
) -> BotConfig:
    return BotConfig(
        allow_add=allow_add,
        allow_edit=allow_edit,
        allow_delete=allow_delete,
    )


def _make_task(
    task_id: int = 1,
    name: str = "Backup Script",
    script_path: str = "C:/scripts/backup.py",
    interval: int = 60,
    task_type: str = "script",
    command: str | None = None,
    start_time: str | None = "09:00",
    arguments: list | None = None,
    last_run_time: str | None = None,
    last_run_success: bool | None = None,
    next_run_time: str | None = None,
) -> dict:
    return {
        "id": task_id,
        "name": name,
        "script_path": script_path,
        "arguments": arguments if arguments is not None else ["--verbose"],
        "interval": interval,
        "task_type": task_type,
        "command": command,
        "start_time": start_time,
        "last_run_time": last_run_time,
        "last_run_success": last_run_success,
        "next_run_time": next_run_time,
    }


def _make_execution(
    name: str = "Backup Script",
    execution_time: str = "2026-02-26 10:00:00",
    success: bool = True,
) -> dict:
    return {
        "execution_id": 1,
        "execution_time": execution_time,
        "success": success,
        "task_id": 1,
        "name": name,
        "script_path": "C:/scripts/backup.py",
        "arguments": [],
        "task_type": "script",
        "command": None,
    }


def _advance_add_wizard_to_confirmation(processor: TaskCommandProcessor) -> None:
    processor.handle(BotMessage(user_id="user1", text="/add"))
    processor.handle(BotMessage(user_id="user1", text="backup.py"))
    processor.handle(BotMessage(user_id="user1", text="Task"))
    processor.handle(BotMessage(user_id="user1", text="5"))
    processor.handle(BotMessage(user_id="user1", text="skip"))
    response = processor.handle(BotMessage(user_id="user1", text="skip"))
    assert "confirm" in response.text.lower() or "yes" in response.text.lower()

from .query import handle_ftp_sync, handle_history, handle_list, handle_run_id
from .task_crud import (
    handle_add,
    handle_copy_task,
    handle_delete,
    handle_edit,
    handle_script,
)
from .task_settings import (
    handle_set_arguments,
    handle_set_interval,
    handle_set_start_time,
)

__all__ = [
    "handle_add",
    "handle_copy_task",
    "handle_delete",
    "handle_edit",
    "handle_ftp_sync",
    "handle_history",
    "handle_list",
    "handle_run_id",
    "handle_script",
    "handle_set_arguments",
    "handle_set_interval",
    "handle_set_start_time",
]

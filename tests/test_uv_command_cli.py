"""Tests for the --uv-command CLI path."""

from unittest.mock import MagicMock

import pytest

from src.commands.task_crud import handle_uv_command
from src.constants import TaskTypes
from src.logger import Logger
from src.scheduler import TaskScheduler


@pytest.fixture
def mock_scheduler() -> MagicMock:
    return MagicMock(spec=TaskScheduler)


@pytest.fixture
def mock_logger() -> MagicMock:
    return MagicMock(spec=Logger)


def _make_args(
    uv_command: list[str] | None = None,
    name: str | None = None,
    interval: int | None = None,
    start_time: str | None = None,
    script_args: list[str] | None = None,
) -> MagicMock:
    args = MagicMock()
    args.uv_command = uv_command
    args.name = name
    args.interval = interval
    args.start_time = start_time
    args.script_args = script_args or []
    return args


class TestHandleUvCommandValidation:
    """Tests for argument validation in handle_uv_command."""

    def test_missing_name_exits(
        self, mock_scheduler: MagicMock, mock_logger: MagicMock
    ) -> None:
        args = _make_args(
            uv_command=["C:\\some\\project", "my-cmd"],
            name=None,
            interval=5,
        )
        with pytest.raises(SystemExit):
            handle_uv_command(mock_scheduler, mock_logger, args)
        mock_logger.error.assert_called_once()
        assert "--name" in mock_logger.error.call_args[0][0]

    def test_missing_interval_exits(
        self, mock_scheduler: MagicMock, mock_logger: MagicMock
    ) -> None:
        args = _make_args(
            uv_command=["C:\\some\\project", "my-cmd"],
            name="Test Task",
            interval=None,
        )
        with pytest.raises(SystemExit):
            handle_uv_command(mock_scheduler, mock_logger, args)
        mock_logger.error.assert_called_once()
        assert "--interval" in mock_logger.error.call_args[0][0]

    def test_negative_interval_exits(
        self, mock_scheduler: MagicMock, mock_logger: MagicMock
    ) -> None:
        args = _make_args(
            uv_command=["C:\\some\\project", "my-cmd"],
            name="Test Task",
            interval=-1,
        )
        with pytest.raises(SystemExit):
            handle_uv_command(mock_scheduler, mock_logger, args)
        mock_logger.error.assert_called_once()
        assert "0 or higher" in mock_logger.error.call_args[0][0]

    def test_invalid_start_time_exits(
        self, mock_scheduler: MagicMock, mock_logger: MagicMock, tmp_path: object
    ) -> None:
        project_dir = str(tmp_path)
        (tmp_path / "pyproject.toml").write_text("")  # type: ignore[union-attr]
        (tmp_path / "uv.lock").write_text("")  # type: ignore[union-attr]

        args = _make_args(
            uv_command=[project_dir, "my-cmd"],
            name="Test Task",
            interval=5,
            start_time="25:99",
        )
        with pytest.raises(SystemExit):
            handle_uv_command(mock_scheduler, mock_logger, args)
        mock_logger.error.assert_called_once()
        assert "Invalid start time" in mock_logger.error.call_args[0][0]


class TestHandleUvCommandProjectValidation:
    """Tests for uv project directory validation."""

    def test_missing_pyproject_toml_exits(
        self, mock_scheduler: MagicMock, mock_logger: MagicMock, tmp_path: object
    ) -> None:
        project_dir = str(tmp_path)
        # No pyproject.toml or uv.lock
        args = _make_args(
            uv_command=[project_dir, "my-cmd"],
            name="Test Task",
            interval=5,
        )
        with pytest.raises(SystemExit):
            handle_uv_command(mock_scheduler, mock_logger, args)
        mock_logger.error.assert_called_once()
        assert "pyproject.toml" in mock_logger.error.call_args[0][0]

    def test_missing_uv_lock_exits(
        self, mock_scheduler: MagicMock, mock_logger: MagicMock, tmp_path: object
    ) -> None:
        project_dir = str(tmp_path)
        (tmp_path / "pyproject.toml").write_text("")  # type: ignore[union-attr]
        # No uv.lock
        args = _make_args(
            uv_command=[project_dir, "my-cmd"],
            name="Test Task",
            interval=5,
        )
        with pytest.raises(SystemExit):
            handle_uv_command(mock_scheduler, mock_logger, args)
        mock_logger.error.assert_called_once()
        assert "uv.lock" in mock_logger.error.call_args[0][0]

    def test_nonexistent_directory_exits(
        self, mock_scheduler: MagicMock, mock_logger: MagicMock
    ) -> None:
        args = _make_args(
            uv_command=["C:\\nonexistent\\path", "my-cmd"],
            name="Test Task",
            interval=5,
        )
        with pytest.raises(SystemExit):
            handle_uv_command(mock_scheduler, mock_logger, args)
        mock_logger.error.assert_called_once()


class TestHandleUvCommandSuccess:
    """Tests for successful task creation."""

    def test_adds_task_with_correct_params(
        self, mock_scheduler: MagicMock, mock_logger: MagicMock, tmp_path: object
    ) -> None:
        project_dir = str(tmp_path)
        (tmp_path / "pyproject.toml").write_text("")  # type: ignore[union-attr]
        (tmp_path / "uv.lock").write_text("")  # type: ignore[union-attr]

        args = _make_args(
            uv_command=[project_dir, "sync-to-local"],
            name="My UV Task",
            interval=5,
        )
        handle_uv_command(mock_scheduler, mock_logger, args)

        mock_scheduler.add_task.assert_called_once_with(
            name="My UV Task",
            script_path=project_dir,
            interval=5,
            arguments=[],
            task_type=TaskTypes.UV_COMMAND,
            command="sync-to-local",
            start_time=None,
        )

    def test_passes_script_args(
        self, mock_scheduler: MagicMock, mock_logger: MagicMock, tmp_path: object
    ) -> None:
        project_dir = str(tmp_path)
        (tmp_path / "pyproject.toml").write_text("")  # type: ignore[union-attr]
        (tmp_path / "uv.lock").write_text("")  # type: ignore[union-attr]

        args = _make_args(
            uv_command=[project_dir, "sync-to-local"],
            name="My UV Task",
            interval=5,
            script_args=["--", "--config", "path/to/config.json"],
        )
        handle_uv_command(mock_scheduler, mock_logger, args)

        mock_scheduler.add_task.assert_called_once_with(
            name="My UV Task",
            script_path=project_dir,
            interval=5,
            arguments=["--config", "path/to/config.json"],
            task_type=TaskTypes.UV_COMMAND,
            command="sync-to-local",
            start_time=None,
        )

    def test_passes_start_time(
        self, mock_scheduler: MagicMock, mock_logger: MagicMock, tmp_path: object
    ) -> None:
        project_dir = str(tmp_path)
        (tmp_path / "pyproject.toml").write_text("")  # type: ignore[union-attr]
        (tmp_path / "uv.lock").write_text("")  # type: ignore[union-attr]

        args = _make_args(
            uv_command=[project_dir, "sync-to-local"],
            name="My UV Task",
            interval=5,
            start_time="09:00",
        )
        handle_uv_command(mock_scheduler, mock_logger, args)

        mock_scheduler.add_task.assert_called_once_with(
            name="My UV Task",
            script_path=project_dir,
            interval=5,
            arguments=[],
            task_type=TaskTypes.UV_COMMAND,
            command="sync-to-local",
            start_time="09:00",
        )

    def test_logs_task_details(
        self, mock_scheduler: MagicMock, mock_logger: MagicMock, tmp_path: object
    ) -> None:
        project_dir = str(tmp_path)
        (tmp_path / "pyproject.toml").write_text("")  # type: ignore[union-attr]
        (tmp_path / "uv.lock").write_text("")  # type: ignore[union-attr]

        args = _make_args(
            uv_command=[project_dir, "sync-to-local"],
            name="My UV Task",
            interval=5,
        )
        handle_uv_command(mock_scheduler, mock_logger, args)

        # Verify logging happened (at least "Task added successfully" message)
        info_messages = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("added successfully" in msg for msg in info_messages)

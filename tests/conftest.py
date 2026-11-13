"""Shared fixtures for the test suite."""

import logging
import tempfile
from unittest.mock import MagicMock, patch

import pytest

import src.config as config_module
from src.bot.command_processor import BotConfig, TaskCommandProcessor
from src.database import Database
from src.scheduler import TaskScheduler
from src.scheduler_jobs import SchedulerJobs
from src.script_runner import ScriptRunner
from src.status_page import StatusPage


@pytest.fixture(autouse=True)
def reset_config_singleton_for_logger_tests(request):
    if request.node.path.name.startswith("test_logger_"):
        config_module.Config._instance = None
        yield
        config_module.Config._instance = None
    else:
        yield


@pytest.fixture
def temp_logs_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir
        for name in list(logging.Logger.manager.loggerDict):
            log = logging.getLogger(name)
            for handler in log.handlers[:]:
                handler.close()
                log.removeHandler(handler)


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as directory:
        yield directory


@pytest.fixture
def mock_handler():
    from src.interaction import InteractionHandler

    return MagicMock(spec=InteractionHandler)


@pytest.fixture
def mock_output():
    from src.interaction import ScriptOutput

    return MagicMock(spec=ScriptOutput)


@pytest.fixture
def scheduler_mock():
    mock = MagicMock(spec=TaskScheduler)
    mock.db = MagicMock(spec=Database)
    return mock


@pytest.fixture
def processor(scheduler_mock):
    with patch("src.bot.command_processor.Logger"):
        return TaskCommandProcessor(
            scheduler=scheduler_mock,
            bot_config=BotConfig(allow_add=True, allow_edit=True, allow_delete=True),
        )


@pytest.fixture
def mock_scheduler():
    with patch.object(TaskScheduler, "__init__", lambda self: None):
        scheduler = TaskScheduler()
        scheduler.logger = MagicMock()
        scheduler.script_runner = MagicMock(spec=ScriptRunner)
        scheduler.db = MagicMock(spec=Database)
        scheduler.status_page = MagicMock(spec=StatusPage)
        scheduler.scheduler = MagicMock()
        scheduler._task_checksums = {}
        scheduler._job_scheduling = SchedulerJobs(
            scheduler.scheduler,
            scheduler.db,
            scheduler.logger,
            scheduler._process_job,
            scheduler._get_job_id,
        )
        return scheduler

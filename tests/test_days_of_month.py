"""Tests for days-of-month scheduling."""

import os
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.database import Database
from src.formatters import format_task_list
from src.month_days import (
    format_days_schedule,
    next_monthly_run,
    parse_days_of_month,
)
from src.scheduler import TaskScheduler
from src.scheduler_jobs import SchedulerJobs
from src.script_runner import ScriptRunner
from src.status_page import StatusPage


class TestParseDaysOfMonth:
    @pytest.mark.parametrize(
        "value, expected",
        [
            ("3", "3"),
            ("3,4,5", "3,4,5"),
            ("3-5", "3,4,5"),
            ("1,15-17", "1,15,16,17"),
            (" 5 , 3 ,3 ", "3,5"),
            ("31", "31"),
        ],
    )
    def test_valid(self, value, expected):
        assert parse_days_of_month(value) == expected

    @pytest.mark.parametrize("value", ["", "0", "32", "5-3", "abc", "3,", "1-"])
    def test_invalid(self, value):
        with pytest.raises(ValueError):
            parse_days_of_month(value)


class TestNextMonthlyRun:
    DAYS = "3,4,5"

    def test_no_history_waits_for_next_slot(self):
        now = datetime(2026, 11, 1, 12, 0)
        assert next_monthly_run(self.DAYS, "08:00", None, now) == datetime(
            2026, 11, 3, 8, 0
        )

    def test_missed_3rd_started_4th_before_slot_waits(self):
        now = datetime(2026, 11, 4, 7, 0)
        last = datetime(2026, 10, 5, 8, 0)
        assert next_monthly_run(self.DAYS, "08:00", last, now) == datetime(
            2026, 11, 4, 8, 0
        )

    def test_missed_slot_started_6th_catches_up_now(self):
        now = datetime(2026, 11, 6, 9, 0)
        last = datetime(2026, 10, 5, 8, 0)
        assert next_monthly_run(self.DAYS, "08:00", last, now) == now

    def test_missed_slot_next_is_tomorrow_catches_up_now(self):
        now = datetime(2026, 11, 4, 9, 0)
        last = datetime(2026, 11, 2, 8, 0)
        assert next_monthly_run(self.DAYS, "08:00", last, now) == now

    def test_already_ran_this_slot_waits(self):
        now = datetime(2026, 11, 5, 9, 0)
        last = datetime(2026, 11, 5, 8, 0, 5)
        assert next_monthly_run(self.DAYS, "08:00", last, now) == datetime(
            2026, 12, 3, 8, 0
        )

    def test_missing_start_time_defaults_to_midnight(self):
        now = datetime(2026, 11, 1, 12, 0)
        assert next_monthly_run("3", None, None, now) == datetime(2026, 11, 3, 0, 0)

    def test_day_31_skips_short_months(self):
        now = datetime(2026, 11, 1, 0, 0)
        assert next_monthly_run("31", "08:00", None, now) == datetime(
            2026, 12, 31, 8, 0
        )


class TestFormat:
    def test_format_days_schedule(self):
        assert format_days_schedule("3,4,5", "08:00") == "days 3,4,5 at 08:00"
        assert format_days_schedule("3", None) == "days 3 at 00:00"

    def test_task_list_shows_days(self):
        task = {
            "id": 1,
            "name": "monthly",
            "script_path": "x.bat",
            "interval": 1440,
            "start_time": "08:00",
            "days_of_month": "3,4,5",
            "arguments": [],
            "next_run_time": None,
        }
        assert "Schedule: days 3,4,5 at 08:00" in format_task_list([task])

    def test_bot_compact_list_shows_days(self):
        from src.bot.formatters import format_task_list_compact

        task = {"id": 1, "name": "monthly", "interval": 1440, "days_of_month": "3-5"}
        assert "1. monthly [days 3-5]" in format_task_list_compact([task])


@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        yield Database(os.path.join(tmpdir, "test.sqlite"))


class TestDatabase:
    def test_round_trip(self, temp_db):
        task_id = temp_db.add_task(
            "m", "x.bat", 1440, start_time="08:00", days_of_month="3,4,5"
        )
        assert temp_db.get_all_tasks()[0]["days_of_month"] == "3,4,5"
        temp_db.edit_task(task_id, "m", "x.bat", 1440, days_of_month=None)
        assert temp_db.get_all_tasks()[0]["days_of_month"] is None


class TestSchedulerJob:
    def test_days_task_uses_cron_trigger(self):
        with patch.object(TaskScheduler, "__init__", lambda self: None):
            scheduler = TaskScheduler()
        scheduler.logger = MagicMock()
        scheduler.script_runner = MagicMock(spec=ScriptRunner)
        scheduler.db = MagicMock(spec=Database)
        scheduler.db.get_last_execution_per_task.return_value = {}
        scheduler.status_page = MagicMock(spec=StatusPage)
        scheduler.scheduler = MagicMock()
        scheduler._job_scheduling = SchedulerJobs(
            scheduler.scheduler,
            scheduler.db,
            scheduler.logger,
            scheduler._process_job,
            scheduler._get_job_id,
        )

        scheduler._schedule_task(
            7, "m", "x.bat", 1440, start_time="08:00", days_of_month="3,4,5"
        )

        trigger = scheduler.scheduler.add_job.call_args.kwargs["trigger"]
        assert type(trigger).__name__ == "CronTrigger"
        assert "day='3,4,5'" in str(trigger)

"""Days-of-month scheduling: parsing, next-run calculation, display."""

from datetime import datetime, time, timedelta
from typing import Iterator, Optional

from .constants import Defaults

# Longest gap between two matching days (e.g. day 31 across Feb-Mar) is < 62 days.
_SCAN_DAYS = 62


def parse_days_of_month(value: str) -> str:
    """Parse "3", "3,4,5", "3-5" or "1,15-17" into a sorted "1,15,16,17".

    Raises:
        ValueError: if empty, malformed, out of 1-31, or a reversed range.
    """
    days: set[int] = set()
    for part in (value or "").split(","):
        part = part.strip()
        start_text, sep, end_text = part.partition("-")
        try:
            start = int(start_text)
            end = int(end_text) if sep else start
        except ValueError as exc:
            raise ValueError(
                f"Invalid days of month: {value!r}. Use e.g. 3, 3,4,5 or 3-5."
            ) from exc
        if not 1 <= start <= end <= 31:
            raise ValueError(
                f"Invalid days of month: {value!r}. Days must be 1-31, ranges low-high."
            )
        days.update(range(start, end + 1))
    return ",".join(str(d) for d in sorted(days))


def _day_set(days_of_month: str) -> set[int]:
    return {int(d) for d in days_of_month.split(",")}


def _slot_time(start_time: Optional[str]) -> time:
    hour, minute = map(int, (start_time or Defaults.DAYS_DEFAULT_START_TIME).split(":"))
    return time(hour, minute)


def _slots(days: set[int], at: time, now: datetime, step: int) -> Iterator[datetime]:
    """Yield slots on matching days, walking forward (step=1) or back (step=-1)."""
    for offset in range(_SCAN_DAYS):
        day = now.date() + timedelta(days=offset * step)
        if day.day in days:
            yield datetime.combine(day, at)


def next_monthly_run(
    days_of_month: str,
    start_time: Optional[str],
    last_run: Optional[datetime],
    now: datetime,
) -> datetime:
    """Return when a days-of-month task should next run.

    Catches up (returns ``now``) only if the task has run before, missed its most
    recent slot, and has no other slot later today.
    """
    days = _day_set(days_of_month)
    at = _slot_time(start_time)
    next_slot = next(s for s in _slots(days, at, now, 1) if s > now)
    prev_slot = next((s for s in _slots(days, at, now, -1) if s <= now), None)

    missed = last_run is not None and prev_slot is not None and last_run < prev_slot
    if missed and next_slot.date() != now.date():
        return now
    return next_slot


def cron_fields(days_of_month: str, start_time: Optional[str]) -> dict:
    """CronTrigger keyword arguments for a days-of-month task."""
    at = _slot_time(start_time)
    return {"day": days_of_month, "hour": at.hour, "minute": at.minute}


def format_days_schedule(days_of_month: str, start_time: Optional[str]) -> str:
    """Human-readable schedule, e.g. "days 3,4,5 at 08:00"."""
    return f"days {days_of_month} at {start_time or Defaults.DAYS_DEFAULT_START_TIME}"

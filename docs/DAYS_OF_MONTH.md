# Days-of-Month Tasks

A task can run once on specific days of the month instead of on an interval. Examples: only on the 3rd, or on the 3rd, 4th and 5th, at 08:00.

## Adding or Editing

Use the interactive prompts: `add.bat` (`python main.py --add`) or `python main.py --edit ID`. After the task name, the "Days of month" prompt appears:

| Input      | Meaning                                    |
|------------|--------------------------------------------|
| `3`        | the 3rd                                    |
| `3,4,5`    | the 3rd, 4th and 5th                       |
| `3-5`      | same as `3,4,5`                            |
| `1,15-17`  | the 1st, 15th, 16th and 17th               |
| Enter      | no days; ask for an interval as usual      |
| `-`        | (edit only) clear the days, back to interval |

In edit mode, Enter keeps the current days. Days must be 1-31; ranges must go low to high. The input is stored sorted, without duplicates (e.g. `5,3,3` is stored as `3,5`).

If you enter days, the interval prompt is skipped. The start-time prompt follows; that is when the task runs on each day. Enter at the start-time prompt means `00:00`.

The `--script` and `--uv-command` command-line options and the bot add/edit wizards cannot set days. The bot does show them.

## When It Runs

- Once per listed day, at the start time.
- Days a month does not have are skipped (`31` does not run in April, `30` does not run in February).

### Missed Runs (scheduler was off)

When the scheduler starts or reloads the task, it runs the task once immediately only if all of these are true:

1. The task has run before. A newly added task never catches up; it waits for its first day.
2. The last run is older than the most recent scheduled slot (a slot was missed).
3. There is no other slot later today.

Examples for `3,4,5` at 08:00:

| Scheduler started    | Last run   | Result                         |
|----------------------|------------|--------------------------------|
| 4th, 07:00           | before 3rd | runs at 08:00 only (no double) |
| 4th, 09:00           | 2nd or earlier | runs once now              |
| 6th                  | before 5th | runs once now                  |
| 5th, 09:00           | 5th, 08:00 | waits for the 3rd next month   |

## Other Commands

| Command                         | Effect on days                       |
|---------------------------------|--------------------------------------|
| `--set-start-time ID HH:MM`     | keeps days, changes the run time     |
| `--rename`, set arguments, copy | keeps days                           |
| `--set-interval ID VALUE`       | clears days, back to interval mode   |
| bot edit with a new interval    | clears days, back to interval mode   |

## Display

`--list`, the status page and the bot task detail show `Schedule: days 3,4,5 at 08:00` instead of the interval. The bot's `/list` tags the task `[days 3,4,5]`.

## Implementation

- Column `days_of_month` (TEXT, e.g. `3,4,5`) in the `tasks` table, added by migration on startup. `NULL` means an interval task.
- The stored `interval` is `1440` for these tasks and is not used for timing. This keeps manual-only (`interval = 0`) logic unaffected.
- `src/month_days.py`: `parse_days_of_month`, `next_monthly_run` (catch-up rule), `cron_fields`, `format_days_schedule`.
- `src/scheduler.py` `_schedule_days_task`: APScheduler `CronTrigger(day=..., hour=..., minute=...)` with `misfire_grace_time=3600` and `coalesce=True`.
- Tests: `tests/test_days_of_month.py`.

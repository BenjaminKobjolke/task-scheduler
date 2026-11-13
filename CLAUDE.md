# Version
3

# Coding Rules (Pointer)

This project's rules live in two files in the project root:

- `CODING_RULES.md` — code quality and conventions. BINDING for all code work in
  this repository, always.
- `IMPLEMENTATION_FLOW.md` — the end-to-end flow to follow when planning and
  implementing a change (checks, gates, Definition of Done).

MANDATORY: Before writing or editing ANY code, you MUST Read BOTH files in full
**in the current session**. Do not rely on memory of a previous session, a
summary, or partial reads.

If you are about to make a code change and have not read both files in this
session: STOP, read them, then continue.

An external tool may orchestrate the implementation itself. When a skill or run
states that the implementation is orchestrated, ignore `IMPLEMENTATION_FLOW.md`
entirely — the orchestrator runs those steps as its own phases. `CODING_RULES.md`
stays binding either way.

Next to `CODING_RULES.md`, apply also writes `CODING_RULES_PLAN.md`,
`CODING_RULES_REVIEW.md` and `CODING_RULES_CODE.md`. When an orchestrator's run
instructions name one of these step files, that file replaces `CODING_RULES.md`
for that run; without such an instruction, `CODING_RULES.md` stays binding in full.

Do not inline rules back into this file and do not use `@import` for either file —
they are intentionally referenced, not imported.


# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Windows task scheduler for Python scripts and batch files. Uses APScheduler for job scheduling and SQLite for persistence.

## Commands

```bash
# Install dependencies
install.bat

# Run scheduler (continuous mode; prompts to take over if one is already running)
python main.py

# Gracefully stop the running scheduler
python main.py --shutdown        # or shutdown.bat
tools\run_tests.bat            # Run the test suite (pytest -v)

# Task management
python main.py --add              # Interactive add
python main.py --list             # List all tasks
python main.py --edit ID          # Edit task
python main.py --delete ID        # Delete task
python main.py --run_id ID        # Run single task
python main.py --history [N]      # Show last N executions (default 10)

# Add task via CLI
python main.py --script "path.py" --name "name" --interval 5 -- --arg1 value
```

## Architecture

- graphify code directory: `.` (repository root, scoped by `.graphifyignore`; covers `main.py` and `src/`).

- `main.py` - Entry point, CLI argument parsing, signal handling
- `src/scheduler.py` - TaskScheduler class wrapping APScheduler's BackgroundScheduler
- `src/database.py` - SQLite persistence for tasks and execution history
- `src/script_runner.py` - Executes Python scripts (with venv/uv support), batch and PowerShell files
- `src/config.py` - Config file handling (config.ini)
- `src/logger.py` - Logging to console and files (logs/scheduler_YYYYMMDD.log)
- `src/status_page.py` - Generates HTML status page

## Key Implementation Details

- Python scripts support two environment types (auto-detected):
  - **uv projects**: Detected by presence of `pyproject.toml` + `uv.lock`, runs via `uv run python script.py`
  - **venv projects**: Must have `venv/` subdirectory, uses `venv/Scripts/python.exe` directly
- Batch files run directly from their directory without venv
- Interactive add: a non-uv directory lists its top-level `.bat`/`.ps1` files to pick from (`cli_input._find_shell_scripts`); this is how Node/other projects get scheduled
- PowerShell `.ps1` files run via `powershell.exe -ExecutionPolicy Bypass -File` from their directory (`shell=False`)
- Tasks persist in `data/tasks.sqlite`
- Single-instance + shutdown handled by `src/instance_controller.py` (`InstanceController`): an OS-level file lock (`data/scheduler.lock`, via `filelock`) enforces one running instance; a stop-request flag file (`data/shutdown.request`) is polled by the main loop each second. `--shutdown` / `shutdown.bat` writes the flag and waits; starting a second instance prompts to take over the running one.
- Shutdown is immediate, not blocking: `TaskScheduler.shutdown()` uses `wait=False` and `main.perform_shutdown()` calls `os._exit(0)` after releasing the lock. This is deliberate — APScheduler worker threads are non-daemon, so a job blocked in `subprocess` would otherwise stall interpreter exit indefinitely (notably the startup burst of coalesced overdue tasks). Already-launched external scripts are separate OS processes and finish independently.
- APScheduler jobs use `misfire_grace_time=60` and `coalesce=True` to handle delayed executions
- Days-of-month tasks (`days_of_month` column, e.g. `"3,4,5"`) use a `CronTrigger` at `start_time` (default 00:00); the stored interval (1440) is unused. Startup catch-up rule lives in `src/month_days.py:next_monthly_run`: run now only if the task has history, missed its last slot, and has no slot later today
- Timestamps stored in local time using SQLite's `datetime('now', 'localtime')`

## Code Analysis

After implementing new features or making significant changes, run the code analysis:

```bash
powershell -Command "cd 'D:\GIT\BenjaminKobjolke\task-scheduler'; cmd /c '.\tools\analyze_code.bat'"
```

To auto-fix issues that Ruff can fix:

```bash
powershell -Command "cd 'D:\GIT\BenjaminKobjolke\task-scheduler'; cmd /c '.\tools\fix_ruff_issues.bat'"
```

Fix any reported issues before committing.

## Bash Tool Rules

- **No compound commands**: Never chain commands with `&&`, `;`, or `||`. Run each command as a separate Bash tool call.
- **No `cd` combined with other commands**: Do not use `cd /path && git commit` or similar. Use separate Bash calls, one for `cd` and one for the command, or pass the directory via the command itself.


# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Windows task scheduler for Python scripts and batch files. Uses APScheduler for job scheduling and SQLite for persistence.

## Commands

```bash
# Install dependencies
install.bat

# Run scheduler (continuous mode)
python main.py

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

- `main.py` - Entry point, CLI argument parsing, signal handling
- `src/scheduler.py` - TaskScheduler class wrapping APScheduler's BackgroundScheduler
- `src/database.py` - SQLite persistence for tasks and execution history
- `src/script_runner.py` - Executes Python scripts (with venv activation) and batch files
- `src/config.py` - Config file handling (config.ini)
- `src/logger.py` - Logging to console and files (logs/scheduler_YYYYMMDD.log)
- `src/status_page.py` - Generates HTML status page

## Key Implementation Details

- Python scripts must have their own `venv/` subdirectory - ScriptRunner activates it automatically
- Batch files run directly from their directory without venv
- Tasks persist in `data/tasks.sqlite`
- APScheduler jobs use `misfire_grace_time=60` and `coalesce=True` to handle delayed executions
- Timestamps stored in local time using SQLite's `datetime('now', 'localtime')`

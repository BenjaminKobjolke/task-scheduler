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
- `src/script_runner.py` - Executes Python scripts (with venv/uv support) and batch files
- `src/config.py` - Config file handling (config.ini)
- `src/logger.py` - Logging to console and files (logs/scheduler_YYYYMMDD.log)
- `src/status_page.py` - Generates HTML status page

## Key Implementation Details

- Python scripts support two environment types (auto-detected):
  - **uv projects**: Detected by presence of `pyproject.toml` + `uv.lock`, runs via `uv run python script.py`
  - **venv projects**: Must have `venv/` subdirectory, uses `venv/Scripts/python.exe` directly
- Batch files run directly from their directory without venv
- Tasks persist in `data/tasks.sqlite`
- APScheduler jobs use `misfire_grace_time=60` and `coalesce=True` to handle delayed executions
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

## Coding Rules Source

Path: `D:\GIT\BenjaminKobjolke\claude-code\coding-rules`

---

## Common Rules (All Languages)

### Use Objects for Related Values

When multiple related values must be passed between classes or methods, bundle them into a
dedicated object (e.g., DTO/Settings/Config) instead of passing many parameters. This improves
readability, reduces call-site churn, and makes changes safer.

### Test-Driven Development for Features and Bug Fixes

Follow TDD when implementing features or fixing bugs:

1. Write tests first
2. Run the tests and confirm they fail
3. Implement the change or fix
4. Run the tests again and confirm they pass

### Prefer Type-Safe Values

Use strong, explicit types instead of loosely typed or stringly typed values (e.g., typed DTOs,
enums, generics, typed settings). This ensures mistakes are caught at compile time or by tests
early in development.

### String Constants

Centralize string constants in a dedicated module/class. Do not scatter raw strings across
the codebase. Use language-appropriate patterns for constants and reuse them consistently.

### README.md is Mandatory

Every project must have a `README.md` file in the root directory. It should include:

- Project name and description
- Installation/setup instructions
- Usage examples
- Dependencies and requirements

### Don't Repeat Yourself (DRY)

Avoid code duplication. If the same logic appears in multiple places, extract it into a
reusable function, class, module, or utility.

- Duplicate code is harder to maintain and leads to bugs
- Extract shared logic into helpers or base abstractions
- Use constants for repeated values

### Confirm Dependency Versions

Before adding any new package or library, confirm the version with the user to ensure we use
up-to-date dependencies.

- Do not assume which version to use
- Ask the user to verify the latest stable version
- Avoid outdated packages that may have security vulnerabilities or missing features

---

## Python Rules

### Use `pyproject.toml` as the single source of truth

No scattered config files. Keep tooling config in `pyproject.toml` (and commit `uv.lock`).

* Python version pinned (e.g. `>=3.11,<3.13`)
* Dependencies managed via `uv add ...`
* Lockfile committed: `uv.lock`

### Enforce formatting + linting + type checking

Minimum toolchain:

```bash
uv add --dev ruff mypy
```

* Ruff handles lint + formatting (replace black/isort/flake8).
* MyPy (or pyright) for typing.
* CI must run: `ruff check`, `ruff format --check`, `mypy`.

### Require type hints on public APIs

* All public functions/classes/methods: typed parameters + return types.
* Use `typing` well: `Sequence`, `Mapping`, `Protocol`, `TypedDict`, `Literal` when helpful.
* Avoid `Any` unless you have a boundary (I/O, third-party libs).

### Centralize configuration with environment-driven settings

No "magic values" in code. Use a single settings module with env overrides.

```py
# app/config/settings.py
from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Settings:
    env: str = os.getenv("APP_ENV", "dev")
    debug: bool = os.getenv("DEBUG", "0") == "1"
    default_lang: str = os.getenv("DEFAULT_LANG", "en")
```

Everything reads from `Settings`, not directly from `os.getenv()` scattered around.

### Tests are mandatory, fast, and isolated

Use pytest:

```bash
uv add --dev pytest
```

* Unit tests for core logic.
* No network in unit tests.
* Use tmp dirs / fixtures; no reliance on developer machine state.
* Run tests in CI on every push.

### Use `spec=` with MagicMock

`MagicMock` without `spec` accepts **any** attribute, even non-existent ones. **Always use `spec=ClassName`** to validate against the real interface:

```python
# BAD - No interface validation
mock = MagicMock()
mock.nonexistent_attribute = "test"  # Silently works

# GOOD - Validates against real class
from unittest.mock import MagicMock
from mylib import EmailMessage

mock = MagicMock(spec=EmailMessage)
mock.nonexistent = "test"  # AttributeError - catches the bug!
```

Quick reference:

```python
from unittest.mock import MagicMock, patch

mock_obj = MagicMock(spec=RealClass)
mock_obj.method_name.return_value = "value"
mock_obj.method_name.side_effect = ValueError("error")

with patch("module.ClassName", spec=RealClass) as mock_cls:
    mock_cls.return_value.method.return_value = "value"
```

### Required Batch Files

Every project must include these batch files:

* `start.bat` - In the root directory, starts the application
* `tools/tests.bat` - Runs the test suite

### Project Setup Scripts

Copy setup batch files from:
`D:\GIT\BenjaminKobjolke\claude-code\prompts\new_project\python_setup_files`

* `install.bat` - Initial project setup (checks uv, creates venv via `uv sync --all-extras`, runs tests)
* `update.bat` - Update all dependencies (`uv lock --upgrade`, sync, lint, test)
* `tools/tests.bat` - Run test suite (`pytest tests/ -v`)

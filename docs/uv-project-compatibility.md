# UV Project Compatibility Guide

This document explains what a uv-managed Python project must have in order to work as a scheduled task.

## Minimum Requirements

The task scheduler checks for two files in the project directory:

1. **`pyproject.toml`** - Project configuration
2. **`uv.lock`** - Dependency lock file (created by `uv lock`)

Without both files, the scheduler rejects the project.

## Task Types

The scheduler supports two ways to run uv projects:

### 1. Script Tasks (`--add` / `--script`)

Runs a Python script inside the project via `uv run python <script>`. No special pyproject.toml setup needed beyond the two files above.

### 2. UV Command Tasks (`--uv-command`)

Runs a named entry point via `uv run <command-name>`. This requires additional configuration in pyproject.toml.

## pyproject.toml Setup for UV Command Tasks

A project that defines a CLI entry point (e.g. `my-tool`) must include three sections beyond the standard `[project]` table:

### Build System

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

Without this, uv cannot install the package and the entry point script is never generated.

### Entry Point Definition

```toml
[project.scripts]
my-tool = "my_module:main"
```

The value follows the format `module:function`. This tells uv which function to call when the command runs.

### Build Target Configuration (flat layout only)

If the project uses a flat layout (e.g. `main.py` at the root instead of a package directory), hatchling needs explicit file selection:

```toml
[tool.hatch.build.targets.wheel]
packages = ["."]
only-include = ["main.py"]
```

For standard package layouts (e.g. `src/my_module/` or `my_module/`), this section is not needed -- hatchling auto-discovers the package.

### Direct Git Dependencies

If any dependency uses a direct git URL:

```toml
dependencies = [
    "some-lib @ git+https://github.com/user/repo.git",
]
```

Add this to allow hatchling to accept it:

```toml
[tool.hatch.metadata]
allow-direct-references = true
```

## Complete Example (flat layout)

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-project"
version = "1.0.0"
requires-python = ">=3.11,<3.13"
dependencies = [
    "requests>=2.0.0",
]

[project.scripts]
my-tool = "main:main"

[tool.hatch.build.targets.wheel]
packages = ["."]
only-include = ["main.py"]
```

## Complete Example (package layout)

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-project"
version = "1.0.0"
requires-python = ">=3.11,<3.13"
dependencies = [
    "requests>=2.0.0",
]

[project.scripts]
my-tool = "my_project.cli:main"
```

## After Updating pyproject.toml

Run `uv sync` in the project directory to install the package and generate the entry point script. Verify with:

```bash
uv run my-tool
```

## Adding the Task

```bash
python main.py --uv-command "D:\path\to\project" "my-tool" --name "My Task" --interval 60
```

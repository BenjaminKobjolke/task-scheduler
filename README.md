# TASK Scheduler

Task Scheduler for Python Scripts and Batch Files is a utility that allows you to schedule Python scripts and batch files to run at specified intervals. It handles virtual environments for Python scripts automatically and persists tasks between restarts.

## Features

- Schedule Python scripts and batch files to run at specified intervals
- **Optional start time** for aligned scheduling (e.g., run every 2 hours starting at 09:00)
- Give descriptive names to scheduled tasks
- Edit existing tasks with updated parameters
- Automatic virtual environment activation for Python scripts (venv and uv projects)
- **Custom uv commands** (e.g., `python -m module_name`) for uv projects (interactive and CLI modes)
- Batch files run directly from their own directory
- Persistent storage of tasks in SQLite database
- Configurable logging system with detailed debugging options
- Graceful shutdown handling
- **Status page generation** (HTML or PHP with authentication)
- **FTP upload** with configurable sync interval
- Configurable output path for status page
- **Hot-reload**: Automatically detects task changes while running (no restart needed)

## Requirements

- Python 3.10 or higher
- Windows operating system
- [uv](https://docs.astral.sh/uv/) package manager
- Each **Python script** must have one of:
  - A `venv` subfolder (traditional virtual environment), OR
  - A `pyproject.toml` + `uv.lock` (uv-managed project, requires `uv` installed)
- Batch files (.bat) can be scheduled without any additional requirements

## Installation

1. Clone this repository
2. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if not already installed
3. Run the installation script:
   ```
   install.bat
   ```
   Or manually:
   ```
   uv sync
   ```

## Usage

### Adding a New Task

There are three ways to add a new task:

#### 1. Interactive Mode

Use the `--add` flag to enter interactive mode, which will guide you through the process:

```bash
python main.py --add
```

This will prompt you for:

- Script path or uv project directory (with validation)
- For uv projects: command selection (predefined or custom)
- Task name
- Interval in minutes
- Start time (optional, HH:MM format for aligned scheduling)
- Arguments (optional, press Enter twice to finish)

**uv Project Commands:**

When you enter a uv project directory, you can either:
1. Select a predefined command from `[project.scripts]` in `pyproject.toml`
2. Enter a custom command (e.g., `python -m module_name`)

Example with predefined commands:
```
Detected uv project! Available commands:
  1. my-command
  2. [Custom command]
Select command [1-2]:
```

Example without predefined commands:
```
Detected uv project! No predefined commands found.
Enter custom command (e.g., python -m module_name): python -m mypackage.main
```

#### 2. Command Line Mode (Script/Batch)

Use the `--script` flag along with other parameters to add a task directly:

```bash
python main.py --script "path/to/script.py" --name "task description" --interval minutes -- script_arguments
```

#### 3. Command Line Mode (uv Command)

Use the `--uv-command` flag to add a uv command task directly from the CLI:

```bash
python main.py --uv-command "PROJECT_DIR" "COMMAND" --name "task name" --interval minutes -- command_arguments
```

- `PROJECT_DIR`: Absolute path to the uv project directory (must contain `pyproject.toml` and `uv.lock`)
- `COMMAND`: The uv command to run (e.g., `sync-to-local`, `python -m mypackage`)

**Examples:**

```bash
# uv command task without arguments
python main.py --uv-command "D:\GIT\my-project" "sync-data" --name "Sync data" --interval 10

# uv command task with arguments
python main.py --uv-command "D:\GIT\my-project" "sync-to-local" --name "Sync to local" --interval 5 -- --config "D:\config\settings.json"

# uv command task with start time
python main.py --uv-command "D:\GIT\my-project" "backup" --name "Scheduled backup" --interval 120 --start-time 09:00
```

#### Parameters

- `--script`: Path to the Python script or batch file to schedule (absolute path or relative to current directory)
- `--uv-command PROJECT_DIR COMMAND`: Add a uv command task (project directory + command name)
- `--name`: Descriptive name for the task (e.g., "convert audio notes to text")
- `--interval`: Interval in minutes between script executions
- `--start-time`: Optional start time for aligned scheduling (HH:MM format)
- `--set-start-time ID TIME`: Set or clear start time for an existing task (use `none` to clear)
- `--set-interval ID MINUTES`: Set interval for an existing task
- `--run_id ID`: Run a specific task immediately by its ID
- `--`: Separator after which all arguments are passed to the script/command
- Arguments after `--` are passed directly to the script/command

#### Examples

```bash
# Simple Python task without arguments
python main.py --script "local_script.py" --name "local task" --interval 1

# Batch file task
python main.py --script "backup.bat" --name "daily backup" --interval 60

# Complex Python task with quoted arguments and paths
python main.py --script "D:\GIT\BenjaminKobjolke\ai-file-renamer\main.py" --name "convert XIDA invoices" --interval 5 -- --source "Z:\Resilio Sync\XIDA_Invoices" --examples "E:\Owncloud\xida\company\GmbH\[--Dokumente--]\[--Rechnungen--]\[--In--]"

# Batch file with arguments
python main.py --script "cleanup.bat" --name "cleanup temp files" --interval 30 -- --force --verbose

# Task with aligned scheduling (runs at 09:00, 11:00, 13:00, etc.)
python main.py --script "backup.py" --name "scheduled backup" --interval 120 --start-time 09:00

# uv command task with arguments
python main.py --uv-command "D:\GIT\my-project" "sync-to-local" --name "Sync to local" --interval 5 -- --config "config.json"
```

Note: When using arguments with spaces or special characters, make sure to:

1. Use `--` to separate scheduler arguments from script arguments
2. Quote values that contain spaces or special characters

### Quick Commands (Batch Files)

For convenience, batch files are provided for common operations:

| Batch File | Description |
|------------|-------------|
| `taskscheduler_run.bat` | Start the scheduler |
| `taskscheduler_list.bat` | List all tasks |
| `taskscheduler_add.bat` | Add a new task (interactive) |
| `taskscheduler_run_with_id.bat ID` | Run a specific task by ID |
| `taskscheduler_remove_with_id.bat ID` | Delete a task by ID |
| `taskscheduler_set_interval.bat ID MINUTES` | Set task interval |
| `taskscheduler_set_start_time.bat ID TIME` | Set task start time |
| `taskscheduler_history.bat` | Show execution history |

### Managing Tasks

#### Listing Tasks

To view all configured tasks without starting the scheduler:

```bash
python main.py --list
```

This will display each task's:

- ID (for use with --delete or --edit)
- Name
- Script path
- Interval
- Start time (if set)
- Arguments
- Next scheduled run time

#### Viewing Execution History

To view recent task executions:

```bash
# Show last 10 executions (default)
python main.py --history

# Show last N executions
python main.py --history 20
```

This will display:

- Execution timestamp (local time)
- Task name
- Success/failure status

#### Running a Single Task

To run a specific task immediately without starting the scheduler:

```bash
python main.py --run_id 5

# Or using batch file
taskscheduler_run_with_id.bat 5
```

#### Editing a Task

To edit an existing task:

```bash
python main.py --edit ID
```

This will:

1. Show the task's current details
2. Enter interactive mode with current values pre-filled
3. Press Enter to keep existing values or enter new ones
4. Update the task with any changes

For example:

```bash
python main.py --edit 1
```

#### Setting Start Time

The start time feature allows you to align task executions to specific time slots. When you set a start time, the task will run at that time and then repeat at the specified interval.

**Example:** With `interval=120` (2 hours) and `start_time=09:00`, the task runs at:
- 09:00, 11:00, 13:00, 15:00, 17:00, etc.

**Quick command to set start time:**

```bash
# Set task 5 to run starting at 09:00
python main.py --set-start-time 5 09:00

# Clear start time (use interval-only behavior)
python main.py --set-start-time 5 none
```

**Batch file for quick access:**

```bash
# Set start time using batch file
taskscheduler_set_start_time.bat 5 09:00
```

**Without start time:** Tasks run immediately when added and then repeat at the interval.

**With start time:** Tasks align to the start_time grid based on the interval.

#### Setting Interval

Quickly change the interval of an existing task:

```bash
# Set task 5 to run every 60 minutes
python main.py --set-interval 5 60

# Using batch file
taskscheduler_set_interval.bat 5 60
```

#### Deleting a Task

To delete a task by its ID:

```bash
python main.py --delete ID
```

This will:

1. Show the task's details
2. Ask for confirmation
3. Delete the task if confirmed

#### Running Tasks

To start the scheduler and run all configured tasks:

```bash
python main.py
```

This will:

1. Load all tasks from the database
2. Display the list of configured tasks
3. Start executing them at their specified intervals

#### Hot-Reload

The scheduler automatically detects database changes every 60 seconds. This means you can:

- Add new tasks while the scheduler is running
- Modify task settings (interval, start_time, etc.)
- Delete tasks

Changes are applied automatically without needing to restart the scheduler.

**Example workflow:**
```bash
# Terminal 1: Start the scheduler
python main.py

# Terminal 2: Modify a task while scheduler is running
python main.py --set-interval 5 30

# The scheduler will detect and apply the change within 60 seconds
# Log output: "Hot-reload: Updated task 'Task Name' (ID: 5)"
```

### Important Notes

1. **Python scripts:** Each Python script must have either:
   - A `venv` subfolder (uses `venv/Scripts/python.exe` directly), OR
   - A `pyproject.toml` + `uv.lock` file (uses `uv run <command>`)

   The scheduler auto-detects the environment type and activates it appropriately.

   For uv projects, you can run predefined commands from `[project.scripts]` or custom commands like `python -m module_name`.
2. **Batch files:** Batch files (.bat) are executed directly from their own directory. No virtual environment is required.
3. Tasks persist between scheduler restarts
4. The scheduler executes scripts in their respective directories

## Logging Configuration

Logging can be configured through both the config.ini file and command-line arguments.

### Config File (config.ini)

```ini
[Logging]
# Logging level: DEBUG, INFO, WARNING, ERROR
level = INFO

# Enable/disable detailed argument logging
detailed_args_logging = false
```

### Command Line Options

Override logging settings temporarily:

```bash
# Set logging level
python main.py --log-level DEBUG

# Enable detailed argument logging
python main.py --detailed-logs true

# Combine both
python main.py --log-level DEBUG --detailed-logs true
```

### Logging Levels

- DEBUG: Show all log messages including detailed debugging information
- INFO: Show general operational messages (default)
- WARNING: Show only warning and error messages
- ERROR: Show only error messages

### Detailed Argument Logging

When enabled (detailed_args_logging = true), shows:

- Original arguments as entered
- JSON format stored in database
- Parsed arguments during task execution

This is particularly useful when debugging issues with argument handling.

### Log Files

Logs are stored in the `logs` directory with the following format:

- File name: `scheduler_YYYYMMDD.log`
- Contains execution details, script output, and any errors
- Log level and detail settings affect what information is included

## Status Page Configuration

The scheduler generates a status page showing recent executions and upcoming tasks.

### Config File (config.ini)

```ini
[StatusPage]
# Output type: html or php (php adds password authentication)
output_type = html

# Output path (relative to project root or absolute path)
output_path = web

# Password for PHP login (only used when output_type = php)
php_password = changeme

# Path to php-simple-login library (only used when output_type = php)
php_login_library_path = D:\GIT\BenjaminKobjolke\php-simple-login
```

### Output Types

- **html**: Simple HTML page (default)
- **php**: HTML wrapped with PHP authentication using [php-simple-login](https://github.com/BenjaminKobjolke/php-simple-login)

## FTP Upload Configuration

Automatically upload the status page to an FTP server.

### Config File (config.ini)

```ini
[FTP]
# Enable automatic FTP sync after status page updates
enabled = false

# FTP server settings
host = ftp.example.com
port = 21
username = your_username
password = your_password
remote_path = /public_html/status

# Connection settings
passive_mode = true
timeout = 30

# Minimum minutes between FTP syncs (0 = sync every time)
sync_interval = 5
```

### Manual FTP Sync

Trigger FTP sync manually:

```bash
python main.py --ftp-sync
```

## Shutdown

To stop the scheduler:

1. Press Ctrl+C in the terminal
2. The scheduler will gracefully shutdown, completing any running scripts

## Error Handling

- If a Python script has neither a `venv` folder nor uv project files (`pyproject.toml` + `uv.lock`), an error will be logged
- If `uv` is not installed but an uv project is detected, the execution will fail with an error
- If a script or batch file fails to execute, it will be logged and the scheduler will continue with the next task
- All errors are logged with full stack traces for debugging

## Project Structure

```
task-scheduler/
├── .claude/commands/        # Claude Code custom slash commands
├── .venv/                   # Project's virtual environment (uv managed)
├── src/
│   ├── __init__.py
│   ├── scheduler.py         # Core scheduling logic
│   ├── script_runner.py     # Script/batch file execution handling
│   ├── database.py          # Task persistence
│   ├── config.py            # Configuration handling
│   ├── constants.py         # Application constants
│   ├── logger.py            # Logging functionality
│   ├── status_page.py       # Status page generation (HTML/PHP)
│   ├── php_login.py         # PHP authentication handling
│   └── ftp_syncer.py        # FTP upload functionality
├── sources/web/templates/   # Status page templates
├── data/                    # Database directory
│   └── tasks.sqlite         # SQLite database for tasks
├── logs/                    # Log files directory
├── web/                     # Generated status page output
├── main.py                  # Entry point
├── config.ini               # Configuration file
├── config.ini.example       # Example configuration
├── pyproject.toml           # Project dependencies (uv)
├── install.bat              # Installation script
├── taskscheduler_run.bat    # Start the scheduler
├── taskscheduler_list.bat   # List all tasks
├── taskscheduler_add.bat    # Add task (interactive)
├── taskscheduler_run_with_id.bat     # Run specific task
├── taskscheduler_remove_with_id.bat  # Delete task
├── taskscheduler_set_interval.bat    # Set task interval
├── taskscheduler_set_start_time.bat  # Set task start time
├── taskscheduler_history.bat         # Show execution history
└── README.md                # This file
```

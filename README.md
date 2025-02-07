# TASC Scheduler

Task Scheduler for Python Scripts (TASC) is a utility that allows you to schedule Python scripts to run at specified intervals. It handles virtual environments for each script automatically and persists tasks between restarts.

## Features

- Schedule Python scripts to run at specified intervals
- Give descriptive names to scheduled tasks
- Automatic virtual environment activation for each script
- Persistent storage of tasks in SQLite database
- Comprehensive logging system
- Graceful shutdown handling

## Requirements

- Python 3.6 or higher
- Windows operating system
- Each script to be scheduled must have its own virtual environment in a `venv` subfolder

## Installation

1. Clone this repository
2. Run the installation script:
   ```
   install.bat
   ```

## Usage

### Adding a New Task

```bash
python main.py --script "path/to/script.py" --name "task description" --arguments "arg1 value1" --interval minutes
```

#### Parameters

- `--script`: Path to the Python script to schedule (absolute path or relative to current directory)
- `--name`: Descriptive name for the task (e.g., "convert audio notes to text")
- `--arguments`: (Optional) Arguments to pass to the script
- `--interval`: Interval in minutes between script executions

#### Example

```bash
# Using absolute path
python main.py --script "D:\GIT\BenjaminKobjolke\audio-to-notes\main.py" --name "convert audio notes to text" --interval 1

# Using relative path (from current directory)
python main.py --script "local_script.py" --name "local task" --interval 1
```

### Managing Tasks

#### Adding a New Task

```bash
python main.py --script "path/to/script.py" --name "task description" --arguments "arg1 value1" --interval minutes
```

#### Listing Tasks

To view all configured tasks without starting the scheduler:

```bash
python main.py --list
```

This will display each task's:

- ID (for use with --delete)
- Name
- Script path
- Interval
- Arguments
- Next scheduled run time

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

### Important Notes

1. Each script must have its own virtual environment in a `venv` subfolder in its directory
2. Tasks persist between scheduler restarts
3. The scheduler will automatically activate the appropriate virtual environment before running each script

## Logging

Logs are stored in the `logs` directory with the following format:

- File name: `scheduler_YYYYMMDD.log`
- Log levels: INFO, WARNING, ERROR
- Contains execution details, script output, and any errors

## Shutdown

To stop the scheduler:

1. Press Ctrl+C in the terminal
2. The scheduler will gracefully shutdown, completing any running scripts

## Error Handling

- If a script's virtual environment is not found, an error will be logged
- If a script fails to execute, it will be logged and the scheduler will continue with the next script
- All errors are logged with full stack traces for debugging

## Project Structure

```
tasc-scheduler/
├── venv/                    # Project's virtual environment
├── src/
│   ├── __init__.py
│   ├── scheduler.py         # Core scheduling logic
│   ├── script_runner.py     # Script execution handling
│   ├── database.py         # Task persistence
│   └── logger.py           # Logging functionality
├── data/                    # Database directory
│   └── tasks.sqlite        # SQLite database for tasks
├── logs/                    # Log files directory
├── main.py                  # Entry point
├── requirements.txt         # Project dependencies
├── install.bat             # Installation script
└── README.md               # This file
```

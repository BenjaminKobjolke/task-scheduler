# PowerShell Script Tasks

The scheduler can run PowerShell scripts (`.ps1`) as tasks, alongside Python scripts and batch files.

## How It Runs

A `.ps1` task is executed from the script's own directory with:

```
powershell.exe -ExecutionPolicy Bypass -File <script>.ps1 [arguments]
```

- `-ExecutionPolicy Bypass` lets the script run without changing the machine-wide execution policy.
- No venv or uv detection is done; the extension alone decides how the file runs.
- The process runs without `shell=True` (unlike `.bat` files), so arguments are passed directly to PowerShell.
- The exit code decides success: `exit 0` = success, anything else = failure in the history.
- Timeout, output logging, interactive prompts, and "launch in new console" behave the same as for batch files.

Windows PowerShell 5.1 (`powershell.exe`) is used. To use PowerShell 7 instead, change `Paths.POWERSHELL_EXE` in `src/constants.py` to `pwsh.exe`.

## Adding a Task

### Interactive (`add.bat` / `--add`)

Enter the `.ps1` path at the `Path:` prompt. Any existing file is accepted as a script task.

### Command Line

```bash
python main.py --script "C:\prosody\renew-certificates.ps1" --name "renew certs" --interval 1d

# With arguments (everything after -- is passed to the script)
python main.py --script "C:\scripts\cleanup.ps1" --name "cleanup" --interval 60 -- -Force -Days 7
```

### XMPP Bot

The bot's add wizard accepts a `.ps1` path the same way as any other script path.

## Implementation

| Location | Purpose |
|----------|---------|
| `src/constants.py` | `Paths.PS1_EXTENSION`, `Paths.POWERSHELL_EXE`, `Paths.POWERSHELL_ARGS` |
| `src/script_runner.py` | `ScriptRunner._shell_script_cmd()` builds the command for `.bat` and `.ps1`; used by `run_script()` and `launch_in_new_console()` |
| `tests/test_script_runner.py` | Command construction + real exit-code tests (Windows only) |
| `tests/test_launch_new_process.py` | New-console launch for `.ps1` |

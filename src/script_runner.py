from __future__ import annotations

import os
import shlex
import subprocess
import threading
from typing import TYPE_CHECKING, List

from .constants import Interactive, Paths
from .logger import Logger
from .script_execution import DEFAULT_TIMEOUT, ScriptExecution
from .script_launcher import ScriptLauncher
from .uv_project_discovery import UvProjectDiscovery

if TYPE_CHECKING:
    from .interaction import InteractionHandler, ScriptOutput


class ScriptRunner:
    """Handles the execution of Python scripts, batch/PowerShell files, and uv CLI commands."""

    def __init__(self):
        """Initialize ScriptRunner with logger."""
        self.logger = Logger("ScriptRunner")
        self._uv_discovery = UvProjectDiscovery(self.logger)
        self._execution = ScriptExecution(self)
        self._launcher = ScriptLauncher(self)

    def _is_uv_project(self, script_dir: str) -> bool:
        """Check if the script directory is a uv-managed project."""
        pyproject_path = os.path.join(script_dir, Paths.PYPROJECT_TOML)
        uv_lock_path = os.path.join(script_dir, Paths.UV_LOCK)
        return os.path.exists(pyproject_path) and os.path.exists(uv_lock_path)

    def _build_env(self, clean_uv: bool = False) -> dict:
        """Copy the process environment and mark scheduled child processes."""
        env = os.environ.copy()
        env[Interactive.ENV_MARKER] = "1"
        if clean_uv:
            env.pop("VIRTUAL_ENV", None)
        return env

    def _run_interactive(
        self,
        cmd: list[str],
        cwd: str,
        env: dict | None,
        shell: bool,
        interaction_handler: InteractionHandler,
        script_output: ScriptOutput | None = None,
    ) -> bool:
        """Run a subprocess with interactive prompt support.

        Reads stdout line-by-line, parses interactive protocol messages,
        and writes responses back to the process's stdin.

        Args:
            cmd: Command to execute
            cwd: Working directory
            env: Environment variables (None for default)
            shell: Whether to use shell execution
            interaction_handler: Handler for interactive prompts
            script_output: Optional output handler for direct console display

        Returns:
            bool: True if process exited with code 0
        """
        from .interaction import InteractionRequest, InteractionType

        def _drain_stderr(
            stream: object,
            output: ScriptOutput | None,
            logger: Logger,
        ) -> None:
            for err_line in iter(stream.readline, ""):
                stripped = err_line.rstrip()
                if output:
                    output.write_line(stripped)
                else:
                    logger.info(stripped)

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd,
                env=env,
                shell=shell,
            )

            stderr_thread = threading.Thread(
                target=_drain_stderr,
                args=(proc.stderr, script_output, self.logger),
                daemon=True,
            )
            stderr_thread.start()

            for line in iter(proc.stdout.readline, ""):
                request = InteractionRequest.parse(line)
                if request:
                    if request.type == InteractionType.OUTPUT:
                        if not request.message:
                            continue
                        if script_output:
                            script_output.write_line(request.message)
                        else:
                            self.logger.info(request.message)
                    else:
                        response = interaction_handler.handle_prompt(request)
                        proc.stdin.write(response.to_json_line() + "\n")
                        proc.stdin.flush()
                elif script_output:
                    script_output.write_line(line.rstrip())
                else:
                    self.logger.info(line.rstrip())

            stderr_thread.join(timeout=5)
            proc.wait(timeout=DEFAULT_TIMEOUT)
            return proc.returncode == 0

        except subprocess.TimeoutExpired:
            self.logger.error(f"Interactive process timed out after {DEFAULT_TIMEOUT}s")
            proc.kill()
            return False
        except Exception as e:
            self.logger.error(f"Error in interactive execution: {str(e)}")
            return False

    def _activate_venv(self, script_path: str) -> str:
        """Get the activation command for the script's virtual environment."""
        script_dir = os.path.dirname(script_path)
        venv_path = os.path.join(script_dir, Paths.VENV_DIR)

        if not os.path.exists(venv_path):
            raise ValueError(f"Virtual environment not found at {venv_path}")

        return os.path.join(venv_path, Paths.SCRIPTS_DIR, Paths.ACTIVATE_SCRIPT)

    def _shell_script_cmd(
        self, script_name: str, arguments: List[str] | None
    ) -> list[str] | None:
        """Build the command for a batch or PowerShell file, or None for Python."""
        ext = os.path.splitext(script_name)[1].lower()
        if ext == Paths.BAT_EXTENSION:
            return [script_name] + (arguments or [])
        if ext == Paths.PS1_EXTENSION:
            return [Paths.POWERSHELL_EXE, *Paths.POWERSHELL_ARGS, script_name] + (
                arguments or []
            )
        return None

    def run_script(
        self,
        script_path: str,
        arguments: List[str] = None,
        interaction_handler: InteractionHandler | None = None,
        script_output: ScriptOutput | None = None,
    ) -> bool:
        """Run a script while preserving the existing public runner API."""
        return self._execution.run_script(
            script_path, arguments, interaction_handler, script_output
        )

    def launch_in_new_console(
        self,
        script_path: str,
        arguments: List[str],
        task_type: str,
        command: str | None,
    ) -> bool:
        """Launch a script or command in a new console window."""
        return self._launcher.launch_in_new_console(
            script_path, arguments, task_type, command
        )

    def get_uv_commands(self, project_dir: str) -> List[str]:
        """Return command names declared in a project's pyproject.toml."""
        return self._uv_discovery.get_commands(project_dir)

    def discover_entry_points(self, project_dir: str) -> list[tuple[str, str]]:
        """Discover likely entry points for a uv project."""
        return self._uv_discovery.discover_entry_points(project_dir)

    def run_uv_command(
        self,
        project_dir: str,
        command: str,
        arguments: List[str] = None,
        interaction_handler: InteractionHandler | None = None,
        script_output: ScriptOutput | None = None,
    ) -> bool:
        """
        Run a uv CLI command (entry point) in a project directory.

        Args:
            project_dir: Path to the uv project directory
            command: The uv command/entry point name
            arguments: List of command line arguments for the command
            interaction_handler: Optional handler for interactive prompts
            script_output: Optional output handler for direct console display

        Returns:
            bool: True if command executed successfully, False otherwise
        """
        if not os.path.isdir(project_dir):
            self.logger.error(f"Project directory not found: {project_dir}")
            return False

        if not self._is_uv_project(project_dir):
            self.logger.error(f"Not a valid uv project: {project_dir}")
            return False

        try:
            # Build the uv run command
            # Use shlex.split to properly handle multi-word commands like "python -m module"
            cmd_parts = shlex.split(command)
            cmd = ["uv", "run"] + cmd_parts + (arguments or [])

            self.logger.info(f"Running uv command: {command} in {project_dir}")

            if self.logger.is_detailed_logging_enabled():
                self.logger.debug(f"Working directory: {project_dir}")
                self.logger.log_arguments(arguments, "uv Command Execution Details")
                self.logger.debug(f"Full command: {' '.join(cmd)}")
            else:
                self.logger.info(
                    f"Arguments: {' '.join(arguments) if arguments else 'None'}"
                )

            if interaction_handler:
                return self._run_interactive(
                    cmd=cmd,
                    cwd=project_dir,
                    env=self._build_env(clean_uv=True),
                    shell=False,
                    interaction_handler=interaction_handler,
                    script_output=script_output,
                )

            try:
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=project_dir,
                    env=self._build_env(clean_uv=True),
                    timeout=DEFAULT_TIMEOUT,
                )
            except subprocess.TimeoutExpired:
                self.logger.error(
                    f"Command timed out after {DEFAULT_TIMEOUT}s: {command}"
                )
                return False

            if process.stdout:
                self.logger.info(f"Command output:\n{process.stdout}")
            if process.stderr:
                self.logger.info(f"Command stderr output:\n{process.stderr}")

            return process.returncode == 0

        except Exception as e:
            self.logger.error(f"Error running uv command {command}: {str(e)}")
            return False

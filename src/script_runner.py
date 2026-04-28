from __future__ import annotations

import os
import shlex
import subprocess
import threading
import tomllib
from typing import TYPE_CHECKING, List

from .constants import Discovery, Interactive, Paths
from .logger import Logger

if TYPE_CHECKING:
    from .interaction import InteractionHandler, ScriptOutput

# Default timeout for script execution (30 minutes)
DEFAULT_TIMEOUT = 1800


class ScriptRunner:
    """Handles the execution of Python scripts, batch files, and uv CLI commands."""

    def __init__(self):
        """Initialize ScriptRunner with logger."""
        self.logger = Logger("ScriptRunner")

    def _is_uv_project(self, script_dir: str) -> bool:
        """Check if the script directory is a uv-managed project."""
        pyproject_path = os.path.join(script_dir, Paths.PYPROJECT_TOML)
        uv_lock_path = os.path.join(script_dir, Paths.UV_LOCK)
        return os.path.exists(pyproject_path) and os.path.exists(uv_lock_path)

    def _build_env(self, clean_uv: bool = False) -> dict:
        """Build environment for subprocess execution.

        Sets the INTERACTIVE marker so child scripts can detect
        they are running under the scheduler. Optionally removes
        VIRTUAL_ENV for uv-managed projects.

        Args:
            clean_uv: If True, remove VIRTUAL_ENV from the environment.

        Returns:
            A copy of os.environ with modifications applied.
        """
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

    def run_script(
        self,
        script_path: str,
        arguments: List[str] = None,
        interaction_handler: InteractionHandler | None = None,
        script_output: ScriptOutput | None = None,
    ) -> bool:
        """
        Run a Python script with its virtual environment or a batch file.

        Args:
            script_path: Path to the Python script or batch file
            arguments: List of command line arguments for the script
            interaction_handler: Optional handler for interactive prompts
            script_output: Optional output handler for direct console display

        Returns:
            bool: True if script executed successfully, False otherwise
        """
        if not os.path.exists(script_path):
            self.logger.error(f"Script not found: {script_path}")
            return False

        # Determine if it's a batch file or Python script
        _, ext = os.path.splitext(script_path)
        is_batch = ext.lower() == Paths.BAT_EXTENSION

        try:
            # Get script directory and name
            script_dir = os.path.dirname(os.path.abspath(script_path))
            script_name = os.path.basename(script_path)

            if is_batch:
                # For batch files, run directly in their directory
                cmd = [script_name] + (arguments or [])

                # Log execution details
                self.logger.info(f"Running batch file: {script_path}")

                if self.logger.is_detailed_logging_enabled():
                    self.logger.debug(f"Working directory: {script_dir}")
                    self.logger.log_arguments(arguments, "Batch File Execution Details")
                    self.logger.debug(f"Full command: {' '.join(cmd)}")
                else:
                    # Basic logging when detailed logging is disabled
                    self.logger.info(
                        f"Arguments: {' '.join(arguments) if arguments else 'None'}"
                    )

                # Run the batch file in its directory
                if interaction_handler:
                    return self._run_interactive(
                        cmd=cmd,
                        cwd=script_dir,
                        env=self._build_env(),
                        shell=True,
                        interaction_handler=interaction_handler,
                        script_output=script_output,
                    )
                try:
                    process = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        cwd=script_dir,
                        shell=True,
                        env=self._build_env(),
                        timeout=DEFAULT_TIMEOUT,
                    )
                except subprocess.TimeoutExpired:
                    self.logger.error(
                        f"Batch file timed out after {DEFAULT_TIMEOUT}s: {script_path}"
                    )
                    return False
            elif self._is_uv_project(script_dir):
                # For uv-managed projects, use uv run
                python_cmd = ["uv", "run", "python", script_name] + (arguments or [])

                # Log execution details based on configuration
                self.logger.info(f"Running script with uv: {script_path}")

                if self.logger.is_detailed_logging_enabled():
                    self.logger.debug(f"Working directory: {script_dir}")
                    self.logger.log_arguments(arguments, "uv Script Execution Details")
                    self.logger.debug(f"Full command: {' '.join(python_cmd)}")
                else:
                    # Basic logging when detailed logging is disabled
                    self.logger.info(
                        f"Arguments: {' '.join(arguments) if arguments else 'None'}"
                    )

                # Run the script using uv
                if interaction_handler:
                    return self._run_interactive(
                        cmd=python_cmd,
                        cwd=script_dir,
                        env=self._build_env(clean_uv=True),
                        shell=False,
                        interaction_handler=interaction_handler,
                        script_output=script_output,
                    )
                try:
                    process = subprocess.run(
                        python_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        cwd=script_dir,
                        env=self._build_env(clean_uv=True),
                        timeout=DEFAULT_TIMEOUT,
                    )
                except subprocess.TimeoutExpired:
                    self.logger.error(
                        f"Script timed out after {DEFAULT_TIMEOUT}s: {script_path}"
                    )
                    return False
            else:
                # For Python scripts with traditional venv
                venv_activate = self._activate_venv(script_path)

                # Get the Python executable from the virtual environment
                venv_python = os.path.join(
                    os.path.dirname(venv_activate), Paths.PYTHON_EXE
                )

                # Build the command using venv's Python
                python_cmd = [venv_python, script_name] + (arguments or [])

                # Log execution details based on configuration
                self.logger.info(f"Running script: {script_path}")

                if self.logger.is_detailed_logging_enabled():
                    self.logger.debug(f"Working directory: {script_dir}")
                    self.logger.log_arguments(arguments, "Script Execution Details")
                    self.logger.debug(f"Full command: {' '.join(python_cmd)}")
                else:
                    # Basic logging when detailed logging is disabled
                    self.logger.info(
                        f"Arguments: {' '.join(arguments) if arguments else 'None'}"
                    )

                # Run the script in the correct directory
                if interaction_handler:
                    return self._run_interactive(
                        cmd=python_cmd,
                        cwd=script_dir,
                        env=self._build_env(),
                        shell=False,
                        interaction_handler=interaction_handler,
                        script_output=script_output,
                    )
                try:
                    process = subprocess.run(
                        python_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        cwd=script_dir,
                        env=self._build_env(),
                        timeout=DEFAULT_TIMEOUT,
                    )
                except subprocess.TimeoutExpired:
                    self.logger.error(
                        f"Script timed out after {DEFAULT_TIMEOUT}s: {script_path}"
                    )
                    return False

            if process.stdout:
                self.logger.info(f"Script output:\n{process.stdout}")
            if process.stderr:
                # Log stderr as info since it might contain warnings that aren't errors
                self.logger.info(f"Script stderr output:\n{process.stderr}")

            # Return True if the process completed successfully (exit code 0)
            return process.returncode == 0

        except Exception as e:
            self.logger.error(f"Error running script {script_path}: {str(e)}")
            return False

    def launch_in_new_console(
        self,
        script_path: str,
        arguments: List[str],
        task_type: str,
        command: str | None,
    ) -> bool:
        """Launch a script or command in a new console window (non-blocking).

        Args:
            script_path: Path to the script or project directory.
            arguments: Arguments for the script/command.
            task_type: Type of task ('script' or 'uv_command').
            command: Command name for uv_command tasks.

        Returns:
            bool: True if launch succeeded, False otherwise.
        """
        try:
            if task_type == "uv_command" and command:
                # uv command
                cmd_parts = shlex.split(command)
                cmd = ["uv", "run"] + cmd_parts + (arguments or [])
                cwd = script_path
                env = self._build_env(clean_uv=True)
                self.logger.info(
                    f"Launching uv command in new console: {command} in {script_path}"
                )
            else:
                _, ext = os.path.splitext(script_path)
                is_batch = ext.lower() == Paths.BAT_EXTENSION
                script_dir = os.path.dirname(os.path.abspath(script_path))
                script_name = os.path.basename(script_path)

                if is_batch:
                    cmd = [script_name] + (arguments or [])
                    cwd = script_dir
                    env = self._build_env()
                    self.logger.info(
                        f"Launching batch file in new console: {script_path}"
                    )
                elif self._is_uv_project(script_dir):
                    cmd = ["uv", "run", "python", script_name] + (arguments or [])
                    cwd = script_dir
                    env = self._build_env(clean_uv=True)
                    self.logger.info(
                        f"Launching uv script in new console: {script_path}"
                    )
                else:
                    venv_activate = self._activate_venv(script_path)
                    venv_python = os.path.join(
                        os.path.dirname(venv_activate), Paths.PYTHON_EXE
                    )
                    cmd = [venv_python, script_name] + (arguments or [])
                    cwd = script_dir
                    env = self._build_env()
                    self.logger.info(
                        f"Launching script in new console: {script_path}"
                    )

            subprocess.Popen(
                cmd,
                cwd=cwd,
                env=env,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            self.logger.info("Process launched in new console window")
            return True

        except Exception as e:
            self.logger.error(f"Error launching in new console: {str(e)}")
            return False

    def get_uv_commands(self, project_dir: str) -> List[str]:
        """
        Get available uv CLI commands from a project's pyproject.toml.

        Args:
            project_dir: Path to the uv project directory

        Returns:
            List of command names defined in [project.scripts]
        """
        pyproject_path = os.path.join(project_dir, Paths.PYPROJECT_TOML)

        if not os.path.exists(pyproject_path):
            return []

        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
            return list(data.get("project", {}).get("scripts", {}).keys())
        except Exception as e:
            self.logger.error(f"Error reading pyproject.toml: {str(e)}")
            return []

    def discover_entry_points(self, project_dir: str) -> list[tuple[str, str]]:
        """
        Discover likely entry points for a uv project.

        Scans for common entry points and returns them as selectable options.

        Args:
            project_dir: Path to the uv project directory

        Returns:
            List of (command_string, description) tuples
        """
        entries: list[tuple[str, str]] = []
        seen_commands: set[str] = set()

        pyproject_data: dict = {}
        pyproject_path = os.path.join(project_dir, Paths.PYPROJECT_TOML)
        if os.path.exists(pyproject_path):
            try:
                with open(pyproject_path, "rb") as f:
                    pyproject_data = tomllib.load(f)
            except Exception:
                pyproject_data = {}

        # 1. Project name from pyproject.toml
        project_name = pyproject_data.get("project", {}).get("name", "")
        if project_name:
            module_name = project_name.replace("-", "_")
            pkg_dir = os.path.join(project_dir, module_name)
            init_path = os.path.join(pkg_dir, Paths.INIT_PY)
            if os.path.isdir(pkg_dir) and os.path.exists(init_path):
                cmd = f"python -m {module_name}"
                if cmd not in seen_commands:
                    entries.append((cmd, Discovery.DESC_PROJECT_MODULE))
                    seen_commands.add(cmd)
                main_module = os.path.join(pkg_dir, Paths.PACKAGE_MAIN_MODULE)
                if os.path.exists(main_module):
                    main_cmd = f"python -m {module_name}.main"
                    if main_cmd not in seen_commands:
                        entries.append((main_cmd, Discovery.DESC_PACKAGE_MAIN_MODULE))
                        seen_commands.add(main_cmd)

        # 2. Build-config-declared packages (e.g. hatch, setuptools)
        for declared in self._declared_packages(pyproject_data):
            self._add_package_entries(
                project_dir,
                declared,
                seen_commands,
                entries,
                main_desc=Discovery.DESC_DECLARED_MAIN_MODULE,
                package_main_desc=Discovery.DESC_DECLARED_PACKAGE_MAIN,
            )

        # 3. Root-level entry files
        for filename in Discovery.ROOT_ENTRY_FILES:
            filepath = os.path.join(project_dir, filename)
            if os.path.isfile(filepath):
                cmd = f"python {filename}"
                if cmd not in seen_commands:
                    entries.append((cmd, Discovery.DESC_ROOT_FILE))
                    seen_commands.add(cmd)

        # 4. Subdir scan: packages with __main__.py or main.py
        try:
            for entry in os.listdir(project_dir):
                entry_path = os.path.join(project_dir, entry)
                if not os.path.isdir(entry_path):
                    continue
                if entry.startswith("."):
                    continue
                if entry in Discovery.EXCLUDED_DIRS:
                    continue
                self._add_package_entries(
                    project_dir,
                    entry,
                    seen_commands,
                    entries,
                    main_desc=Discovery.DESC_MAIN_MODULE,
                    package_main_desc=Discovery.DESC_PACKAGE_MAIN_MODULE,
                )
        except OSError:
            pass

        return entries

    def _declared_packages(self, pyproject_data: dict) -> list[str]:
        """
        Collect top-level package names declared by build backends.

        Reads:
            - [tool.hatch.build.targets.wheel].packages
            - [tool.setuptools].packages (simple list form)
            - [tool.setuptools.packages.find].include (literal entries only)

        Skips nested package paths (containing '/', '\\' or '.').
        """
        names: list[str] = []
        seen: set[str] = set()

        def add(value: object) -> None:
            if not isinstance(value, str):
                return
            name = value.strip()
            if not name:
                return
            if "/" in name or "\\" in name or "." in name:
                return
            if name in Discovery.EXCLUDED_DIRS:
                return
            if name in seen:
                return
            seen.add(name)
            names.append(name)

        tool = pyproject_data.get("tool", {})
        if not isinstance(tool, dict):
            return names

        hatch_pkgs = (
            tool.get("hatch", {})
            .get("build", {})
            .get("targets", {})
            .get("wheel", {})
            .get("packages")
        )
        if isinstance(hatch_pkgs, list):
            for pkg in hatch_pkgs:
                add(pkg)

        setuptools = tool.get("setuptools", {})
        if isinstance(setuptools, dict):
            packages = setuptools.get("packages")
            if isinstance(packages, list):
                for pkg in packages:
                    add(pkg)
            elif isinstance(packages, dict):
                find = packages.get("find", {})
                if isinstance(find, dict):
                    include = find.get("include", [])
                    if isinstance(include, list):
                        for pkg in include:
                            if isinstance(pkg, str) and "*" not in pkg:
                                add(pkg)

        return names

    def _add_package_entries(
        self,
        project_dir: str,
        package_name: str,
        seen_commands: set[str],
        entries: list[tuple[str, str]],
        *,
        main_desc: str,
        package_main_desc: str,
    ) -> None:
        """
        Append `python -m <pkg>` and/or `python -m <pkg>.main` candidates
        based on which entry-point files exist under <project_dir>/<package_name>/.
        """
        pkg_dir = os.path.join(project_dir, package_name)
        if not os.path.isdir(pkg_dir):
            return

        if os.path.exists(os.path.join(pkg_dir, Paths.MAIN_PY)):
            cmd = f"python -m {package_name}"
            if cmd not in seen_commands:
                entries.append((cmd, main_desc))
                seen_commands.add(cmd)

        if os.path.exists(os.path.join(pkg_dir, Paths.PACKAGE_MAIN_MODULE)):
            cmd = f"python -m {package_name}.main"
            if cmd not in seen_commands:
                entries.append((cmd, package_main_desc))
                seen_commands.add(cmd)

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

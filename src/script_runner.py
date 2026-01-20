import os
import shlex
import subprocess
import tomllib
from typing import List, Optional
from .logger import Logger
from .constants import Paths

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

    def _get_clean_env_for_uv(self) -> dict:
        """Get environment without VIRTUAL_ENV for uv execution."""
        env = os.environ.copy()
        env.pop('VIRTUAL_ENV', None)
        return env

    def _activate_venv(self, script_path: str) -> str:
        """Get the activation command for the script's virtual environment."""
        script_dir = os.path.dirname(script_path)
        venv_path = os.path.join(script_dir, Paths.VENV_DIR)

        if not os.path.exists(venv_path):
            raise ValueError(f"Virtual environment not found at {venv_path}")

        return os.path.join(venv_path, Paths.SCRIPTS_DIR, Paths.ACTIVATE_SCRIPT)
    
    def run_script(self, script_path: str, arguments: List[str] = None) -> bool:
        """
        Run a Python script with its virtual environment or a batch file.

        Args:
            script_path: Path to the Python script or batch file
            arguments: List of command line arguments for the script

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
                    self.logger.info(f"Arguments: {' '.join(arguments) if arguments else 'None'}")

                # Run the batch file in its directory
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=script_dir,
                    shell=True
                )
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
                    self.logger.info(f"Arguments: {' '.join(arguments) if arguments else 'None'}")

                # Run the script using uv
                process = subprocess.run(
                    python_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=script_dir,
                    env=self._get_clean_env_for_uv()
                )
            else:
                # For Python scripts with traditional venv
                venv_activate = self._activate_venv(script_path)

                # Get the Python executable from the virtual environment
                venv_python = os.path.join(os.path.dirname(venv_activate), Paths.PYTHON_EXE)

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
                    self.logger.info(f"Arguments: {' '.join(arguments) if arguments else 'None'}")

                # Run the script in the correct directory
                process = subprocess.run(
                    python_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=script_dir
                )

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

    def run_uv_command(self, project_dir: str, command: str, arguments: List[str] = None) -> bool:
        """
        Run a uv CLI command (entry point) in a project directory.

        Args:
            project_dir: Path to the uv project directory
            command: The uv command/entry point name
            arguments: List of command line arguments for the command

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
                self.logger.info(f"Arguments: {' '.join(arguments) if arguments else 'None'}")

            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=project_dir,
                env=self._get_clean_env_for_uv()
            )

            if process.stdout:
                self.logger.info(f"Command output:\n{process.stdout}")
            if process.stderr:
                self.logger.info(f"Command stderr output:\n{process.stderr}")

            return process.returncode == 0

        except Exception as e:
            self.logger.error(f"Error running uv command {command}: {str(e)}")
            return False

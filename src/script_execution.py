"""Execute scripts and launch them in separate console windows."""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING, List

from .constants import Paths

if TYPE_CHECKING:
    from .interaction import InteractionHandler, ScriptOutput
    from .script_runner import ScriptRunner

DEFAULT_TIMEOUT = 1800


class ScriptExecution:
    """Own subprocess execution while ScriptRunner keeps its public API."""

    def __init__(self, runner: ScriptRunner):
        self._runner = runner

    def run_script(
        self,
        script_path: str,
        arguments: List[str] = None,
        interaction_handler: InteractionHandler | None = None,
        script_output: ScriptOutput | None = None,
    ) -> bool:
        """

        Run a Python script with its virtual environment, or a batch/PowerShell file.



        Args:

            script_path: Path to the Python script, batch or PowerShell file

            arguments: List of command line arguments for the script

            interaction_handler: Optional handler for interactive prompts

            script_output: Optional output handler for direct console display



        Returns:

            bool: True if script executed successfully, False otherwise

        """

        if not os.path.exists(script_path):
            self._runner.logger.error(f"Script not found: {script_path}")

            return False

        try:
            # Get script directory and name

            script_dir = os.path.dirname(os.path.abspath(script_path))

            script_name = os.path.basename(script_path)

            # Batch/PowerShell files get a direct command; Python scripts get None

            cmd = self._runner._shell_script_cmd(script_name, arguments)

            is_batch = os.path.splitext(script_name)[1].lower() == Paths.BAT_EXTENSION

            if cmd:
                # For batch/PowerShell files, run directly in their directory

                # Log execution details

                self._runner.logger.info(f"Running script file: {script_path}")

                if self._runner.logger.is_detailed_logging_enabled():
                    self._runner.logger.debug(f"Working directory: {script_dir}")

                    self._runner.logger.log_arguments(
                        arguments, "Script File Execution Details"
                    )

                    self._runner.logger.debug(f"Full command: {' '.join(cmd)}")

                else:
                    # Basic logging when detailed logging is disabled

                    self._runner.logger.info(
                        f"Arguments: {' '.join(arguments) if arguments else 'None'}"
                    )

                # Run the batch file in its directory

                if interaction_handler:
                    return self._runner._run_interactive(
                        cmd=cmd,
                        cwd=script_dir,
                        env=self._runner._build_env(),
                        shell=is_batch,
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
                        shell=is_batch,
                        env=self._runner._build_env(),
                        timeout=DEFAULT_TIMEOUT,
                    )

                except subprocess.TimeoutExpired:
                    self._runner.logger.error(
                        f"Script file timed out after {DEFAULT_TIMEOUT}s: {script_path}"
                    )

                    return False

            elif self._runner._is_uv_project(script_dir):
                # For uv-managed projects, use uv run

                python_cmd = ["uv", "run", "python", script_name] + (arguments or [])

                # Log execution details based on configuration

                self._runner.logger.info(f"Running script with uv: {script_path}")

                if self._runner.logger.is_detailed_logging_enabled():
                    self._runner.logger.debug(f"Working directory: {script_dir}")

                    self._runner.logger.log_arguments(
                        arguments, "uv Script Execution Details"
                    )

                    self._runner.logger.debug(f"Full command: {' '.join(python_cmd)}")

                else:
                    # Basic logging when detailed logging is disabled

                    self._runner.logger.info(
                        f"Arguments: {' '.join(arguments) if arguments else 'None'}"
                    )

                # Run the script using uv

                if interaction_handler:
                    return self._runner._run_interactive(
                        cmd=python_cmd,
                        cwd=script_dir,
                        env=self._runner._build_env(clean_uv=True),
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
                        env=self._runner._build_env(clean_uv=True),
                        timeout=DEFAULT_TIMEOUT,
                    )

                except subprocess.TimeoutExpired:
                    self._runner.logger.error(
                        f"Script timed out after {DEFAULT_TIMEOUT}s: {script_path}"
                    )

                    return False

            else:
                # For Python scripts with traditional venv

                venv_activate = self._runner._activate_venv(script_path)

                # Get the Python executable from the virtual environment

                venv_python = os.path.join(
                    os.path.dirname(venv_activate), Paths.PYTHON_EXE
                )

                # Build the command using venv's Python

                python_cmd = [venv_python, script_name] + (arguments or [])

                # Log execution details based on configuration

                self._runner.logger.info(f"Running script: {script_path}")

                if self._runner.logger.is_detailed_logging_enabled():
                    self._runner.logger.debug(f"Working directory: {script_dir}")

                    self._runner.logger.log_arguments(
                        arguments, "Script Execution Details"
                    )

                    self._runner.logger.debug(f"Full command: {' '.join(python_cmd)}")

                else:
                    # Basic logging when detailed logging is disabled

                    self._runner.logger.info(
                        f"Arguments: {' '.join(arguments) if arguments else 'None'}"
                    )

                # Run the script in the correct directory

                if interaction_handler:
                    return self._runner._run_interactive(
                        cmd=python_cmd,
                        cwd=script_dir,
                        env=self._runner._build_env(),
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
                        env=self._runner._build_env(),
                        timeout=DEFAULT_TIMEOUT,
                    )

                except subprocess.TimeoutExpired:
                    self._runner.logger.error(
                        f"Script timed out after {DEFAULT_TIMEOUT}s: {script_path}"
                    )

                    return False

            if process.stdout:
                self._runner.logger.info(f"Script output:\n{process.stdout}")

            if process.stderr:
                # Log stderr as info since it might contain warnings that aren't errors

                self._runner.logger.info(f"Script stderr output:\n{process.stderr}")

            # Return True if the process completed successfully (exit code 0)

            return process.returncode == 0

        except Exception as e:
            self._runner.logger.error(f"Error running script {script_path}: {str(e)}")

            return False

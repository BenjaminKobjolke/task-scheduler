import os
import subprocess
from typing import List, Optional
from .logger import Logger

class ScriptRunner:
    """Handles the execution of Python scripts with their virtual environments."""
    
    def __init__(self):
        """Initialize ScriptRunner with logger."""
        self.logger = Logger("ScriptRunner")
    
    def _is_uv_project(self, script_dir: str) -> bool:
        """Check if the script directory is a uv-managed project."""
        pyproject_path = os.path.join(script_dir, "pyproject.toml")
        uv_lock_path = os.path.join(script_dir, "uv.lock")
        return os.path.exists(pyproject_path) and os.path.exists(uv_lock_path)

    def _activate_venv(self, script_path: str) -> str:
        """Get the activation command for the script's virtual environment."""
        script_dir = os.path.dirname(script_path)
        venv_path = os.path.join(script_dir, "venv")

        if not os.path.exists(venv_path):
            raise ValueError(f"Virtual environment not found at {venv_path}")

        return os.path.join(venv_path, "Scripts", "activate")
    
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
        is_batch = ext.lower() == '.bat'

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
                    self.logger.debug("=== Batch File Execution Details ===")
                    self.logger.debug(f"Working directory: {script_dir}")
                    self.logger.debug("Arguments (as stored):")
                    if arguments:
                        for i, arg in enumerate(arguments):
                            self.logger.debug(f"  {i+1}. [{arg}]")
                    else:
                        self.logger.debug("  No arguments")
                    self.logger.debug(f"Full command: {' '.join(cmd)}")
                    self.logger.debug("====================================")
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
                    self.logger.debug("=== uv Script Execution Details ===")
                    self.logger.debug(f"Working directory: {script_dir}")
                    self.logger.debug("Arguments (as stored):")
                    if arguments:
                        for i, arg in enumerate(arguments):
                            self.logger.debug(f"  {i+1}. [{arg}]")
                    else:
                        self.logger.debug("  No arguments")
                    self.logger.debug(f"Full command: {' '.join(python_cmd)}")
                    self.logger.debug("====================================")
                else:
                    # Basic logging when detailed logging is disabled
                    self.logger.info(f"Arguments: {' '.join(arguments) if arguments else 'None'}")

                # Run the script using uv
                process = subprocess.run(
                    python_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=script_dir
                )
            else:
                # For Python scripts with traditional venv
                venv_activate = self._activate_venv(script_path)

                # Get the Python executable from the virtual environment
                venv_python = os.path.join(os.path.dirname(venv_activate), "python.exe")

                # Build the command using venv's Python
                python_cmd = [venv_python, script_name] + (arguments or [])

                # Log execution details based on configuration
                self.logger.info(f"Running script: {script_path}")

                if self.logger.is_detailed_logging_enabled():
                    self.logger.debug("=== Script Execution Details ===")
                    self.logger.debug(f"Working directory: {script_dir}")
                    self.logger.debug("Arguments (as stored):")
                    if arguments:
                        for i, arg in enumerate(arguments):
                            self.logger.debug(f"  {i+1}. [{arg}]")
                    else:
                        self.logger.debug("  No arguments")
                    self.logger.debug(f"Full command: {' '.join(python_cmd)}")
                    self.logger.debug("============================")
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

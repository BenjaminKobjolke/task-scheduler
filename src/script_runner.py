import os
import subprocess
from typing import List, Optional
from .logger import Logger

class ScriptRunner:
    """Handles the execution of Python scripts with their virtual environments."""
    
    def __init__(self):
        """Initialize ScriptRunner with logger."""
        self.logger = Logger("ScriptRunner")
    
    def _activate_venv(self, script_path: str) -> str:
        """Get the activation command for the script's virtual environment."""
        script_dir = os.path.dirname(script_path)
        venv_path = os.path.join(script_dir, "venv")
        
        if not os.path.exists(venv_path):
            raise ValueError(f"Virtual environment not found at {venv_path}")
        
        return os.path.join(venv_path, "Scripts", "activate")
    
    def run_script(self, script_path: str, arguments: List[str] = None) -> bool:
        """
        Run a Python script with its virtual environment.
        
        Args:
            script_path: Path to the Python script
            arguments: List of command line arguments for the script
            
        Returns:
            bool: True if script executed successfully, False otherwise
        """
        if not os.path.exists(script_path):
            self.logger.error(f"Script not found: {script_path}")
            return False
            
        try:
            venv_activate = self._activate_venv(script_path)
            
            # Get script directory and name
            script_dir = os.path.dirname(os.path.abspath(script_path))
            script_name = os.path.basename(script_path)
            
            # Get the Python executable from the virtual environment
            venv_python = os.path.join(os.path.dirname(venv_activate), "python.exe")
            
            # Build the command using venv's Python
            python_cmd = [venv_python, script_name] + (arguments or [])
            
            self.logger.info(f"Working directory: {script_dir}")
            self.logger.info(f"Running script: {script_path}")
            self.logger.info(f"Arguments: {arguments if arguments else 'None'}")
            self.logger.info(f"Command: {' '.join(python_cmd)}")
            
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

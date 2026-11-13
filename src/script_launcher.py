"""Launch scheduler scripts in a new console window."""

from __future__ import annotations

import os
import shlex
import subprocess
from typing import TYPE_CHECKING, List

from .constants import Paths

if TYPE_CHECKING:
    from .script_runner import ScriptRunner


class ScriptLauncher:
    """Launch script and uv command tasks without waiting for completion."""

    def __init__(self, runner: ScriptRunner):
        self._runner = runner

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

                env = self._runner._build_env(clean_uv=True)

                self._runner.logger.info(
                    f"Launching uv command in new console: {command} in {script_path}"
                )

            else:
                script_dir = os.path.dirname(os.path.abspath(script_path))

                script_name = os.path.basename(script_path)

                shell_cmd = self._runner._shell_script_cmd(script_name, arguments)

                if shell_cmd:
                    cmd = shell_cmd

                    cwd = script_dir

                    env = self._runner._build_env()

                    self._runner.logger.info(
                        f"Launching script file in new console: {script_path}"
                    )

                elif self._runner._is_uv_project(script_dir):
                    cmd = ["uv", "run", "python", script_name] + (arguments or [])

                    cwd = script_dir

                    env = self._runner._build_env(clean_uv=True)

                    self._runner.logger.info(
                        f"Launching uv script in new console: {script_path}"
                    )

                else:
                    venv_activate = self._runner._activate_venv(script_path)

                    venv_python = os.path.join(
                        os.path.dirname(venv_activate), Paths.PYTHON_EXE
                    )

                    cmd = [venv_python, script_name] + (arguments or [])

                    cwd = script_dir

                    env = self._runner._build_env()

                    self._runner.logger.info(
                        f"Launching script in new console: {script_path}"
                    )

            subprocess.Popen(
                cmd,
                cwd=cwd,
                env=env,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )

            self._runner.logger.info("Process launched in new console window")

            return True

        except Exception as e:
            self._runner.logger.error(f"Error launching in new console: {str(e)}")

            return False

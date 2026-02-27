import os
import shutil
from typing import Dict, List, Optional
from datetime import datetime
from .logger import Logger
from .config import Config
from .constants import Defaults, TaskTypes
from .php_login import PhpLoginHandler
from .ftp_syncer import FtpSyncer


class StatusPage:
    """Handles the generation and updating of the status web page."""

    def __init__(self):
        """Initialize the status page handler."""
        self.logger = Logger("StatusPage")
        self.config = Config()
        self.php_handler = PhpLoginHandler()
        self.ftp_syncer = FtpSyncer()
        self._last_ftp_sync = None  # Track last FTP sync time for throttling

        self.script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.template_path = os.path.join(
            self.script_dir, "sources", "web", "templates", "index.html"
        )

        # Get output path from config (can be relative or absolute)
        self._update_output_paths()

        # Copy static files and set up PHP if needed
        self._setup_output_directory()

    def _update_output_paths(self):
        """Update output paths based on config."""
        output_path_config = self.config.get_output_path()
        output_type = self.config.get_output_type()

        # Determine output directory (relative or absolute)
        if os.path.isabs(output_path_config):
            self.output_dir = output_path_config
        else:
            self.output_dir = os.path.join(self.script_dir, output_path_config)

        # Determine file extension based on output type
        extension = ".php" if output_type == "php" else ".html"
        self.output_path = os.path.join(self.output_dir, f"index{extension}")

    def _setup_output_directory(self):
        """Set up output directory with static files and PHP if needed."""
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

        # Copy static files
        self._copy_static_files()

        # Set up PHP login if output type is PHP
        if self.config.get_output_type() == "php":
            self.php_handler.setup_php_login(self.output_dir)

    def _copy_static_files(self):
        """Copy static files from sources to output directory."""
        src_dir = os.path.join(self.script_dir, "sources", "web", "templates")

        # Copy CSS
        src_css = os.path.join(src_dir, "styles.css")
        dst_css = os.path.join(self.output_dir, "styles.css")
        if os.path.exists(src_css):
            shutil.copy2(src_css, dst_css)

    def _generate_task_card(
        self,
        name: str,
        script_path: str,
        time: str,
        task_id: Optional[int] = None,
        arguments: Optional[List[str]] = None,
        success: Optional[bool] = None,
        task_type: str = TaskTypes.SCRIPT,
        command: Optional[str] = None,
        interval: Optional[int] = None,
        start_time: Optional[str] = None,
    ) -> str:
        """Generate HTML for a task card."""
        if success is not None:
            status_class = "success" if success else "error"
            status_html = f'<span class="status {status_class}">{"Success" if success else "Failed"}</span>'
        else:
            status_html = ""

        # Format arguments to be more readable
        args_html = ""
        if arguments:
            args_list = []
            current_arg = []
            for arg in arguments:
                if arg.startswith("--"):
                    if current_arg:
                        args_list.append(" ".join(current_arg))
                    current_arg = [arg]
                else:
                    current_arg.append(arg)
            if current_arg:
                args_list.append(" ".join(current_arg))
            args_html = '<div class="task-arguments">'
            for arg_pair in args_list:
                args_html += f'<div class="argument">{arg_pair}</div>'
            args_html += "</div>"

        # Format details based on task type
        if task_type == TaskTypes.UV_COMMAND and command:
            details_html = f"""
                <div class="task-details">Command: {command}</div>
                <div class="task-details">Project: {script_path}</div>
            """
        else:
            details_html = f'<div class="task-details">{script_path}</div>'

        # Format schedule info if interval is provided
        schedule_html = ""
        if interval is not None:
            if interval == 0:
                schedule_html = f'<div class="task-schedule">{Defaults.MANUAL_ONLY_LABEL.capitalize()}</div>'
            elif start_time:
                schedule_html = f'<div class="task-schedule">Every {interval} min from {start_time}</div>'
            else:
                schedule_html = f'<div class="task-schedule">Every {interval} min</div>'

        return f"""
            <div class="task-card">
                <div class="task-header">
                    <span class="task-id">#{task_id}</span>
                    <div class="task-title">{name}</div>
                    {status_html}
                </div>
                {details_html}
                {schedule_html}
                {args_html}
                <div class="task-time">{time}</div>
            </div>
        """

    def update(
        self,
        recent_executions: List[Dict],
        next_jobs: List[Dict],
        tasks: Optional[List[Dict]] = None,
    ):
        """
        Update the status page with recent executions and next scheduled tasks.

        Args:
            recent_executions: List of recent task executions
            next_jobs: List of next scheduled jobs
            tasks: Optional list of all tasks (for interval/start_time info)
        """
        try:
            # Refresh output paths in case config changed
            self._update_output_paths()

            # Ensure output directory exists and is set up
            self._setup_output_directory()

            # Build a lookup for task details (interval, start_time)
            task_lookup = {}
            if tasks:
                for task in tasks:
                    task_lookup[task["id"]] = task

            # Generate HTML for recent tasks
            recent_html = []
            for execution in recent_executions:
                recent_html.append(
                    self._generate_task_card(
                        name=execution["name"],
                        script_path=execution["script_path"],
                        time=execution["execution_time"],
                        task_id=execution["task_id"],
                        success=execution["success"],
                        task_type=execution.get("task_type", TaskTypes.SCRIPT),
                        command=execution.get("command"),
                    )
                )

            # Generate HTML for next tasks
            # Job args: [task_id, name, script_path, arguments, task_type, command]
            next_html = []
            if next_jobs:
                for job in next_jobs:
                    if not hasattr(job, 'args') or not job.args:
                        continue
                    task_id = job.args[0]
                    task_type = job.args[4] if len(job.args) > 4 else TaskTypes.SCRIPT
                    command = job.args[5] if len(job.args) > 5 else None

                    # Get interval and start_time from task lookup
                    interval = None
                    start_time = None
                    if task_id in task_lookup:
                        interval = task_lookup[task_id].get("interval")
                        start_time = task_lookup[task_id].get("start_time")

                    task_html = self._generate_task_card(
                        name=job.name,
                        script_path=job.args[2],
                        time=f"Next run: {job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')}",
                        task_id=task_id,
                        arguments=job.args[3] if job.args[3] else None,
                        task_type=task_type,
                        command=command,
                        interval=interval,
                        start_time=start_time,
                    )
                    next_html.append(task_html)
                next_html = "\n".join(next_html)
            else:
                next_html = '<p class="no-tasks">No upcoming tasks</p>'

            # Read the template
            with open(self.template_path, "r", encoding="utf-8") as f:
                template = f.read()

            # Prepare replacements
            replacements = {
                "{{last_update}}": datetime.now().strftime("%d/%m/%Y, %H:%M:%S"),
                "{{next_tasks}}": next_html
                if next_html
                else '<p class="no-tasks">No upcoming tasks</p>',
                "{{recent_tasks}}": "\n".join(recent_html)
                if recent_html
                else '<p class="no-tasks">No recent tasks</p>',
            }

            # Apply all replacements
            for placeholder, value in replacements.items():
                template = template.replace(placeholder, value)

            # Wrap with PHP if output type is PHP
            if self.config.get_output_type() == "php":
                template = self.php_handler.wrap_html_with_php(template)

            # Write the updated file
            with open(self.output_path, "w", encoding="utf-8") as f:
                f.write(template)

            self.logger.debug(f"Status page updated at {self.output_path}")

        except Exception as e:
            self.logger.error(f"Error updating status page: {str(e)}")

    def sync_to_ftp(self) -> bool:
        """
        Sync the output directory to FTP if enabled and throttle interval has passed.

        Returns:
            True if sync was successful, skipped, or FTP is disabled, False on error
        """
        if not self.config.is_ftp_enabled():
            return True

        # Check throttle interval
        sync_interval = self.config.get_ftp_sync_interval()
        if sync_interval > 0 and self._last_ftp_sync:
            elapsed = (datetime.now() - self._last_ftp_sync).total_seconds()
            if elapsed < sync_interval * 60:
                self.logger.debug(
                    f"FTP sync skipped: {int(elapsed)}s since last sync, "
                    f"interval is {sync_interval}min"
                )
                return True  # Skip sync, not enough time passed

        # Proceed with sync
        success = self.ftp_syncer.sync(self.output_dir)
        if success:
            self._last_ftp_sync = datetime.now()
        return success

    def get_output_dir(self) -> str:
        """Get the current output directory path."""
        return self.output_dir

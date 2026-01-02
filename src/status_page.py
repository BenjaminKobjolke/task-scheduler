import os
import shutil
from typing import Dict, List, Optional
from datetime import datetime
from .logger import Logger
from .constants import TaskTypes

class StatusPage:
    """Handles the generation and updating of the status web page."""
    
    def __init__(self):
        """Initialize the status page handler."""
        self.logger = Logger("StatusPage")
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.template_path = os.path.join(script_dir, "sources", "web", "templates", "index.html")
        self.output_path = os.path.join(script_dir, "web", "index.html")
        
        # Copy static files on init
        self._copy_static_files()
        
    def _copy_static_files(self):
        """Copy static files from sources to web output directory."""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        src_dir = os.path.join(script_dir, "sources", "web", "templates")
        dst_dir = os.path.join(script_dir, "web")
        
        # Create web directory if it doesn't exist
        os.makedirs(dst_dir, exist_ok=True)
        
        # Copy CSS
        shutil.copy2(
            os.path.join(src_dir, "styles.css"),
            os.path.join(dst_dir, "styles.css")
        )
    
    def _generate_task_card(
        self,
        name: str,
        script_path: str,
        time: str,
        task_id: Optional[int] = None,
        arguments: Optional[List[str]] = None,
        success: Optional[bool] = None,
        task_type: str = TaskTypes.SCRIPT,
        command: Optional[str] = None
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
                if arg.startswith('--'):
                    if current_arg:
                        args_list.append(' '.join(current_arg))
                    current_arg = [arg]
                else:
                    current_arg.append(arg)
            if current_arg:
                args_list.append(' '.join(current_arg))
            args_html = '<div class="task-arguments">'
            for arg_pair in args_list:
                args_html += f'<div class="argument">{arg_pair}</div>'
            args_html += '</div>'

        # Format details based on task type
        if task_type == TaskTypes.UV_COMMAND and command:
            details_html = f"""
                <div class="task-details">Command: {command}</div>
                <div class="task-details">Project: {script_path}</div>
            """
        else:
            details_html = f'<div class="task-details">{script_path}</div>'

        return f"""
            <div class="task-card">
                <div class="task-header">
                    <span class="task-id">#{task_id}</span>
                    <div class="task-title">{name}</div>
                    {status_html}
                </div>
                {details_html}
                {args_html}
                <div class="task-time">{time}</div>
            </div>
        """
    
    def update(self, recent_executions: List[Dict], next_jobs: List[Dict]):
        """
        Update the status page with recent executions and next scheduled tasks.

        Args:
            recent_executions: List of recent task executions
            next_jobs: List of next scheduled jobs
        """
        try:
            # Generate HTML for recent tasks
            recent_html = []
            for execution in recent_executions:
                recent_html.append(
                    self._generate_task_card(
                        name=execution['name'],
                        script_path=execution['script_path'],
                        time=execution['execution_time'],
                        task_id=execution['task_id'],
                        success=execution['success'],
                        task_type=execution.get('task_type', TaskTypes.SCRIPT),
                        command=execution.get('command')
                    )
                )

            # Generate HTML for next tasks
            # Job args: [task_id, name, script_path, arguments, task_type, command]
            next_html = []
            if next_jobs:
                for job in next_jobs:
                    task_type = job.args[4] if len(job.args) > 4 else TaskTypes.SCRIPT
                    command = job.args[5] if len(job.args) > 5 else None
                    task_html = self._generate_task_card(
                        name=job.name,
                        script_path=job.args[2],
                        time=f"Next run: {job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')}",
                        task_id=job.args[0],  # task_id is first argument
                        arguments=job.args[3] if job.args[3] else None,
                        task_type=task_type,
                        command=command
                    )
                    next_html.append(task_html)
                next_html = '\n'.join(next_html)
            else:
                next_html = '<p class="no-tasks">No upcoming tasks</p>'

            # Read the template
            with open(self.template_path, 'r', encoding='utf-8') as f:
                template = f.read()

            # Prepare replacements
            replacements = {
                '{{last_update}}': datetime.now().strftime("%d/%m/%Y, %H:%M:%S"),
                '{{next_tasks}}': next_html if next_html else '<p class="no-tasks">No upcoming tasks</p>',
                '{{recent_tasks}}': '\n'.join(recent_html) if recent_html else '<p class="no-tasks">No recent tasks</p>'
            }

            # Apply all replacements
            for placeholder, value in replacements.items():
                template = template.replace(placeholder, value)

            # Write the updated file
            with open(self.output_path, 'w', encoding='utf-8') as f:
                f.write(template)

        except Exception as e:
            self.logger.error(f"Error updating status page: {str(e)}")

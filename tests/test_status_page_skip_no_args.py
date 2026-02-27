"""Tests that StatusPage.update() skips jobs without args (e.g. _hot_reload)."""

from unittest.mock import MagicMock, mock_open, patch
from datetime import datetime

from src.status_page import StatusPage
from src.constants import TaskTypes


TEMPLATE_HTML = "<html>{{recent_tasks}}{{next_tasks}}{{last_update}}</html>"


@patch.object(StatusPage, "__init__", lambda self: None)
def _make_status_page() -> StatusPage:
    """Create a StatusPage with minimal mocked internals."""
    sp = StatusPage()
    sp.logger = MagicMock()
    sp.config = MagicMock()
    sp.config.get_output_type.return_value = "html"
    sp.php_handler = MagicMock()
    sp.ftp_syncer = MagicMock()
    sp.script_dir = ""
    sp.template_path = "fake_template.html"
    sp.output_dir = ""
    sp.output_path = "fake_output.html"
    sp._last_ftp_sync = None
    sp._update_output_paths = MagicMock()
    sp._setup_output_directory = MagicMock()
    return sp


class TestStatusPageSkipsJobsWithoutArgs:
    """Regression tests for tuple index out of range when jobs lack args."""

    @patch("builtins.open", mock_open(read_data=TEMPLATE_HTML))
    def test_job_without_args_is_skipped(self):
        """A job with empty args (like _hot_reload) must not crash update()."""
        sp = _make_status_page()
        sp._generate_task_card = MagicMock(return_value="<div>card</div>")

        # A job that mimics _hot_reload: has args attribute but it's empty
        hot_reload_job = MagicMock()
        hot_reload_job.args = ()
        hot_reload_job.name = "_hot_reload"

        # A normal task job
        normal_job = MagicMock()
        normal_job.args = (1, "Test Task", "/path/to/script.py", [], TaskTypes.SCRIPT, None)
        normal_job.name = "Test Task"
        normal_job.next_run_time = datetime(2026, 1, 1, 12, 0, 0)

        # Should not raise
        sp.update(
            recent_executions=[],
            next_jobs=[hot_reload_job, normal_job],
            tasks=[],
        )

        # _generate_task_card should only be called for the normal job
        assert sp._generate_task_card.call_count == 1

    @patch("builtins.open", mock_open(read_data=TEMPLATE_HTML))
    def test_job_without_args_attribute_is_skipped(self):
        """A job object missing the args attribute entirely must not crash."""
        sp = _make_status_page()
        sp._generate_task_card = MagicMock(return_value="<div>card</div>")

        job_no_attr = MagicMock(spec=[])  # empty spec — no attributes
        job_no_attr.name = "_hot_reload"

        sp.update(
            recent_executions=[],
            next_jobs=[job_no_attr],
            tasks=[],
        )

        # No task card should be generated
        sp._generate_task_card.assert_not_called()

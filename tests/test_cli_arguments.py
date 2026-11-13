import sys

import pytest

from main import parse_arguments


def test_parse_arguments_preserves_supported_task_flags(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "main.py",
            "--script",
            "job.py",
            "--name",
            "Nightly job",
            "--interval",
            "2h",
            "--",
            "--target",
            "backup folder",
        ],
    )

    args = parse_arguments()

    assert args.script == "job.py"
    assert args.name == "Nightly job"
    assert args.interval == 120
    assert args.script_args == ["--", "--target", "backup folder"]


def test_parse_arguments_defaults_history_to_ten(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["main.py", "--history"])

    assert parse_arguments().history == 10


def test_parse_arguments_reports_invalid_interval(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["main.py", "--interval", "invalid"])

    with pytest.raises(SystemExit) as error:
        parse_arguments()

    assert error.value.code == 2

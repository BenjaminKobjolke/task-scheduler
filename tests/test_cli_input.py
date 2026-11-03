"""Tests for script-file discovery in the interactive add wizard."""

import os
from pathlib import Path

import pytest

from src.cli_input import _find_shell_scripts, _select_shell_script


@pytest.fixture
def script_dir(tmp_path: Path) -> Path:
    (tmp_path / "start.bat").write_text("")
    (tmp_path / "B.PS1").write_text("")
    (tmp_path / "x.py").write_text("")
    (tmp_path / "settings.json").write_text("")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.bat").write_text("")
    return tmp_path


def _feed_input(monkeypatch: pytest.MonkeyPatch, answers: list[str]) -> None:
    it = iter(answers)
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(it))


class TestFindShellScripts:
    def test_returns_only_top_level_bat_and_ps1_sorted(self, script_dir: Path) -> None:
        result = _find_shell_scripts(str(script_dir))
        assert [os.path.basename(p) for p in result] == ["B.PS1", "start.bat"]
        assert all(os.path.isabs(p) for p in result)

    def test_empty_dir(self, tmp_path: Path) -> None:
        assert _find_shell_scripts(str(tmp_path)) == []

    def test_missing_dir(self, tmp_path: Path) -> None:
        assert _find_shell_scripts(str(tmp_path / "nope")) == []


class TestSelectShellScript:
    def test_picks_numbered_script(
        self, script_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _feed_input(monkeypatch, ["2"])
        result = _select_shell_script(_find_shell_scripts(str(script_dir)))
        assert result is not None
        assert os.path.basename(result) == "start.bat"

    def test_empty_input_returns_none(
        self, script_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _feed_input(monkeypatch, [""])
        assert _select_shell_script(_find_shell_scripts(str(script_dir))) is None

    def test_invalid_then_valid(
        self, script_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _feed_input(monkeypatch, ["9", "abc", "1"])
        result = _select_shell_script(_find_shell_scripts(str(script_dir)))
        assert result is not None
        assert os.path.basename(result) == "B.PS1"

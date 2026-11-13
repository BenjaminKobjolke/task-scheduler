"""Tests for script_runner module."""

import os
import pytest
from src.script_runner import ScriptRunner
from src.constants import Paths


@pytest.fixture
def runner():
    """Create a ScriptRunner instance."""
    return ScriptRunner()


class TestGetUvCommands:
    """Tests for get_uv_commands method."""

    def test_get_uv_commands_no_pyproject(self, runner, temp_dir):
        result = runner.get_uv_commands(temp_dir)
        assert result == []

    def test_get_uv_commands_empty_scripts(self, runner, temp_dir):
        # Create pyproject.toml without scripts section
        pyproject_path = os.path.join(temp_dir, Paths.PYPROJECT_TOML)
        with open(pyproject_path, "w") as f:
            f.write("[project]\nname = 'test'\n")

        result = runner.get_uv_commands(temp_dir)
        assert result == []

    def test_get_uv_commands_with_scripts(self, runner, temp_dir):
        # Create pyproject.toml with scripts
        pyproject_path = os.path.join(temp_dir, Paths.PYPROJECT_TOML)
        with open(pyproject_path, "w") as f:
            f.write("""[project]
name = "test"

[project.scripts]
cmd1 = "test.main:main"
cmd2 = "test.cli:run"
""")

        result = runner.get_uv_commands(temp_dir)
        assert len(result) == 2
        assert "cmd1" in result
        assert "cmd2" in result


class TestDiscoverEntryPoints:
    """Tests for discover_entry_points method."""

    def test_discover_entry_points_from_project_name(self, runner, temp_dir):
        """Project name in pyproject.toml with matching package dir returns python -m command."""
        pyproject_path = os.path.join(temp_dir, Paths.PYPROJECT_TOML)
        with open(pyproject_path, "w") as f:
            f.write('[project]\nname = "my-cool-app"\n')

        # Create matching package directory
        pkg_dir = os.path.join(temp_dir, "my_cool_app")
        os.makedirs(pkg_dir)
        open(os.path.join(pkg_dir, "__init__.py"), "w").close()

        result = runner.discover_entry_points(temp_dir)

        assert any(cmd == "python -m my_cool_app" for cmd, _ in result)

    def test_discover_entry_points_no_matching_package(self, runner, temp_dir):
        """Project name exists but no matching directory → skipped."""
        pyproject_path = os.path.join(temp_dir, Paths.PYPROJECT_TOML)
        with open(pyproject_path, "w") as f:
            f.write('[project]\nname = "my-cool-app"\n')

        result = runner.discover_entry_points(temp_dir)

        assert not any("my_cool_app" in cmd for cmd, _ in result)

    def test_discover_entry_points_root_files(self, runner, temp_dir):
        """main.py and app.py in project root are discovered."""
        # Create pyproject.toml (required for uv project)
        pyproject_path = os.path.join(temp_dir, Paths.PYPROJECT_TOML)
        with open(pyproject_path, "w") as f:
            f.write('[project]\nname = "test"\n')

        open(os.path.join(temp_dir, "main.py"), "w").close()
        open(os.path.join(temp_dir, "app.py"), "w").close()

        result = runner.discover_entry_points(temp_dir)

        commands = [cmd for cmd, _ in result]
        assert "python main.py" in commands
        assert "python app.py" in commands

    def test_discover_entry_points_main_module(self, runner, temp_dir):
        """Package with __main__.py is discovered."""
        pyproject_path = os.path.join(temp_dir, Paths.PYPROJECT_TOML)
        with open(pyproject_path, "w") as f:
            f.write('[project]\nname = "test"\n')

        pkg_dir = os.path.join(temp_dir, "mypackage")
        os.makedirs(pkg_dir)
        open(os.path.join(pkg_dir, "__main__.py"), "w").close()

        result = runner.discover_entry_points(temp_dir)

        assert any(cmd == "python -m mypackage" for cmd, _ in result)

    def test_discover_entry_points_dedup(self, runner, temp_dir):
        """Project name and __main__.py scan producing same command → only one entry."""
        pyproject_path = os.path.join(temp_dir, Paths.PYPROJECT_TOML)
        with open(pyproject_path, "w") as f:
            f.write('[project]\nname = "mypackage"\n')

        pkg_dir = os.path.join(temp_dir, "mypackage")
        os.makedirs(pkg_dir)
        open(os.path.join(pkg_dir, "__init__.py"), "w").close()
        open(os.path.join(pkg_dir, "__main__.py"), "w").close()

        result = runner.discover_entry_points(temp_dir)

        matching = [cmd for cmd, _ in result if cmd == "python -m mypackage"]
        assert len(matching) == 1

    def test_discover_entry_points_empty(self, runner, temp_dir):
        """Nothing found → returns empty list."""
        pyproject_path = os.path.join(temp_dir, Paths.PYPROJECT_TOML)
        with open(pyproject_path, "w") as f:
            f.write('[project]\nname = "test"\n')

        result = runner.discover_entry_points(temp_dir)

        assert result == []

    def test_discover_entry_points_skips_excluded_dirs(self, runner, temp_dir):
        """tests/, __pycache__/, .hidden/ directories are skipped."""
        pyproject_path = os.path.join(temp_dir, Paths.PYPROJECT_TOML)
        with open(pyproject_path, "w") as f:
            f.write('[project]\nname = "test"\n')

        # Create excluded dirs with __main__.py
        for dirname in ["tests", "__pycache__", ".hidden"]:
            excluded_dir = os.path.join(temp_dir, dirname)
            os.makedirs(excluded_dir)
            open(os.path.join(excluded_dir, "__main__.py"), "w").close()

        result = runner.discover_entry_points(temp_dir)

        commands = [cmd for cmd, _ in result]
        assert "python -m tests" not in commands
        assert "python -m __pycache__" not in commands
        assert "python -m .hidden" not in commands

    def test_discover_entry_points_subdir_main_module_file(self, runner, temp_dir):
        """Subdir scan: <pkg>/main.py (not __main__.py) → python -m <pkg>.main."""
        pyproject_path = os.path.join(temp_dir, Paths.PYPROJECT_TOML)
        with open(pyproject_path, "w") as f:
            f.write('[project]\nname = "folders-cleanup"\n')

        pkg_dir = os.path.join(temp_dir, "app")
        os.makedirs(pkg_dir)
        open(os.path.join(pkg_dir, "main.py"), "w").close()

        result = runner.discover_entry_points(temp_dir)

        commands = [cmd for cmd, _ in result]
        assert "python -m app.main" in commands
        # Bare `python -m app` requires __main__.py and must NOT appear
        assert "python -m app" not in commands

    def test_discover_entry_points_hatch_declared_package(self, runner, temp_dir):
        """[tool.hatch.build.targets.wheel].packages = ["app"] surfaces app."""
        pyproject_path = os.path.join(temp_dir, Paths.PYPROJECT_TOML)
        with open(pyproject_path, "w") as f:
            f.write("""[project]
name = "folders-cleanup"

[tool.hatch.build.targets.wheel]
packages = ["app"]
""")

        pkg_dir = os.path.join(temp_dir, "app")
        os.makedirs(pkg_dir)
        open(os.path.join(pkg_dir, "main.py"), "w").close()

        result = runner.discover_entry_points(temp_dir)

        commands = [cmd for cmd, _ in result]
        # Should appear exactly once despite both phase 2 (declared) and phase 4
        # (subdir scan) finding it
        assert commands.count("python -m app.main") == 1

    def test_discover_entry_points_setuptools_packages_list(self, runner, temp_dir):
        """[tool.setuptools].packages = ["mypkg"] is honored."""
        pyproject_path = os.path.join(temp_dir, Paths.PYPROJECT_TOML)
        with open(pyproject_path, "w") as f:
            f.write("""[project]
name = "myproject"

[tool.setuptools]
packages = ["mypkg"]
""")

        pkg_dir = os.path.join(temp_dir, "mypkg")
        os.makedirs(pkg_dir)
        open(os.path.join(pkg_dir, "__main__.py"), "w").close()

        result = runner.discover_entry_points(temp_dir)

        commands = [cmd for cmd, _ in result]
        assert "python -m mypkg" in commands

    def test_discover_entry_points_setuptools_find_include(self, runner, temp_dir):
        """[tool.setuptools.packages.find].include with literal entries is honored."""
        pyproject_path = os.path.join(temp_dir, Paths.PYPROJECT_TOML)
        with open(pyproject_path, "w") as f:
            f.write("""[project]
name = "myproject"

[tool.setuptools.packages.find]
include = ["literal_pkg", "wildcard*"]
""")

        # Create both candidate dirs; only literal_pkg should be surfaced via
        # phase 2. The wildcard entry has '*' and must be skipped.
        for name in ("literal_pkg", "wildcard"):
            d = os.path.join(temp_dir, name)
            os.makedirs(d)
            open(os.path.join(d, "main.py"), "w").close()

        result = runner.discover_entry_points(temp_dir)

        commands = [cmd for cmd, _ in result]
        # literal_pkg surfaces via both phase 2 (declared) and phase 4 (subdir
        # scan) — once after dedup.
        assert commands.count("python -m literal_pkg.main") == 1
        # wildcard surfaces only via phase 4 (subdir scan), not phase 2.
        assert "python -m wildcard.main" in commands

    def test_discover_entry_points_skips_nested_declared_package(
        self, runner, temp_dir
    ):
        """Declared package names containing '.' or '/' are skipped (nested)."""
        pyproject_path = os.path.join(temp_dir, Paths.PYPROJECT_TOML)
        with open(pyproject_path, "w") as f:
            f.write("""[project]
name = "myproject"

[tool.hatch.build.targets.wheel]
packages = ["src/app", "myproject.sub"]
""")

        # Create the directory at "src/app" and "myproject" with main.py to
        # confirm phase 2 did NOT surface either as `python -m src/app...`.
        os.makedirs(os.path.join(temp_dir, "src", "app"))
        open(os.path.join(temp_dir, "src", "app", "main.py"), "w").close()

        result = runner.discover_entry_points(temp_dir)

        commands = [cmd for cmd, _ in result]
        # Phase 2 must skip nested paths. Phase 4 may still pick up "src" as a
        # subdir, but that has no main.py / __main__.py at its root.
        assert not any("src/app" in cmd or "src\\app" in cmd for cmd in commands)
        assert "python -m myproject.sub" not in commands

    def test_discover_entry_points_project_name_with_main_module(
        self, runner, temp_dir
    ):
        """Project-name match with both __init__.py and main.py emits both forms."""
        pyproject_path = os.path.join(temp_dir, Paths.PYPROJECT_TOML)
        with open(pyproject_path, "w") as f:
            f.write('[project]\nname = "my-app"\n')

        pkg_dir = os.path.join(temp_dir, "my_app")
        os.makedirs(pkg_dir)
        open(os.path.join(pkg_dir, "__init__.py"), "w").close()
        open(os.path.join(pkg_dir, "main.py"), "w").close()

        result = runner.discover_entry_points(temp_dir)

        commands = [cmd for cmd, _ in result]
        # Bare form is preserved (legacy: __init__.py alone is enough)
        assert "python -m my_app" in commands
        # New: main.py adds the .main form
        assert "python -m my_app.main" in commands

"""Read uv project metadata and find commands a user can run."""

import os
import tomllib

from .constants import Discovery, Paths
from .logger import Logger


class UvProjectDiscovery:
    """Parse pyproject metadata and discover likely Python entry points."""

    def __init__(self, logger: Logger):
        self.logger = logger

    def get_commands(self, project_dir: str) -> list[str]:
        """Return command names declared in a project's ``[project.scripts]``."""
        pyproject_path = os.path.join(project_dir, Paths.PYPROJECT_TOML)
        if not os.path.exists(pyproject_path):
            return []

        try:
            with open(pyproject_path, "rb") as pyproject_file:
                data = tomllib.load(pyproject_file)
            return list(data.get("project", {}).get("scripts", {}).keys())
        except Exception as error:
            self.logger.error(f"Error reading pyproject.toml: {str(error)}")
            return []

    def discover_entry_points(self, project_dir: str) -> list[tuple[str, str]]:
        """Find common module and script entry points in a uv project."""
        entries: list[tuple[str, str]] = []
        seen_commands: set[str] = set()
        pyproject_data = self._read_pyproject(project_dir)

        project_name = pyproject_data.get("project", {}).get("name", "")
        if project_name:
            module_name = project_name.replace("-", "_")
            package_dir = os.path.join(project_dir, module_name)
            init_path = os.path.join(package_dir, Paths.INIT_PY)
            if os.path.isdir(package_dir) and os.path.exists(init_path):
                command = f"python -m {module_name}"
                self._append_entry(entries, seen_commands, command, Discovery.DESC_PROJECT_MODULE)
                main_path = os.path.join(package_dir, Paths.PACKAGE_MAIN_MODULE)
                if os.path.exists(main_path):
                    command = f"python -m {module_name}.main"
                    self._append_entry(
                        entries, seen_commands, command, Discovery.DESC_PACKAGE_MAIN_MODULE
                    )

        for package in self._declared_packages(pyproject_data):
            self._add_package_entries(
                project_dir,
                package,
                seen_commands,
                entries,
                main_desc=Discovery.DESC_DECLARED_MAIN_MODULE,
                package_main_desc=Discovery.DESC_DECLARED_PACKAGE_MAIN,
            )

        for filename in Discovery.ROOT_ENTRY_FILES:
            if os.path.isfile(os.path.join(project_dir, filename)):
                command = f"python {filename}"
                self._append_entry(entries, seen_commands, command, Discovery.DESC_ROOT_FILE)

        try:
            for entry in os.listdir(project_dir):
                entry_path = os.path.join(project_dir, entry)
                if (
                    not os.path.isdir(entry_path)
                    or entry.startswith(".")
                    or entry in Discovery.EXCLUDED_DIRS
                ):
                    continue
                self._add_package_entries(
                    project_dir,
                    entry,
                    seen_commands,
                    entries,
                    main_desc=Discovery.DESC_MAIN_MODULE,
                    package_main_desc=Discovery.DESC_PACKAGE_MAIN_MODULE,
                )
        except OSError:
            pass

        return entries

    @staticmethod
    def _append_entry(
        entries: list[tuple[str, str]],
        seen_commands: set[str],
        command: str,
        description: str,
    ) -> None:
        if command not in seen_commands:
            entries.append((command, description))
            seen_commands.add(command)

    @staticmethod
    def _read_pyproject(project_dir: str) -> dict:
        pyproject_path = os.path.join(project_dir, Paths.PYPROJECT_TOML)
        if not os.path.exists(pyproject_path):
            return {}
        try:
            with open(pyproject_path, "rb") as pyproject_file:
                return tomllib.load(pyproject_file)
        except Exception:
            return {}

    @staticmethod
    def _declared_packages(pyproject_data: dict) -> list[str]:
        """Collect top-level packages declared by supported build backends."""
        names: list[str] = []
        seen: set[str] = set()

        def add(value: object) -> None:
            if not isinstance(value, str):
                return
            name = value.strip()
            if (
                not name
                or "/" in name
                or "\\" in name
                or "." in name
                or name in Discovery.EXCLUDED_DIRS
                or name in seen
            ):
                return
            seen.add(name)
            names.append(name)

        tool = pyproject_data.get("tool", {})
        if not isinstance(tool, dict):
            return names

        hatch_packages = (
            tool.get("hatch", {})
            .get("build", {})
            .get("targets", {})
            .get("wheel", {})
            .get("packages")
        )
        if isinstance(hatch_packages, list):
            for package in hatch_packages:
                add(package)

        setuptools = tool.get("setuptools", {})
        if isinstance(setuptools, dict):
            packages = setuptools.get("packages")
            if isinstance(packages, list):
                for package in packages:
                    add(package)
            elif isinstance(packages, dict):
                find = packages.get("find", {})
                if isinstance(find, dict):
                    include = find.get("include", [])
                    if isinstance(include, list):
                        for package in include:
                            if isinstance(package, str) and "*" not in package:
                                add(package)

        return names

    def _add_package_entries(
        self,
        project_dir: str,
        package_name: str,
        seen_commands: set[str],
        entries: list[tuple[str, str]],
        *,
        main_desc: str,
        package_main_desc: str,
    ) -> None:
        """Append module entry points present in a package directory."""
        package_dir = os.path.join(project_dir, package_name)
        if not os.path.isdir(package_dir):
            return

        if os.path.exists(os.path.join(package_dir, Paths.MAIN_PY)):
            self._append_entry(
                entries, seen_commands, f"python -m {package_name}", main_desc
            )
        if os.path.exists(os.path.join(package_dir, Paths.PACKAGE_MAIN_MODULE)):
            self._append_entry(
                entries,
                seen_commands,
                f"python -m {package_name}.main",
                package_main_desc,
            )

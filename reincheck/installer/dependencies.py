"""Dependency scanning and management."""

import re
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum

SUBPROCESS_TIMEOUT = 5
WHICH_PATTERN = r"^which \S+$"


class RiskLevel(Enum):
    SAFE = "safe"
    INTERACTIVE = "interactive"
    DANGEROUS = "dangerous"


class PresetStatus(Enum):
    GREEN = "green"
    PARTIAL = "partial"
    RED = "red"


@dataclass
class Dependency:
    name: str
    check_command: str
    install_hint: str
    version_command: str | None = None
    min_version: str | None = None
    max_version: str | None = None

    def is_available(self) -> bool:
        binary = _extract_binary_from_which(self.check_command)
        if binary:
            return shutil.which(binary) is not None

        try:
            result = subprocess.run(
                self.check_command,
                shell=True,
                capture_output=True,
                timeout=SUBPROCESS_TIMEOUT,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False

    def get_version(self) -> str | None:
        if not self.version_command:
            return None

        try:
            result = subprocess.run(
                self.version_command,
                shell=True,
                capture_output=True,
                timeout=SUBPROCESS_TIMEOUT,
                text=True,
            )
            if result.returncode == 0:
                output = result.stdout.strip() or result.stderr.strip()
                return self._extract_version(output)
        except (subprocess.TimeoutExpired, OSError):
            pass

        return None

    def _extract_version(self, output: str) -> str | None:
        patterns = [
            r"(\d+\.\d+\.\d+)",
            r"(\d+\.\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                return match.group(1)

        stripped = output.strip()
        if re.match(r"^[\d.]+$", stripped):
            return stripped

        return None

    def is_version_satisfied(self, version: str | None) -> bool:
        if not version:
            return False

        if not self.min_version and not self.max_version:
            return True

        try:
            from packaging import version as pkg_version

            v = pkg_version.parse(version)

            if self.min_version:
                min_v = pkg_version.parse(self.min_version)
                if v < min_v:
                    return False

            if self.max_version:
                max_v = pkg_version.parse(self.max_version)
                if v > max_v:
                    return False

            return True
        except pkg_version.InvalidVersion:
            return True
        except Exception:
            return True


@dataclass
class DependencyStatus:
    name: str
    available: bool
    version: str | None = None
    path: str | None = None
    version_satisfied: bool = True

    @property
    def status_icon(self) -> str:
        if not self.available:
            return "❌"
        if not self.version_satisfied:
            return "⚠️"
        return "✅"


_BUILTIN_DEPENDENCIES = [
    Dependency(
        name="mise",
        check_command="which mise",
        version_command="mise --version",
        install_hint="Install from https://mise.jdx.dev",
    ),
    Dependency(
        name="npm",
        check_command="which npm",
        version_command="npm --version",
        install_hint="Install Node.js from https://nodejs.org",
    ),
    Dependency(
        name="curl",
        check_command="which curl",
        version_command="curl --version",
        install_hint="Install via system package manager",
    ),
    Dependency(
        name="jq",
        check_command="which jq",
        version_command="jq --version",
        install_hint="Install via system package manager",
    ),
    Dependency(
        name="uv",
        check_command="which uv",
        version_command="uv --version",
        install_hint="Install from https://docs.astral.sh/uv/",
    ),
    Dependency(
        name="brew",
        check_command="which brew",
        version_command="brew --version",
        install_hint="Install from https://brew.sh",
    ),
    Dependency(
        name="pipx",
        check_command="which pipx",
        version_command="pipx --version",
        install_hint="Install via 'pip install pipx' or system package manager",
    ),
    Dependency(
        name="cargo",
        check_command="which cargo",
        version_command="cargo --version",
        install_hint="Install Rust from https://rustup.rs",
    ),
    Dependency(
        name="rg",
        check_command="which rg",
        version_command="rg --version",
        install_hint="Install from https://github.com/BurntSushi/ripgrep",
    ),
    Dependency(
        name="sd",
        check_command="which sd",
        version_command="sd --version",
        install_hint="Install from https://github.com/chmln/sd",
    ),
    Dependency(
        name="python",
        check_command="which python3 || which python",
        version_command="python3 --version || python --version",
        min_version="3.11",
        install_hint="Install Python 3.11+ from https://python.org",
    ),
    Dependency(
        name="node",
        check_command="which node",
        version_command="node --version",
        install_hint="Install Node.js from https://nodejs.org",
    ),
    Dependency(
        name="go",
        check_command="which go",
        version_command="go version",
        install_hint="Install Go from https://go.dev",
    ),
    Dependency(
        name="git",
        check_command="which git",
        version_command="git --version",
        install_hint="Install from https://git-scm.com",
    ),
]


def get_all_dependencies() -> dict[str, Dependency]:
    return {dep.name: dep for dep in _BUILTIN_DEPENDENCIES}


def get_dependency(name: str) -> Dependency | None:
    return get_all_dependencies().get(name)


def scan_dependencies() -> dict[str, DependencyStatus]:
    deps = get_all_dependencies()
    result = {}

    for name, dep in deps.items():
        version = None
        path = None
        version_satisfied = True

        if dep.check_command.startswith("which "):
            path = _get_binary_path(dep.check_command)
            available = path is not None
        else:
            try:
                result_subproc = subprocess.run(
                    dep.check_command,
                    shell=True,
                    capture_output=True,
                    timeout=SUBPROCESS_TIMEOUT,
                )
                available = result_subproc.returncode == 0
            except (subprocess.TimeoutExpired, OSError):
                available = False

        if available:
            version = dep.get_version()
            version_satisfied = dep.is_version_satisfied(version)

        result[name] = DependencyStatus(
            name=name,
            available=available,
            version=version,
            path=path,
            version_satisfied=version_satisfied,
        )

    return result


def _infer_risk_level(command: str) -> RiskLevel:
    pipe_pattern = re.compile(r"\|.*\b(sh|bash)\b", re.IGNORECASE)
    if pipe_pattern.search(command):
        return RiskLevel.DANGEROUS
    if (
        "npm install" in command
        or "pip install" in command
        or "uv tool install" in command
    ):
        return RiskLevel.INTERACTIVE
    return RiskLevel.SAFE


def _is_simple_which_command(command: str) -> bool:
    return re.match(WHICH_PATTERN, command) is not None


def _extract_binary_from_which(command: str) -> str | None:
    if _is_simple_which_command(command):
        return command.split(maxsplit=1)[1].strip()
    return None


def _get_binary_path(command: str) -> str | None:
    binary = _extract_binary_from_which(command)
    if binary:
        return shutil.which(binary)

    try:
        proc_result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            timeout=SUBPROCESS_TIMEOUT,
        )
        if proc_result.returncode == 0 and proc_result.stdout:
            if isinstance(proc_result.stdout, bytes):
                path = proc_result.stdout.decode().strip()
            else:
                path = proc_result.stdout.strip()
            if path:
                first_line = path.splitlines()[0]
                return first_line if first_line else None
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None


__all__ = [
    "RiskLevel",
    "PresetStatus",
    "Dependency",
    "DependencyStatus",
    "get_all_dependencies",
    "get_dependency",
    "scan_dependencies",
    "_infer_risk_level",
]

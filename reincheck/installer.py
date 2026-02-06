"""Installer engine for harness setup and management."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RiskLevel(Enum):
    SAFE = "safe"
    INTERACTIVE = "interactive"
    DANGEROUS = "dangerous"


class PresetStatus(Enum):
    GREEN = "green"  # All dependencies satisfied
    PARTIAL = "partial"  # Some dependencies satisfied
    RED = "red"  # No dependencies satisfied


@dataclass
class Dependency:
    name: str
    check_command: str
    install_hint: str
    version_command: str | None = None
    min_version: str | None = None
    max_version: str | None = None

    def is_available(self) -> bool:
        """Check if this dependency is available in PATH.

        Uses subprocess directly to avoid asyncio.run() issues when
        called from within an existing event loop.
        """
        import shutil
        import subprocess

        # Fast path: if check_command is just "which <name>", use shutil.which
        if self.check_command.startswith("which "):
            binary = self.check_command.split(maxsplit=1)[1].strip()
            return shutil.which(binary) is not None

        # Fallback: run the check command synchronously
        try:
            result = subprocess.run(
                self.check_command,
                shell=True,
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False

    def get_version(self) -> str | None:
        """Get the installed version of this dependency."""
        import subprocess

        if not self.version_command:
            return None

        try:
            # Security note: shell=True is safe here because version_command
            # is a predefined internal string from our dependency definitions,
            # never user input. Matches reincheck-gg2 design decision.
            result = subprocess.run(
                self.version_command,
                shell=True,
                capture_output=True,
                timeout=5,
                text=True,
            )
            if result.returncode == 0:
                # Extract version from output (handle common patterns)
                output = result.stdout.strip() or result.stderr.strip()
                return self._extract_version(output)
        except (subprocess.TimeoutExpired, OSError):
            pass

        return None

    def _extract_version(self, output: str) -> str | None:
        """Extract version string from command output.

        Handles common patterns:
        - "mise 2024.12.1" -> "2024.12.1"
        - "Python 3.11.7" -> "3.11.7"
        - "npm 10.8.0" -> "10.8.0"
        - "0.0.1770300461" (amp style) -> "0.0.1770300461"
        """
        import re

        # Try to find a version-like string (digits with dots)
        # Match patterns like: X.Y.Z, vX.Y.Z, version X.Y.Z
        patterns = [
            r"(\d+\.\d+\.\d+)",  # Semantic version
            r"(\d+\.\d+)",  # Major.Minor
        ]

        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                return match.group(1)

        # If no pattern matches, check if entire output is just the version (like amp)
        stripped = output.strip()
        if re.match(r"^[\d.]+$", stripped):
            return stripped

        return None

    def is_version_satisfied(self, version: str | None) -> bool:
        """Check if the given version satisfies min/max constraints.

        For complex version schemes (like amp's timestamp-based versions),
        this returns True unless min/max are specified and a comparator
        is registered.
        """
        if not version:
            return False

        if not self.min_version and not self.max_version:
            return True

        # For now, only handle semver comparisons
        # Custom comparators can be added here for special cases (amp, etc.)
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
            # Version string doesn't conform to semver (e.g., amp timestamps)
            # Assume satisfied - don't block on non-standard versions
            return True
        except Exception:
            # Other unexpected errors - assume satisfied to avoid blocking
            return True


@dataclass
class DependencyStatus:
    """Result of scanning a dependency."""

    name: str
    available: bool
    version: str | None = None
    path: str | None = None
    version_satisfied: bool = True

    @property
    def status_icon(self) -> str:
        """Get status icon for display."""
        if not self.available:
            return "❌"
        if not self.version_satisfied:
            return "⚠️"
        return "✅"


@dataclass
class Harness:
    name: str
    display_name: str
    description: str
    github_repo: str | None = None
    release_notes_url: str | None = None


@dataclass
class InstallMethod:
    harness: str
    method_name: str
    install: str
    upgrade: str
    version: str
    check_latest: str
    dependencies: list[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.SAFE


@dataclass
class Preset:
    name: str
    strategy: str
    description: str
    methods: dict[str, str]
    fallback_strategy: str | None = None
    priority: int = 999


@dataclass
class PlanStep:
    harness: str
    action: str
    command: str
    timeout: int
    risk_level: RiskLevel
    method_name: str
    dependencies: list[str] = field(default_factory=list)


@dataclass
class Plan:
    preset_name: str
    steps: list[PlanStep]
    unsatisfied_deps: list[str] = field(default_factory=list)
    risky_steps: list[str] = field(default_factory=list)

    def is_ready(self) -> bool:
        return len(self.unsatisfied_deps) == 0


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
    """Get all built-in dependencies."""
    return {dep.name: dep for dep in _BUILTIN_DEPENDENCIES}


def get_dependency(name: str) -> Dependency | None:
    """Get a dependency by name."""
    return get_all_dependencies().get(name)


def scan_dependencies() -> dict[str, DependencyStatus]:
    """Scan PATH for all known dependencies, return full status with versions."""
    import shutil

    deps = get_all_dependencies()
    result = {}

    for name, dep in deps.items():
        available = dep.is_available()
        version = None
        path = None
        version_satisfied = True

        if available:
            # Get the binary path
            if dep.check_command.startswith("which "):
                binary = dep.check_command.split(maxsplit=1)[1].strip()
                path = shutil.which(binary)

            # Get version
            version = dep.get_version()

            # Check if version satisfies constraints
            version_satisfied = dep.is_version_satisfied(version)

        result[name] = DependencyStatus(
            name=name,
            available=available,
            version=version,
            path=path,
            version_satisfied=version_satisfied,
        )

    return result


def compute_preset_status(
    preset: Preset,
    methods: dict[str, InstallMethod],
    dep_map: dict[str, DependencyStatus],
) -> PresetStatus:
    """Determine if a preset is fully green, partially green, or red.

    A preset is GREEN if all required dependencies for all chosen methods
    are available and satisfy version constraints.
    PARTIAL if some are satisfied.
    RED if none are satisfied.
    """
    all_deps = set()

    for harness_name, method_name in preset.methods.items():
        method_key = f"{harness_name}.{method_name}"
        method = methods.get(method_key)
        if method:
            all_deps.update(method.dependencies)

    if not all_deps:
        # No dependencies defined, assume green
        return PresetStatus.GREEN

    satisfied_count = 0
    for dep_name in all_deps:
        status = dep_map.get(dep_name)
        if status and status.available and status.version_satisfied:
            satisfied_count += 1

    if satisfied_count == len(all_deps):
        return PresetStatus.GREEN
    elif satisfied_count > 0:
        return PresetStatus.PARTIAL
    else:
        return PresetStatus.RED


@dataclass
class DependencyReport:
    """Structured dependency report for UI consumption."""

    all_deps: dict[str, DependencyStatus]
    preset_statuses: dict[str, PresetStatus]
    missing_deps: list[str]
    unsatisfied_versions: list[str]
    available_count: int
    total_count: int

    @property
    def overall_ready(self) -> bool:
        """Check if all dependencies are satisfied."""
        return self.available_count == self.total_count


def get_dependency_report(
    presets: dict[str, Preset],
    methods: dict[str, InstallMethod],
    dep_map: dict[str, DependencyStatus] | None = None,
) -> DependencyReport:
    """Generate a structured dependency report for the setup UI.

    Args:
        presets: Dictionary of preset name to Preset objects
        methods: Dictionary of "{harness}.{method}" to InstallMethod objects
        dep_map: Optional pre-scanned dependency map (will scan if not provided)

    Returns:
        DependencyReport with all dependency statuses and preset readiness
    """
    if dep_map is None:
        dep_map = scan_dependencies()

    # Compute status for each preset
    preset_statuses = {}
    for preset_name, preset in presets.items():
        status = compute_preset_status(preset, methods, dep_map)
        preset_statuses[preset_name] = status

    # Find missing and unsatisfied dependencies
    missing_deps = []
    unsatisfied_versions = []

    for name, status in dep_map.items():
        if not status.available:
            missing_deps.append(name)
        elif not status.version_satisfied:
            unsatisfied_versions.append(name)

    # Count available dependencies
    available_count = sum(
        1 for s in dep_map.values() if s.available and s.version_satisfied
    )

    return DependencyReport(
        all_deps=dep_map,
        preset_statuses=preset_statuses,
        missing_deps=missing_deps,
        unsatisfied_versions=unsatisfied_versions,
        available_count=available_count,
        total_count=len(dep_map),
    )


def _infer_risk_level(command: str) -> RiskLevel:
    """Infer risk level from command string."""
    import re

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


def resolve_method(
    preset: Preset,
    harness_name: str,
    methods: dict[str, InstallMethod],
    overrides: dict[str, Any] | None = None,
) -> InstallMethod:
    """Resolve which install method to use for a harness.

    Resolution order:
    1. Per-command override
    2. Per-harness method override
    3. Preset default
    4. Fallback strategy (if defined)
    """
    overrides = overrides or {}
    harness_override = overrides.get(harness_name)

    if isinstance(harness_override, dict):
        custom_override = harness_override

        # Find base method to merge with (from override's "method" key or preset default)
        base_method_name = custom_override.get("method") or preset.methods.get(
            harness_name
        )
        base_method = (
            methods.get(f"{harness_name}.{base_method_name}")
            if base_method_name
            else None
        )

        if "commands" in custom_override:
            cmds = custom_override["commands"]
            # Build custom method, using base_method as fallback for missing commands
            return InstallMethod(
                harness=harness_name,
                method_name="custom",
                install=cmds.get("install")
                or (base_method.install if base_method else ""),
                upgrade=cmds.get("upgrade")
                or (base_method.upgrade if base_method else ""),
                version=cmds.get("version")
                or (base_method.version if base_method else ""),
                check_latest=cmds.get("check_latest")
                or (base_method.check_latest if base_method else ""),
                dependencies=base_method.dependencies if base_method else [],
                risk_level=_infer_risk_level(cmds.get("install", "")),
            )
        elif base_method:
            return base_method

    if harness_override and isinstance(harness_override, str):
        method_key = f"{harness_name}.{harness_override}"
        method = methods.get(method_key)
        if method:
            return method

    preset_method_name = preset.methods.get(harness_name)
    if preset_method_name:
        method_key = f"{harness_name}.{preset_method_name}"
        method = methods.get(method_key)
        if method:
            return method

    if preset.fallback_strategy:
        fallback_key = f"{harness_name}.{preset.fallback_strategy}"
        method = methods.get(fallback_key)
        if method:
            return method

    raise ValueError(
        f"No valid install method found for {harness_name} in preset {preset.name}"
    )


def plan_install(
    preset: Preset,
    harnesses: list[str],
    methods: dict[str, InstallMethod],
    overrides: dict[str, Any] | None = None,
) -> Plan:
    """Generate ordered installation steps."""
    from reincheck import INSTALL_TIMEOUT

    steps = []
    unsatisfied = set()
    risky = []
    dep_map = scan_dependencies()

    for harness_name in harnesses:
        method = resolve_method(preset, harness_name, methods, overrides)

        for dep in method.dependencies:
            if not dep_map.get(dep, False):
                unsatisfied.add(dep)

        if method.risk_level == RiskLevel.DANGEROUS:
            risky.append(harness_name)

        steps.append(
            PlanStep(
                harness=harness_name,
                action="install",
                command=method.install,
                timeout=INSTALL_TIMEOUT,
                risk_level=method.risk_level,
                method_name=method.method_name,
                dependencies=method.dependencies.copy(),
            )
        )

    return Plan(
        preset_name=preset.name,
        steps=steps,
        unsatisfied_deps=list(unsatisfied),
        risky_steps=risky,
    )


def render_plan(plan: Plan) -> str:
    """Generate human-readable plan summary."""
    lines = [f"Installation Plan: {plan.preset_name}", ""]

    if plan.unsatisfied_deps:
        lines.append("⚠️  Missing dependencies:")
        for dep in plan.unsatisfied_deps:
            dep_obj = get_dependency(dep)
            hint = dep_obj.install_hint if dep_obj else "Unknown dependency"
            lines.append(f"   • {dep}: {hint}")
        lines.append("")

    if plan.risky_steps:
        lines.append("⚠️  The following require curl|sh (review carefully):")
        for harness in plan.risky_steps:
            lines.append(f"   • {harness}")
        lines.append("")

    lines.append("Steps:")
    for i, step in enumerate(plan.steps, 1):
        risk_icon = {"safe": "🟢", "interactive": "🟡", "dangerous": "🔴"}[
            step.risk_level.value
        ]
        lines.append(f"  {i}. {risk_icon} {step.harness}")
        lines.append(f"     $ {step.command}")

    return "\n".join(lines)


@dataclass
class StepResult:
    harness: str
    status: str
    output: str


def _confirm(message: str) -> bool:
    """Ask user for confirmation."""
    import click

    return click.confirm(message, default=False)


async def apply_plan(
    plan: Plan, dry_run: bool = False, skip_confirmation: bool = False
) -> list[StepResult]:
    """Execute installation plan."""
    from reincheck import run_command_async

    if not plan.is_ready() and not skip_confirmation:
        if not _confirm("Dependencies missing. Continue anyway?"):
            return []

    results = []

    for step in plan.steps:
        if step.risk_level == RiskLevel.DANGEROUS and not skip_confirmation:
            print(f"\n⚠️  DANGEROUS: About to run curl|sh for {step.harness}")
            print(f"   Command: {step.command}")
            if not _confirm("Execute this command? (review carefully)"):
                results.append(StepResult(step.harness, "skipped", "User declined"))
                continue

        if dry_run:
            print(f"[DRY-RUN] Would execute: {step.command}")
            results.append(StepResult(step.harness, "dry-run", step.command))
            continue

        output, returncode = await run_command_async(step.command, timeout=step.timeout)

        if returncode == 0:
            results.append(StepResult(step.harness, "success", output))
        else:
            results.append(StepResult(step.harness, "failed", output))

    return results


__all__ = [
    "RiskLevel",
    "PresetStatus",
    "Dependency",
    "DependencyStatus",
    "DependencyReport",
    "Harness",
    "InstallMethod",
    "Preset",
    "PlanStep",
    "Plan",
    "StepResult",
    "get_all_dependencies",
    "get_dependency",
    "scan_dependencies",
    "compute_preset_status",
    "get_dependency_report",
    "resolve_method",
    "plan_install",
    "render_plan",
    "apply_plan",
]

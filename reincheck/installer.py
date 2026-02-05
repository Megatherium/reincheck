"""Installer engine for harness setup and management."""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RiskLevel(Enum):
    SAFE = "safe"
    INTERACTIVE = "interactive"
    DANGEROUS = "dangerous"


@dataclass
class Dependency:
    name: str
    check_command: str
    install_hint: str

    def is_available(self) -> bool:
        """Check if this dependency is available in PATH."""
        from reincheck import run_command_async

        async def _check() -> bool:
            try:
                _, returncode = await asyncio.wait_for(
                    run_command_async(self.check_command, timeout=5), timeout=5
                )
                return returncode == 0
            except (asyncio.TimeoutError, Exception):
                return False

        return asyncio.run(_check())


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
        install_hint="Install from https://mise.jdx.dev",
    ),
    Dependency(
        name="npm",
        check_command="which npm",
        install_hint="Install Node.js from https://nodejs.org",
    ),
    Dependency(
        name="curl",
        check_command="which curl",
        install_hint="Install via system package manager",
    ),
    Dependency(
        name="jq",
        check_command="which jq",
        install_hint="Install via system package manager",
    ),
    Dependency(
        name="uv",
        check_command="which uv",
        install_hint="Install from https://docs.astral.sh/uv/",
    ),
    Dependency(
        name="brew",
        check_command="which brew",
        install_hint="Install from https://brew.sh",
    ),
]


def get_all_dependencies() -> dict[str, Dependency]:
    """Get all built-in dependencies."""
    return {dep.name: dep for dep in _BUILTIN_DEPENDENCIES}


def get_dependency(name: str) -> Dependency | None:
    """Get a dependency by name."""
    return get_all_dependencies().get(name)


def scan_dependencies() -> dict[str, bool]:
    """Scan PATH for all known dependencies, return availability map."""
    deps = get_all_dependencies()
    return {name: dep.is_available() for name, dep in deps.items()}


def _infer_risk_level(command: str) -> RiskLevel:
    """Infer risk level from command string."""
    if "curl" in command and (
        " | " in command or " |sh" in command or "| sh" in command
    ):
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
        method_key = f"{harness_name}.custom"

        method = methods.get(method_key)
        if method:
            if "commands" in custom_override:
                return InstallMethod(
                    harness=harness_name,
                    method_name="custom",
                    install=custom_override["commands"].get("install", method.install),
                    upgrade=custom_override["commands"].get("upgrade", method.upgrade),
                    version=custom_override["commands"].get("version", method.version),
                    check_latest=custom_override["commands"].get(
                        "check_latest", method.check_latest
                    ),
                    dependencies=method.dependencies,
                    risk_level=_infer_risk_level(
                        custom_override["commands"].get("install", method.install)
                    ),
                )
            return method

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
    "Dependency",
    "Harness",
    "InstallMethod",
    "Preset",
    "PlanStep",
    "Plan",
    "StepResult",
    "get_all_dependencies",
    "get_dependency",
    "scan_dependencies",
    "resolve_method",
    "plan_install",
    "render_plan",
    "apply_plan",
]

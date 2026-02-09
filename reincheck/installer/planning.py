"""Installation planning and rendering."""

from typing import Any

from reincheck.execution import INSTALL_TIMEOUT

from .dependencies import RiskLevel, scan_dependencies
from .models import InstallMethod, Plan, PlanStep, Preset
from .resolution import resolve_method


def plan_install(
    preset: Preset,
    harnesses: list[str],
    methods: dict[str, InstallMethod],
    overrides: dict[str, Any] | None = None,
) -> Plan:
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
    lines = [f"Installation Plan: {plan.preset_name}", ""]

    if plan.unsatisfied_deps:
        lines.append("⚠️  Missing dependencies:")
        from .dependencies import get_dependency

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


__all__ = [
    "plan_install",
    "render_plan",
]

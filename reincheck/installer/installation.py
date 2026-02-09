"""Installation execution and confirmation."""

import click

from reincheck import run_command_async

from .dependencies import PresetStatus, RiskLevel, get_dependency
from .models import Plan, StepResult


def _confirm(message: str) -> bool:
    return click.confirm(message, default=False)


def confirm_installation(
    plan: Plan,
    preset_status: PresetStatus,
    skip_confirmation: bool = False,
) -> bool:
    has_dangerous = bool(plan.risky_steps)
    if skip_confirmation and preset_status == PresetStatus.GREEN and not has_dangerous:
        return True

    click.echo("")
    click.echo("=" * 60)
    click.echo(f"Installation Summary: {plan.preset_name}")
    click.echo("=" * 60)
    click.echo("")
    click.echo(f"  Harnesses to install: {len(plan.steps)}")
    click.echo(f"  Commands to execute: {len(plan.steps)}")

    if preset_status != PresetStatus.GREEN:
        click.echo("")
        if preset_status == PresetStatus.PARTIAL:
            click.secho("  ⚠️  WARNING: Partial dependencies", fg="yellow", bold=True)
            click.secho(
                "      Some dependencies are missing or have version issues.",
                fg="yellow",
            )
        elif preset_status == PresetStatus.RED:
            click.secho("  ❌ WARNING: Missing dependencies", fg="red", bold=True)
            click.secho(
                "      Critical dependencies are missing. Installation may fail.",
                fg="red",
            )

        if plan.unsatisfied_deps:
            click.echo("")
            click.echo("  Missing dependencies:")
            for dep in plan.unsatisfied_deps:
                dep_obj = get_dependency(dep)
                hint = dep_obj.install_hint if dep_obj else "Unknown"
                click.echo(f"    • {dep}: {hint}")

    if has_dangerous:
        click.echo("")
        click.secho("  🔴 DANGEROUS: curl|sh commands detected", fg="red", bold=True)
        click.secho(
            "      The following will execute remote scripts via curl|sh:",
            fg="red",
        )
        for harness in plan.risky_steps:
            click.echo(f"      • {harness}")
        click.echo("")
        click.secho(
            "      ⚠️  Review these commands carefully before proceeding!",
            fg="yellow",
        )

    click.echo("")
    click.echo("=" * 60)

    if has_dangerous:
        return click.confirm(
            "\n⚠️  DANGEROUS commands detected. Continue anyway?",
            default=False,
        )

    return click.confirm("\nContinue with installation?", default=False)


async def apply_plan(
    plan: Plan, dry_run: bool = False, skip_confirmation: bool = False
) -> list[StepResult]:
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
    "confirm_installation",
    "apply_plan",
]

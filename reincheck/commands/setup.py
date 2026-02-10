"""Setup command implementation."""

import asyncio
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import click

from reincheck import (
    ConfigError,
    format_error,
    run_command_async,
    setup_logging,
)
from reincheck.data_loader import get_all_methods, get_harnesses, get_presets
from reincheck.installer import (
    DependencyReport,
    Harness,
    InstallMethod,
    Plan,
    Preset,
    RiskLevel,
    StepResult,
    get_dependency,
    get_dependency_report,
    plan_install,
    render_plan,
    resolve_method,
)
from reincheck.paths import get_config_path
from reincheck.tui import (
    resolve_failed_harnesses_interactive,
    select_harnesses_interactive,
    select_preset_interactive,
)

_logging = logging.getLogger(__name__)

# Exit codes
EXIT_SUCCESS = 0
EXIT_INVALID_ARGS = 2
EXIT_PRESET_NOT_FOUND = 3
EXIT_CONFIG_ERROR = 4
EXIT_INSTALL_FAILED = 5


@dataclass
class SetupContext:
    """Shared context for setup workflow."""
    presets: dict[str, Preset]
    available_harnesses: dict[str, Harness]
    all_methods: dict[str, InstallMethod]
    overrides: dict[str, str]
    debug: bool
    yes: bool
    verbose: bool


def _validate_setup_options(
    list_presets: bool,
    preset: str | None,
    override: tuple[str, ...],
    harness: tuple[str, ...],
    dry_run: bool,
    apply: bool,
    yes: bool,
) -> None:
    """Validate setup command options.

    Raises:
        click.BadArgumentUsage: If options are invalid
    """
    from reincheck.data_loader import get_harnesses

    # --list-presets is standalone
    if list_presets:
        if any([preset, override, harness, dry_run, apply]):
            raise click.BadArgumentUsage(
                "--list-presets cannot be used with other options"
            )
        return

    # Allow preset to be None for interactive mode (TTY available)
    # Will be validated again after interactive selection
    if preset is None and not sys.stdin.isatty():
        click.echo(format_error("--preset is required"), err=True)
        sys.exit(EXIT_CONFIG_ERROR)

    # --override required for custom preset
    if preset == "custom" and not override:
        raise click.BadArgumentUsage(
            "preset 'custom' requires at least one --override\n"
            "Example: reincheck setup --preset custom --override claude=language_native\n\n"
            "Available methods depend on the preset. Use --list-presets to see available presets.\n"
            "Common method names: mise_binary, mise_language, language_native, homebrew"
        )

    # --apply requires --harness
    if apply and not harness:
        raise click.BadArgumentUsage(
            "--apply requires --harness\n"
            "Specify harnesses to install or use --harness ALL"
        )

    # Validate --harness values
    available = get_harnesses()
    for h in harness:
        if h != "ALL" and h not in available:
            available_names = ", ".join(sorted(available.keys()))
            raise click.BadOptionUsage(
                "--harness", f"Unknown harness '{h}'. Available: {available_names}"
            )


def _parse_overrides(override_options: tuple[str, ...]) -> dict[str, str]:
    """Parse --override options into overrides dictionary.

    Args:
        override_options: Tuple of "harness=method" strings

    Returns:
        Dict mapping harness name to method name

    Raises:
        click.BadOptionUsage: If format is invalid
    """
    overrides = {}
    for opt in override_options:
        if "=" not in opt:
            raise click.BadOptionUsage(
                "--override", f"Invalid override format: '{opt}'. Use harness=method"
            )
        harness, method = opt.split("=", 1)
        harness = harness.strip()
        method = method.strip()
        if not harness or not method:
            raise click.BadOptionUsage(
                "--override",
                f"Invalid override format: '{opt}'. Both harness and method must be non-empty",
            )
        overrides[harness] = method
    return overrides


def _list_presets_with_status(debug: bool = False) -> None:
    """List all available presets with dependency status.

    Args:
        debug: Enable debug output
    """
    from reincheck.data_loader import get_presets, get_all_methods
    from reincheck.installer import get_dependency_report

    from reincheck import setup_logging

    setup_logging(debug)

    presets = get_presets()
    methods = get_all_methods()
    report = get_dependency_report(presets, methods)

    click.echo("Available presets (sorted by priority):")
    click.echo("")

    # Sort presets by priority field if available, otherwise by name
    sorted_presets = sorted(presets.values(), key=lambda p: (p.priority, p.name))

    for preset in sorted_presets:
        status = report.preset_statuses.get(preset.name)
        if status:
            status_icon = {"green": "✅", "partial": "⚠️ ", "red": "❌"}.get(
                status.value, "❓"
            )
            click.echo(f"{status_icon} {preset.name:12s} - {preset.description}")

    click.echo("")
    if report.missing_deps:
        click.echo("Missing dependencies:")
        for dep in report.missing_deps:
            from reincheck.installer import get_dependency

            dep_obj = get_dependency(dep)
            hint = dep_obj.install_hint if dep_obj else "Unknown"
            click.echo(f"  • {dep}: {hint}")
        click.echo("")

    click.echo("Run 'reincheck setup --preset <name> --dry-run' to preview changes.")


def _select_preset_interactive_with_fallback(
    presets: dict[str, Preset],
    report: DependencyReport,
    debug: bool = False,
) -> str | None:
    """Select preset interactively or return None if not possible.

    Args:
        presets: Available presets
        report: Dependency report with statuses
        debug: Enable debug output

    Returns:
        Selected preset name, or None if cannot select interactively
    """
    import sys

    # Check if we can do interactive selection
    if not sys.stdin.isatty():
        return None

    # Load methods once and pass to selector
    methods = get_all_methods()

    try:
        return select_preset_interactive(presets, report, methods=methods)
    except RuntimeError:
        # TTY not available
        return None
    except ImportError:
        # questionary not installed
        return None
    except OSError as e:
        # Terminal errors (e.g., TERM issues, encoding problems)
        if debug:
            _logging.debug(f"Terminal error in preset selection: {e}")
        return None
    except KeyboardInterrupt:
        # User interrupted with Ctrl+C
        return None


def _select_harnesses_interactive_with_fallback(
    preset: Preset,
    methods: dict,
    harnesses: dict,
    debug: bool = False,
) -> tuple[list[str], dict[str, str]] | None:
    """Select harnesses interactively or return None if not possible.

    Args:
        preset: Selected preset
        methods: All install methods
        harnesses: All harness metadata
        debug: Enable debug output

    Returns:
        Tuple of (selected_harnesses, overrides) or None if interactive
        selection is not possible.
    """
    if not sys.stdin.isatty():
        return None

    try:
        return select_harnesses_interactive(preset, methods, harnesses)
    except RuntimeError:
        return None
    except ImportError:
        return None
    except OSError as e:
        if debug:
            _logging.debug(f"Terminal error in harness selection: {e}")
        return None
    except KeyboardInterrupt:
        # User interrupted with Ctrl+C
        return None


def _resolve_all_methods(
    preset: Preset,
    overrides: dict[str, str],
    available_harnesses: dict[str, Harness],
    methods: dict[str, InstallMethod],
) -> dict[str, InstallMethod]:
    """Resolve install methods for all harnesses in preset.

    Args:
        preset: Preset to resolve methods for
        overrides: Harness→method overrides from --set
        available_harnesses: All available harnesses
        methods: All available methods

    Returns:
        Dict mapping harness name to resolved InstallMethod
    """
    resolved = {}

    # For custom preset, only include overridden harnesses
    if preset.name == "custom":
        for harness_name, method_name in overrides.items():
            if harness_name in available_harnesses:
                # Build a minimal preset for resolution
                from reincheck.installer import Preset as InstallerPreset

                temp_preset = InstallerPreset(
                    name="custom",
                    strategy="custom",
                    description="Custom preset",
                    methods={harness_name: method_name},
                )
                try:
                    resolved[harness_name] = resolve_method(
                        temp_preset, harness_name, methods, overrides
                    )
                except ValueError as e:
                    click.echo(
                        f"Warning: Could not resolve method for {harness_name}: {e}",
                        err=True,
                    )
    else:
        # For named presets, include all harnesses in preset plus overrides
        for harness_name in preset.methods.keys():
            if harness_name in available_harnesses:
                try:
                    resolved[harness_name] = resolve_method(
                        preset, harness_name, methods, overrides
                    )
                except ValueError as e:
                    click.echo(
                        f"Warning: Could not resolve method for {harness_name}: {e}",
                        err=True,
                    )

    return resolved


def _build_agent_config(
    harness: Harness,
    method: InstallMethod,
) -> dict:
    """Build agent config dict from Harness and InstallMethod.

    Args:
        harness: Harness metadata
        method: Resolved install method

    Returns:
        Dict compatible with AgentConfig/agents.json format
    """
    config = {
        "name": harness.name,
        "description": harness.description,
        "install_command": method.install,
        "upgrade_command": method.upgrade,
        "version_command": method.version,
        "check_latest_command": method.check_latest,
    }

    if harness.github_repo:
        config["github_repo"] = harness.github_repo

    if harness.release_notes_url:
        config["release_notes_url"] = harness.release_notes_url

    return config


def _write_agent_config(
    agent_configs: list[dict], config_path: Path, preset_name: str | None = None
) -> None:
    """Write agent configuration to file.

    Args:
        agent_configs: List of agent config dicts
        config_path: Path to write config file
        preset_name: Optional preset name to store as active preset

    Raises:
        ConfigError: If write fails
    """

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, object] = {"agents": agent_configs}

        # Store active preset if provided
        if preset_name:
            data["preset"] = preset_name

        # Write to temp file first
        temp_path = config_path.with_suffix(".tmp")
        with open(temp_path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        # Atomic rename
        temp_path.replace(config_path)
    except (IOError, OSError) as e:
        raise ConfigError(f"Failed to write config to {config_path}: {e}")


def _get_harnesses_to_install(
    preset: Preset,
    harness_options: tuple[str, ...],
    overrides: dict[str, str],
    available_harnesses: dict[str, Harness],
    resolved_methods: dict[str, InstallMethod] | None = None,
) -> list[str]:
    """Determine which harnesses to install based on --harness options.

    Args:
        preset: Selected preset
        harness_options: List from --harness option
        overrides: Harness method overrides
        available_harnesses: All available harnesses
        resolved_methods: Dict of harness to InstallMethod (for filtering)

    Returns:
        List of harness names to install
    """
    if not harness_options:
        return []

    # Filter harnesses by those that have resolved methods
    valid_harnesses = set(available_harnesses.keys())
    if resolved_methods:
        valid_harnesses = set(resolved_methods.keys())

    if "ALL" in harness_options:
        # Install all harnesses
        if preset.name == "custom":
            # For custom preset, install only overridden harnesses
            return [h for h in overrides.keys() if h in valid_harnesses]
        else:
            # For named presets, install all in preset plus overrides
            preset_harnesses = set(preset.methods.keys())
            preset_harnesses.update(overrides.keys())
            return [h for h in preset_harnesses if h in valid_harnesses]
    else:
        # Install specific harnesses only, filter by valid methods
        return [h for h in harness_options if h in valid_harnesses]


async def _execute_installation_with_progress(
    plan: Plan,
    skip_confirmation: bool,
    verbose: bool,
    debug: bool,
) -> list[StepResult]:
    """Execute installation plan with progress bars.

    Args:
        plan: Installation plan
        skip_confirmation: Skip user confirmations
        verbose: Show detailed command output
        debug: Enable debug logging

    Returns:
        List of step results
    """
    setup_logging(debug)
    results = []

    # Show full installation plan preview using render_plan()
    click.echo("")
    click.echo(render_plan(plan))

    # Prominent curl|sh warning summary if any dangerous steps
    dangerous_count = sum(
        1 for step in plan.steps if step.risk_level == RiskLevel.DANGEROUS
    )
    if dangerous_count > 0:
        click.echo("")
        click.echo("=" * 60)
        click.echo("⚠️  SECURITY WARNING")
        click.echo("=" * 60)
        click.echo(f"This installation plan contains {dangerous_count} harness(es)")
        click.echo("that will execute remote scripts via curl|sh.")
        click.echo("")
        click.echo("These commands will download and execute code from internet.")
        click.echo("Please review each command carefully before confirming.")
        click.echo("=" * 60)

    if not skip_confirmation:
        click.echo("")
        if not click.confirm("Proceed with installation?", default=False):
            click.echo("Installation cancelled.")
            sys.exit(EXIT_SUCCESS)

    click.echo("")
    click.echo("Installing harnesses...")

    with click.progressbar(
        plan.steps,
        label="",
        show_pos=True,
        show_eta=True,
        item_show_func=lambda item: f" {item.harness}" if item else "",
    ) as bar:
        for step in bar:
            # Dangerous command confirmation - always required regardless of skip_confirmation
            if step.risk_level == RiskLevel.DANGEROUS:
                click.echo(f"\n⚠️  DANGEROUS: About to run curl|sh for {step.harness}")
                click.echo(f"   Command: {step.command}")
                if not click.confirm(
                    "Execute this command? (review carefully)", default=False
                ):
                    results.append(StepResult(step.harness, "skipped", "User declined"))
                    continue

            # Execute installation
            try:
                output, returncode = await run_command_async(
                    step.command, timeout=step.timeout, debug=verbose
                )

                if returncode == 0:
                    results.append(StepResult(step.harness, "success", output))
                    if verbose:
                        click.echo(f"\n✅ {step.harness} installed successfully")
                else:
                    results.append(StepResult(step.harness, "failed", output))
                    click.echo(f"\n❌ {step.harness} installation failed:")
                    click.echo(f"   {output}")
            except Exception as e:
                error_msg = str(e)
                results.append(StepResult(step.harness, "failed", error_msg))
                click.echo(f"\n❌ {step.harness} installation failed: {error_msg}")

    return results


def _load_setup_data(debug: bool = False) -> tuple[
    dict[str, Preset], dict[str, Harness], dict[str, InstallMethod]
]:
    """Load required data for setup workflow.

    Args:
        debug: Enable debug logging

    Returns:
        Tuple of (presets, harnesses, methods)

    Raises:
        ConfigError: If data loading fails
    """
    setup_logging(debug)
    try:
        presets = get_presets()
        available_harnesses = get_harnesses()
        all_methods = get_all_methods()
        return presets, available_harnesses, all_methods
    except Exception as e:
        raise ConfigError(f"Error loading data: {e}")


def _resolve_selected_preset(
    preset_name: str | None,
    presets: dict[str, Preset],
    all_methods: dict[str, InstallMethod],
    debug: bool = False,
) -> Preset:
    """Resolve selected preset (interactive or explicit).

    Args:
        preset_name: Explicit preset name or None for interactive
        presets: Available presets
        all_methods: All install methods
        debug: Enable debug output

    Returns:
        Resolved Preset object

    Raises:
        ConfigError: If preset resolution fails
    """
    if preset_name is None:
        report = get_dependency_report(presets, all_methods)
        selected = _select_preset_interactive_with_fallback(presets, report, debug)

        if selected is None:
            raise ConfigError(
                "--preset is required (or use interactive mode). "
                "Run 'reincheck setup --list-presets' to see available presets."
            )

        preset_name = selected
        click.echo(f"Selected preset: {preset_name}")
        click.echo("")

    selected_preset = presets.get(preset_name)

    if not selected_preset:
        if preset_name == "custom":
            from reincheck.installer import Preset as InstallerPreset

            selected_preset = InstallerPreset(
                name="custom",
                strategy="custom",
                description="Custom configuration with overrides",
                methods={},
            )
        else:
            available_names = ", ".join(sorted(presets.keys()))
            raise ConfigError(
                f"Preset '{preset_name}' not found. Available presets: {available_names}"
            )

    return selected_preset


def _resolve_install_methods(
    preset: Preset,
    ctx: SetupContext,
) -> dict[str, InstallMethod]:
    """Resolve install methods with interactive fix for failed harnesses.

    Args:
        preset: Selected preset
        ctx: Setup context containing all required data

    Returns:
        Dict mapping harness name to resolved InstallMethod
    """
    resolved_methods = _resolve_all_methods(
        preset, ctx.overrides, ctx.available_harnesses, ctx.all_methods
    )

    if not sys.stdin.isatty() or ctx.yes:
        return resolved_methods

    expected_harnesses = set()
    if preset.name == "custom":
        expected_harnesses = {
            h for h in ctx.overrides.keys() if h in ctx.available_harnesses
        }
    else:
        expected_harnesses = {
            h for h in preset.methods.keys() if h in ctx.available_harnesses
        }

    failed_harnesses = list(expected_harnesses - set(resolved_methods.keys()))
    failed_harnesses.sort()

    if not failed_harnesses:
        return resolved_methods

    click.echo("")
    click.secho(
        f"⚠️  Could not resolve install methods for {len(failed_harnesses)} harnesses.",
        fg="yellow",
    )

    dep_report = get_dependency_report(ctx.presets, ctx.all_methods)
    new_overrides = resolve_failed_harnesses_interactive(
        failed_harnesses, ctx.all_methods, ctx.available_harnesses, dep_report
    )

    if new_overrides:
        ctx.overrides.update(new_overrides)
        click.echo("Retrying resolution with selected methods...")
        resolved_methods = _resolve_all_methods(
            preset, ctx.overrides, ctx.available_harnesses, ctx.all_methods
        )

    return resolved_methods


def _apply_interactive_harness_selection(
    preset: Preset,
    overrides: dict[str, str],
    all_methods: dict[str, InstallMethod],
    available_harnesses: dict[str, Harness],
    debug: bool = False,
) -> tuple[Preset, dict[str, str]] | None:
    """Apply interactive harness selection if possible.

    Args:
        preset: Selected preset
        overrides: Existing overrides
        all_methods: All install methods
        available_harnesses: Available harnesses
        debug: Enable debug output

    Returns:
        Tuple of (updated_preset, merged_overrides) or None if interactive not available
    """
    if not sys.stdin.isatty():
        return None

    interactive_selection = _select_harnesses_interactive_with_fallback(
        preset, all_methods, available_harnesses, debug
    )

    if interactive_selection is None:
        return None

    selected_harnesses, interactive_overrides = interactive_selection

    if not selected_harnesses:
        click.echo("No harnesses selected. Cancelled.")
        sys.exit(EXIT_SUCCESS)

    merged_overrides = overrides.copy()
    for k, v in interactive_overrides.items():
        if k not in merged_overrides:
            merged_overrides[k] = v

    from reincheck.installer import Preset as InstallerPreset

    updated_preset = InstallerPreset(
        name=preset.name,
        strategy=preset.strategy,
        description=preset.description,
        methods={
            h: preset.methods[h]
            for h in selected_harnesses
            if h in preset.methods
        },
        fallback_strategy=preset.fallback_strategy,
        priority=preset.priority,
    )

    return updated_preset, merged_overrides


def _display_dry_run(
    preset_name: str,
    selected_preset: Preset,
    agent_configs: list[dict],
    harness_options: tuple[str, ...],
    ctx: SetupContext,
    resolved_methods: dict[str, InstallMethod],
) -> None:
    """Display dry-run preview.

    Args:
        preset_name: Preset name
        selected_preset: Selected preset
        agent_configs: Generated agent configs
        harness_options: Harness options from CLI
        ctx: Setup context
        resolved_methods: Resolved methods
    """
    harness_list = ", ".join(c["name"] for c in agent_configs)
    click.echo(f"[DRY-RUN] Would generate config from preset '{preset_name}':")
    click.echo(f"  Configuring {len(agent_configs)} harnesses")
    click.echo(f"  Harnesses: {harness_list}")

    if not harness_options:
        click.echo("")
        click.echo("[DRY-RUN] No changes made.")
        click.echo("Run 'reincheck setup --preset <name> --apply' to execute.")
        return

    harnesses_to_install = _get_harnesses_to_install(
        selected_preset,
        harness_options,
        ctx.overrides,
        ctx.available_harnesses,
        resolved_methods,
    )

    if not harnesses_to_install:
        click.echo("")
        click.echo("[DRY-RUN] No changes made.")
        click.echo("Run 'reincheck setup --preset <name> --apply' to execute.")
        return

    click.echo("")
    click.echo("=" * 60)
    click.echo("INSTALLATION PLAN PREVIEW")
    click.echo("=" * 60)

    try:
        plan = plan_install(
            selected_preset, harnesses_to_install, ctx.all_methods, ctx.overrides
        )
        click.echo(render_plan(plan))
    except Exception as e:
        click.echo("  [DRY-RUN] Would install harnesses:")
        harness_install_list = ", ".join(harnesses_to_install)
        click.echo(f"    {harness_install_list}")
        if ctx.debug:
            click.echo(f"  Error generating plan: {e}")

    click.echo("=" * 60)
    click.echo("")
    click.echo("[DRY-RUN] No changes made.")
    click.echo("Run 'reincheck setup --preset <name> --apply' to execute.")


def _write_config_with_backup(
    agent_configs: list[dict],
    preset_name: str,
    yes: bool = False,
) -> bool:
    """Write config with backup handling.

    Args:
        agent_configs: Agent configs to write
        preset_name: Preset name to store
        yes: Skip confirmation

    Returns:
        True if config was written, False if user cancelled

    Raises:
        ConfigError: If write fails
    """
    config_path = get_config_path(create=True)

    if config_path.exists():
        backup_path = config_path.with_suffix(".json.bak")
        click.echo(f"⚠️  Existing config will be backed up to {backup_path}")
        if not yes:
            if not click.confirm("Continue?", default=False):
                click.echo("Cancelled.")
                return False
        config_path.rename(backup_path)

    try:
        _write_agent_config(agent_configs, config_path, preset_name=preset_name)
        click.echo(f"✅ Configured {len(agent_configs)} harnesses")
        harness_list = ", ".join(c["name"] for c in agent_configs)
        if len(harness_list) <= 60:
            click.echo(f"  {harness_list}")
        else:
            click.echo(
                f"  {', '.join(c['name'] for c in agent_configs[:5])}, ... ({len(agent_configs)} total)"
            )
    except Exception as e:
        raise ConfigError(f"Failed to write config: {e}")

    return True


async def _execute_installation_flow(
    preset: Preset,
    harness_options: tuple[str, ...],
    ctx: SetupContext,
    resolved_methods: dict[str, InstallMethod],
) -> None:
    """Execute installation workflow.

    Args:
        preset: Selected preset
        harness_options: Harness options from CLI
        ctx: Setup context
        resolved_methods: Resolved install methods

    Raises:
        ConfigError: If installation fails
    """
    harnesses_to_install = _get_harnesses_to_install(
        preset, harness_options, ctx.overrides, ctx.available_harnesses, resolved_methods
    )

    if not harnesses_to_install:
        click.echo("")
        click.echo(
            "No harnesses selected for installation (use --harness and --apply to install)"
        )
        return

    try:
        plan = plan_install(preset, harnesses_to_install, ctx.all_methods, ctx.overrides)
    except Exception as e:
        raise ConfigError(f"Error generating installation plan: {e}")

    if plan.unsatisfied_deps and not ctx.yes:
        click.echo("")
        click.echo("⚠️  Missing dependencies:")

        for dep in plan.unsatisfied_deps:
            dep_obj = get_dependency(dep)
            hint = dep_obj.install_hint if dep_obj else "Unknown"
            click.echo(f"  • {dep}: {hint}")
        click.echo("")
        if not click.confirm(
            "Dependencies missing. Continue anyway?", default=False
        ):
            click.echo("Installation cancelled.")
            return

    try:
        results = await _execute_installation_with_progress(
            plan, ctx.yes, ctx.verbose, ctx.debug
        )
    except Exception as e:
        raise ConfigError(f"Error during installation: {e}")

    click.echo("")
    successful = [r for r in results if r.status == "success"]
    failed = [r for r in results if r.status == "failed"]

    if failed:
        click.echo(f"❌ Installation failed for {len(failed)} harness(es):")
        for r in failed:
            click.echo(f"  • {r.harness}: {r.output[:100]}")
        raise ConfigError(f"Installation failed for {len(failed)} harness(es)")
    else:
        click.echo(f"✅ Installation complete ({len(successful)}/{len(results)})")


@click.command()
@click.option("--list-presets", is_flag=True, help="List available presets")
@click.option("--preset", type=str, help="Preset to generate config from")
@click.option(
    "--override",
    type=str,
    multiple=True,
    help="Override install method: harness=method (e.g., cline=language_native)",
)
@click.option(
    "--harness",
    type=str,
    multiple=True,
    help="Harness to install (repeatable, use ALL for all)",
)
@click.option("--dry-run", is_flag=True, help="Preview changes")
@click.option("--apply", is_flag=True, help="Execute installation")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmations")
@click.option("--verbose", "-v", is_flag=True, help="Detailed output")
@click.pass_context
def setup(
    ctx,
    list_presets: bool,
    preset: str | None,
    override: tuple[str, ...],
    harness: tuple[str, ...],
    dry_run: bool,
    apply: bool,
    yes: bool,
    verbose: bool,
):
    """Generate agents.json config and optionally install harnesses."""
    debug = ctx.obj.get("debug", False)

    _validate_setup_options(
        list_presets, preset, override, harness, dry_run, apply, yes
    )

    if list_presets:
        _list_presets_with_status(debug)
        return

    try:
        presets, available_harnesses, all_methods = _load_setup_data(debug)
    except ConfigError as e:
        click.echo(format_error(str(e)), err=True)
        sys.exit(EXIT_CONFIG_ERROR)

    overrides = _parse_overrides(override)

    ctx_obj = SetupContext(
        presets=presets,
        available_harnesses=available_harnesses,
        all_methods=all_methods,
        overrides=overrides,
        debug=debug,
        yes=yes,
        verbose=verbose,
    )

    try:
        selected_preset = _resolve_selected_preset(preset, presets, all_methods, debug)
    except ConfigError as e:
        click.echo(format_error(str(e)), err=True)
        sys.exit(EXIT_PRESET_NOT_FOUND)

    interactive_result = _apply_interactive_harness_selection(
        selected_preset,
        overrides,
        all_methods,
        available_harnesses,
        debug,
    )
    if interactive_result:
        selected_preset, overrides = interactive_result
        ctx_obj.overrides = overrides

    resolved_methods = _resolve_install_methods(selected_preset, ctx_obj)

    if not resolved_methods:
        click.echo(format_error("no valid install methods found for any harnesses"), err=True)
        sys.exit(EXIT_CONFIG_ERROR)

    click.echo(f"Generating agents.json from preset '{selected_preset.name}'...")

    agent_configs = []
    for harness_name, method in resolved_methods.items():
        harness_obj = available_harnesses[harness_name]
        agent_config = _build_agent_config(harness_obj, method)
        agent_configs.append(agent_config)

    agent_configs.sort(key=lambda c: c["name"])

    if dry_run:
        _display_dry_run(
            selected_preset.name,
            selected_preset,
            agent_configs,
            harness,
            ctx_obj,
            resolved_methods,
        )
        return

    config_written = _write_config_with_backup(agent_configs, selected_preset.name, yes)
    if not config_written:
        sys.exit(EXIT_SUCCESS)

    if apply:
        try:
            asyncio.run(
                _execute_installation_flow(
                    selected_preset,
                    harness,
                    ctx_obj,
                    resolved_methods,
                )
            )
        except ConfigError as e:
            click.echo(format_error(str(e)), err=True)
            sys.exit(EXIT_INSTALL_FAILED)
    else:
        click.echo("")
        click.echo(
            "No harnesses selected for installation (use --harness and --apply to install)"
        )

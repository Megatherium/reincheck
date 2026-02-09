"""Setup command implementation."""

import asyncio
import json
import logging
import sys
from pathlib import Path

import click

from reincheck import (
    ConfigError,
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
        click.echo("Error: --preset is required.", err=True)
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
    from reincheck import ConfigError

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
    setup_logging(debug)

    # Validate options
    _validate_setup_options(
        list_presets, preset, override, harness, dry_run, apply, yes
    )

    # List presets
    if list_presets:
        _list_presets_with_status(debug)
        return

    # Load data (needed for preset selection and validation)
    try:
        presets = get_presets()
        available_harnesses = get_harnesses()
        all_methods = get_all_methods()
    except Exception as e:
        click.echo(f"Error loading data: {e}", err=True)
        sys.exit(EXIT_CONFIG_ERROR)

    # Interactive preset selection if not provided
    if preset is None:
        report = get_dependency_report(presets, all_methods)
        selected = _select_preset_interactive_with_fallback(presets, report, debug)

        if selected is None:
            click.echo(
                "Error: --preset is required (or use interactive mode).", err=True
            )
            click.echo(
                "Run 'reincheck setup --list-presets' to see available presets.",
                err=True,
            )
            sys.exit(EXIT_CONFIG_ERROR)

        preset = selected
        click.echo(f"Selected preset: {preset}")
        click.echo("")

    # Validate options (now that we have preset)
    _validate_setup_options(
        list_presets, preset, override, harness, dry_run, apply, yes
    )

    # Parse overrides
    overrides = _parse_overrides(override)

    # Get preset
    selected_preset = presets.get(preset)

    if not selected_preset:
        # Check if it's "custom" special keyword
        if preset == "custom":
            # Will be handled below after parsing overrides
            pass
        else:
            available_names = ", ".join(sorted(presets.keys()))
            click.echo(f"Error: Preset '{preset}' not found.", err=True)
            click.echo(f"Available presets: {available_names}", err=True)
            sys.exit(EXIT_PRESET_NOT_FOUND)

    # Resolve methods and build config
    click.echo(f"Generating agents.json from preset '{preset}'...")

    # For custom preset, create a temporary preset object for resolution
    if preset == "custom":
        from reincheck.installer import Preset as InstallerPreset

        selected_preset = InstallerPreset(
            name="custom",
            strategy="custom",
            description="Custom configuration with overrides",
            methods={},
        )

    if selected_preset is None:
        click.echo("Error: Preset resolution failed.", err=True)
        sys.exit(EXIT_CONFIG_ERROR)

    # Interactive harness selection (when no --harness flags and TTY available)
    interactive_harness_selection = None
    if not harness and not yes and preset != "custom" and sys.stdin.isatty():
        interactive_harness_selection = _select_harnesses_interactive_with_fallback(
            selected_preset, all_methods, available_harnesses, debug
        )

        if interactive_harness_selection is not None:
            selected_h, interactive_overrides = interactive_harness_selection
            if not selected_h:
                click.echo("No harnesses selected. Cancelled.")
                sys.exit(EXIT_SUCCESS)
            # Merge: CLI --override flags take precedence over interactive
            for k, v in interactive_overrides.items():
                if k not in overrides:
                    overrides[k] = v
            # Narrow preset methods to only selected harnesses
            from reincheck.installer import Preset as InstallerPreset

            selected_preset = InstallerPreset(
                name=selected_preset.name,
                strategy=selected_preset.strategy,
                description=selected_preset.description,
                methods={
                    h: selected_preset.methods[h]
                    for h in selected_h
                    if h in selected_preset.methods
                },
                fallback_strategy=selected_preset.fallback_strategy,
                priority=selected_preset.priority,
            )

    resolved_methods = _resolve_all_methods(
        selected_preset, overrides, available_harnesses, all_methods
    )

    # Check for failed resolutions and offer interactive fix
    if sys.stdin.isatty() and not yes:
        expected_harnesses = set()
        if selected_preset.name == "custom":
            expected_harnesses = {
                h for h in overrides.keys() if h in available_harnesses
            }
        else:
            expected_harnesses = {
                h for h in selected_preset.methods.keys() if h in available_harnesses
            }

        failed_harnesses = list(expected_harnesses - set(resolved_methods.keys()))
        failed_harnesses.sort()

        if failed_harnesses:
            click.echo("")
            click.secho(
                f"⚠️  Could not resolve install methods for {len(failed_harnesses)} harnesses.",
                fg="yellow",
            )

            # We need to pass presets to get_dependency_report, checking if it's available
            # It should be available from earlier in the function
            dep_report = get_dependency_report(presets, all_methods)

            new_overrides = resolve_failed_harnesses_interactive(
                failed_harnesses, all_methods, available_harnesses, dep_report
            )

            if new_overrides:
                overrides.update(new_overrides)
                click.echo("Retrying resolution with selected methods...")
                resolved_methods = _resolve_all_methods(
                    selected_preset, overrides, available_harnesses, all_methods
                )

    if not resolved_methods:
        click.echo("Error: No valid install methods found for any harnesses.", err=True)
        sys.exit(EXIT_CONFIG_ERROR)

    # Build agent configs
    agent_configs = []
    for harness_name, method in resolved_methods.items():
        harness_obj = available_harnesses[harness_name]
        agent_config = _build_agent_config(harness_obj, method)
        agent_configs.append(agent_config)

    # Sort by name for consistency
    agent_configs.sort(key=lambda c: c["name"])

    # Dry-run mode
    if dry_run:
        harness_list = ", ".join(c["name"] for c in agent_configs)
        click.echo(f"[DRY-RUN] Would generate config from preset '{preset}':")
        click.echo(f"  Configuring {len(agent_configs)} harnesses")
        click.echo(f"  Harnesses: {harness_list}")

        # Show installation plan if harnesses specified
        if harness:
            harnesses_to_install = _get_harnesses_to_install(
                selected_preset,
                harness,
                overrides,
                available_harnesses,
                resolved_methods,
            )

            if harnesses_to_install:
                click.echo("")
                click.echo("=" * 60)
                click.echo("INSTALLATION PLAN PREVIEW")
                click.echo("=" * 60)

                # Generate and display the full installation plan
                try:
                    plan = plan_install(
                        selected_preset, harnesses_to_install, all_methods, overrides
                    )
                    click.echo(render_plan(plan))
                except Exception as e:
                    click.echo(f"  [DRY-RUN] Would install harnesses:")
                    harness_install_list = ", ".join(harnesses_to_install)
                    click.echo(f"    {harness_install_list}")
                    if debug:
                        click.echo(f"  Error generating plan: {e}")

                click.echo("=" * 60)

        click.echo("")
        click.echo("[DRY-RUN] No changes made.")
        click.echo("Run 'reincheck setup --preset <name> --apply' to execute.")
        return

    # Write config
    config_path = get_config_path(create=True)

    # Warn if overwriting
    if config_path.exists():
        backup_path = config_path.with_suffix(".json.bak")
        click.echo(f"⚠️  Existing config will be backed up to {backup_path}")
        if not yes:
            if not click.confirm("Continue?", default=False):
                click.echo("Cancelled.")
                sys.exit(EXIT_SUCCESS)
        config_path.rename(backup_path)

    try:
        _write_agent_config(agent_configs, config_path, preset_name=preset)
        click.echo(f"✅ Configured {len(agent_configs)} harnesses")
        harness_list = ", ".join(c["name"] for c in agent_configs)
        if len(harness_list) <= 60:
            click.echo(f"  {harness_list}")
        else:
            click.echo(
                f"  {', '.join(c['name'] for c in agent_configs[:5])}, ... ({len(agent_configs)} total)"
            )
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(EXIT_CONFIG_ERROR)

    # Installation
    if apply:
        harnesses_to_install = _get_harnesses_to_install(
            selected_preset, harness, overrides, available_harnesses, resolved_methods
        )

        if not harnesses_to_install:
            click.echo("")
            click.echo(
                "No harnesses selected for installation (use --harness and --apply to install)"
            )
            return

        # Generate installation plan
        try:
            plan = plan_install(
                selected_preset, harnesses_to_install, all_methods, overrides
            )
        except Exception as e:
            click.echo(f"Error generating installation plan: {e}", err=True)
            sys.exit(EXIT_CONFIG_ERROR)

        # Check for missing dependencies
        if plan.unsatisfied_deps and not yes:
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
                sys.exit(EXIT_SUCCESS)

        # Execute installation
        try:
            results = asyncio.run(
                _execute_installation_with_progress(plan, yes, verbose, debug)
            )
        except Exception as e:
            click.echo(f"\nError during installation: {e}", err=True)
            sys.exit(EXIT_INSTALL_FAILED)

        # Report results
        click.echo("")
        successful = [r for r in results if r.status == "success"]
        failed = [r for r in results if r.status == "failed"]

        if failed:
            click.echo(f"❌ Installation failed for {len(failed)} harness(es):")
            for r in failed:
                click.echo(f"  • {r.harness}: {r.output[:100]}")
            sys.exit(EXIT_INSTALL_FAILED)
        else:
            click.echo(f"✅ Installation complete ({len(successful)}/{len(results)})")
    else:
        click.echo("")
        click.echo(
            "No harnesses selected for installation (use --harness and --apply to install)"
        )

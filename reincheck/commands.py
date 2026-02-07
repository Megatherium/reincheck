"""CLI command definitions for reincheck."""

import asyncio
import click
import json
import os
import subprocess
import sys
import uuid
import logging
from pathlib import Path

from reincheck import (
    load_config,
    get_current_version,
    fetch_release_notes,
    run_command_async,
    AgentConfig,
    save_config,
    compare_versions,
    INSTALL_TIMEOUT,
    ConfigError,
)

from reincheck.adapter import get_effective_method_from_config, list_available_methods

# Import path helpers
from reincheck.paths import get_config_path

# Import migration helpers
# from reincheck.migration import ensure_user_config

# Import load_config from config module directly for the fmt command
from reincheck.config import load_config as load_config_raw

# Import installer types for setup command (forward references used in annotations)
from reincheck.installer import (
    Harness,
    InstallMethod,
    Preset,
    Plan,
    StepResult,
    DependencyReport,
)

_logging = logging.getLogger(__name__)


def filter_agent_by_name(agents: list[AgentConfig], name: str) -> list[AgentConfig]:
    """Filter agents list by name, returning empty list if not found."""
    return [a for a in agents if a.name == name]


def validate_pager(pager_cmd: str) -> str:
    """Validate pager command against whitelist for security.

    Args:
        pager_cmd: Pager command from environment variable or default

    Returns:
        The validated pager command

    Raises:
        ValueError: If pager command is not in the allowed list
    """
    SAFE_PAGERS = {
        "cat",
        "less",
        "more",
        "bat",
        "most",
        "pager",
    }

    # Handle absolute paths - extract base command
    if os.path.isabs(pager_cmd):
        base_cmd = os.path.basename(pager_cmd)
        if base_cmd in SAFE_PAGERS:
            return pager_cmd
        raise ValueError(
            f"Unsafe pager: '{pager_cmd}'. "
            f"Allowed commands: {', '.join(sorted(SAFE_PAGERS))}"
        )

    # Handle relative/bare commands
    if pager_cmd in SAFE_PAGERS:
        return pager_cmd

    raise ValueError(
        f"Unsafe pager: '{pager_cmd}'. "
        f"Allowed commands: {', '.join(sorted(SAFE_PAGERS))}"
    )


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug output for troubleshooting")
@click.pass_context
def cli(ctx, debug):
    """CLI tool to manage AI coding agents."""
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug


@cli.command()
@click.option("--agent", "-a", help="Check specific agent")
@click.option("--quiet", "-q", is_flag=True, help="Show only agents with updates")
@click.pass_context
def check(ctx, agent: str | None, quiet: bool):
    """Check for updates for agents."""
    debug = ctx.obj.get("debug", False)
    try:
        asyncio.run(run_check(agent, quiet, debug))
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


async def run_check(agent: str | None, quiet: bool, debug: bool):
    config = load_config()
    agents = config.agents

    if agent:
        agents = [a for a in agents if a.name == agent]
        if not agents:
            click.echo(f"Agent '{agent}' not found in configuration.", err=True)
            sys.exit(1)

    update_count = 0
    null_latest_count = 0

    for agent_config in agents:
        effective = get_effective_method_from_config(agent_config)
        effective_config = effective.to_agent_config()
        effective_config.latest_version = agent_config.latest_version

        current, status = await get_current_version(effective_config)
        latest = effective_config.latest_version

        if latest is None:
            null_latest_count += 1
            if not quiet:
                click.echo(
                    f"⚠️  {effective.name}: latest_version is null - run 'reincheck update' first"
                )
            continue

        if (
            current
            and status == "success"
            and latest
            and current.strip().lower() != "unknown"
        ):
            if compare_versions(current, latest) < 0:
                update_count += 1
                click.echo(f"🔄 {effective.name}: {current} → {latest}")
                click.echo(f"   {effective.description}")
            elif not quiet:
                click.echo(f"✅ {effective.name}: {current} (up to date)")
        elif not quiet:
            if current and current.strip().lower() != "unknown":
                click.echo(f"⚪ {effective.name}: {current} (latest: {latest})")
            else:
                click.echo(f"⚪ {effective.name}: Not installed")

    if null_latest_count > 0 and not quiet:
        click.echo(
            f"\n⚠️  {null_latest_count} agent(s) have null latest_version - run 'reincheck update' first"
        )

    if update_count > 0:
        click.echo(f"\n{update_count} agent(s) have updates available.")
    else:
        click.echo("\nAll agents are up to date.")


@cli.command()
@click.option("--agent", "-a", help="Update specific agent")
@click.option("--quiet", "-q", is_flag=True, help="Suppress output")
@click.pass_context
def update(ctx, agent: str | None, quiet: bool):
    """Update latest version info for agents."""
    debug = ctx.obj.get("debug", False)
    try:
        asyncio.run(run_update(agent, quiet, debug))
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


async def run_update(agent: str | None, quiet: bool, debug: bool):
    from . import setup_logging, get_latest_version

    setup_logging(debug)
    config = load_config()
    agents = config.agents

    if agent:
        agents = filter_agent_by_name(agents, agent)
        if not agents:
            click.echo(f"Agent '{agent}' not found in configuration.", err=True)
            sys.exit(2)

    if not quiet:
        click.echo(f"Updating {len(agents)} agents...")

    failed_agents = []

    for agent_config in agents:
        effective = get_effective_method_from_config(agent_config)

        if debug:
            _logging.debug(
                f"Checking {agent_config.name} with command: {effective.check_latest_command}"
            )

        latest_version, status = await get_latest_version(
            check_command=effective.check_latest_command
        )

        if status == "success" and latest_version:
            agent_config.latest_version = latest_version
            if not quiet:
                click.echo(f"✅ {agent_config.name}: {latest_version}")
        else:
            failed_agents.append(agent_config.name)
            if not quiet:
                error_msg = status if status != "success" else "Unknown error"
                click.echo(f"❌ {agent_config.name}: {error_msg}")
            if debug:
                _logging.debug(f"Command: {effective.check_latest_command}")
                _logging.debug(f"Status: {status}")

    save_config(config)

    if failed_agents:
        if not quiet:
            click.echo(f"\n{len(failed_agents)} agent(s) failed to update.")
        sys.exit(1)
    else:
        if not quiet:
            click.echo("\nAll agents updated successfully.")


@cli.command()
@click.option("--agent", "-a", help="Upgrade specific agent")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be upgraded without actually upgrading",
)
@click.option(
    "--timeout", "-t", default=300, help="Command timeout in seconds (default: 300)"
)
@click.pass_context
def upgrade(ctx, agent: str | None, dry_run: bool, timeout: int):
    """Upgrade agents to latest versions."""
    debug = ctx.obj.get("debug", False)
    try:
        asyncio.run(run_upgrade(agent, dry_run, timeout, debug))
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


async def run_upgrade(agent: str | None, dry_run: bool, timeout: int, debug: bool):
    from . import setup_logging
    from .adapter import get_effective_method_from_config

    setup_logging(debug)
    config = load_config()
    agents = config.agents

    if agent:
        agents = [a for a in agents if a.name == agent]
        if not agents:
            click.echo(f"Agent '{agent}' not found in configuration.", err=True)
            sys.exit(1)

    click.echo("Checking for available updates...")

    upgradeable_agents: list[AgentConfig] = []
    from . import get_current_version, compare_versions

    for agent_config in agents:
        current, status = await get_current_version(agent_config)
        latest = agent_config.latest_version

        if (
            current
            and status == "success"
            and latest
            and current.strip().lower() != "unknown"
        ):
            if compare_versions(current, latest) < 0:
                upgradeable_agents.append(agent_config)

    if not upgradeable_agents:
        click.echo("No agents need updating.")
        return

    if dry_run:
        click.echo("The following upgrades would be performed:")
        for agent_config in upgradeable_agents:
            current, status = await get_current_version(agent_config)
            latest = agent_config.latest_version
            effective = get_effective_method_from_config(agent_config)
            click.echo(f"  {effective.name}: {current} → {latest}")
        return

    click.echo(f"Upgrading {len(upgradeable_agents)} agents...")

    async def perform_upgrade(agent_config: AgentConfig) -> tuple[str, int, str]:
        effective = get_effective_method_from_config(agent_config)
        upgrade_command = effective.upgrade_command
        if upgrade_command:
            click.echo(f"Upgrading {effective.name}...")
            if debug:
                _logging.debug(f"  Running: {upgrade_command}")
            output, returncode = await run_command_async(
                upgrade_command, timeout=timeout, debug=debug
            )
            return effective.name, returncode, output
        return effective.name, 1, "No upgrade command configured"

    upgrade_results = await asyncio.gather(
        *[perform_upgrade(a) for a in upgradeable_agents]
    )

    for name, returncode, output in upgrade_results:
        if returncode == 0:
            click.echo(f"✅ {name} upgraded successfully")
        else:
            click.echo(f"❌ {name} upgrade failed: {output}")
            if debug:
                _logging.debug(f"  Return code: {returncode}")


@cli.command()
@click.argument("agent_name")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force installation even if already installed",
)
@click.option(
    "--timeout",
    "-t",
    default=INSTALL_TIMEOUT,
    help="Command timeout in seconds (default: 600)",
)
@click.pass_context
def install(ctx, agent_name: str, force: bool, timeout: int):
    """Install a specific agent."""
    debug = ctx.obj.get("debug", False)
    try:
        asyncio.run(run_install(agent_name, force, timeout, debug))
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


async def run_install(agent_name: str, force: bool, timeout: int, debug: bool):
    from . import setup_logging
    from .adapter import get_effective_method

    setup_logging(debug)
    config = load_config()
    agents = config.agents

    agent_config = next((a for a in agents if a.name == agent_name), None)
    if not agent_config:
        click.echo(f"Agent '{agent_name}' not found in configuration.", err=True)
        sys.exit(1)

    if debug:
        _logging.debug(f"Checking current version for {agent_name}...")

    current, status = await get_current_version(agent_config)

    if status == "success" and not force:
        click.echo(f"Agent '{agent_name}' is already installed (version: {current}).")
        click.echo("Use --force to reinstall.")
        return

    # Try to get effective method from preset first, fall back to config
    install_command = None
    effective_method = None

    if config.preset:
        try:
            effective_method = get_effective_method(
                agent_name, preset_name=config.preset
            )
            if effective_method:
                install_command = effective_method.install_command
                if debug:
                    _logging.debug(
                        f"Using install command from preset '{config.preset}': {install_command}"
                    )
            else:
                # Harness not in preset - will fall back to config
                if debug:
                    _logging.debug(
                        f"Harness '{agent_name}' not found in preset '{config.preset}', falling back to config"
                    )
        except (ValueError, Exception) as e:
            # Resolution failed - fall back to config
            if debug:
                _logging.debug(
                    f"Failed to resolve method from preset: {e}, falling back to config"
                )

    # Fall back to config's install_command if preset method not available
    if install_command is None:
        install_command = agent_config.install_command
        if debug:
            _logging.debug(f"Using install command from config: {install_command}")

    if not install_command:
        click.echo(f"No install command defined for agent '{agent_name}'.", err=True)
        sys.exit(1)

    click.echo(f"Installing {agent_name}...")
    if debug:
        _logging.debug(f"  Running: {install_command}")
    output, returncode = await run_command_async(
        install_command, timeout=timeout, debug=debug
    )

    if returncode == 0:
        click.echo(f"✅ {agent_name} installed successfully")
        new_ver, _ = await get_current_version(agent_config)
        if new_ver:
            click.echo(f"Installed version: {new_ver}")
    else:
        click.echo(f"❌ {agent_name} installation failed: {output}")
        if debug:
            _logging.debug(f"  Return code: {returncode}")
        sys.exit(1)


@cli.command(name="list")
@click.option(
    "--verbose", "-v", is_flag=True, help="Show detailed information including methods"
)
@click.pass_context
def list_agents(ctx, verbose: bool):
    """List all configured agents."""
    debug = ctx.obj.get("debug", False)
    try:
        asyncio.run(run_list_agents(verbose, debug))
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


async def run_list_agents(verbose: bool, debug: bool):
    from . import setup_logging

    setup_logging(debug)
    config = load_config()
    agents = config.agents

    if not agents:
        click.echo("No agents configured.")
        return

    # Parallelize fetching current versions for all agents
    results = await asyncio.gather(*[get_current_version(agent) for agent in agents])

    if verbose:
        click.echo("Configured agents:\n")

    for i, agent in enumerate(agents):
        current, status = results[i]

        if verbose:
            # Verbose output: detailed information
            try:
                effective = get_effective_method_from_config(agent)
                method_display = effective.method.method_name
            except Exception:
                method_display = "unknown"

            click.echo(f"• {agent.name}")
            click.echo(f"  Description: {agent.description}")
            click.echo(f"  Current version: {current or 'not installed'}")
            click.echo(f"  Source: {method_display}")

            # Get available methods for this harness
            try:
                available = list_available_methods(agent.name)
            except Exception:
                available = []
            if available:
                click.echo(f"  Available methods: {', '.join(sorted(available))}")
            click.echo("")
        else:
            # Default: one line per agent
            version_str = (
                current if current and status == "success" else "not installed"
            )
            click.echo(f"{agent.name}: {version_str}")


async def run_release_notes(agent: str | None, debug: bool):
    from . import setup_logging

    setup_logging(debug)
    config = load_config()
    agents = config.agents

    if agent:
        agents = [a for a in agents if a.name == agent]
        if not agents:
            click.echo(f"Agent '{agent}' not found.", err=True)
            sys.exit(1)

    # Create releasenotes directory
    rn_dir = Path("releasenotes")
    rn_dir.mkdir(exist_ok=True)

    click.echo(f"Fetching release notes for {len(agents)} agents...")

    # First fetch current versions to validate notes
    click.echo("  Checking installed versions...")
    version_results = await asyncio.gather(*[get_current_version(a) for a in agents])

    # Pair agents with their current versions
    tasks = []
    for i, a in enumerate(agents):
        current_ver, _ = version_results[i]
        tasks.append(fetch_release_notes(a, current_ver))

    results = await asyncio.gather(*tasks)

    raw_pager = os.environ.get("REINCHECK_RN_PAGER", "cat")

    try:
        pager_cmd = validate_pager(raw_pager)
    except ValueError as e:
        click.echo(f"Security error: {e}", err=True)
        sys.exit(1)

    combined_path = rn_dir / "all_release_notes.md"

    # Clear combined file if it exists
    if combined_path.exists():
        combined_path.unlink()

    with open(combined_path, "w") as combined_f:
        for name, content in results:
            file_path = rn_dir / f"{name}.md"
            with open(file_path, "w") as f:
                f.write(content)

            # Append to combined file
            combined_f.write(f"\n\n# {name}\n\n")
            combined_f.write(content)
            combined_f.write("\n\n---\n\n")

    if agent:
        # Render the single file
        file_path = rn_dir / f"{agents[0].name}.md"
        result = subprocess.run([pager_cmd, str(file_path)], check=False)
        if result.returncode != 0:
            click.echo(f"Pager exited with code {result.returncode}", err=True)
    else:
        # Render all
        result = subprocess.run([pager_cmd, str(combined_path)], check=False)
        if result.returncode != 0:
            click.echo(f"Pager exited with code {result.returncode}", err=True)


@cli.command(name="release-notes")
@click.option("--agent", "-a", help="Get release notes for specific agent")
@click.pass_context
def release_notes(ctx, agent: str | None):
    """Fetch and display release notes."""
    debug = ctx.obj.get("debug", False)
    try:
        asyncio.run(run_release_notes(agent, debug))
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


cli.add_command(release_notes, name="rn")


# ============================================================================
# Setup command
# ============================================================================

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
    presets: dict[str, "Preset"],
    report: "DependencyReport",
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

    from reincheck.tui import select_preset_interactive
    from reincheck.data_loader import get_all_methods

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


def _select_harnesses_interactive_with_fallback(
    preset: "Preset",
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
    from reincheck.tui import select_harnesses_interactive

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


def _resolve_all_methods(
    preset: "Preset",
    overrides: dict[str, str],
    available_harnesses: dict[str, "Harness"],
    methods: dict[str, "InstallMethod"],
) -> dict[str, "InstallMethod"]:
    """Resolve install methods for all harnesses in preset.

    Args:
        preset: Preset to resolve methods for
        overrides: Harness→method overrides from --set
        available_harnesses: All available harnesses
        methods: All available methods

    Returns:
        Dict mapping harness name to resolved InstallMethod
    """
    from reincheck.installer import resolve_method

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
    harness: "Harness",
    method: "InstallMethod",
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
    preset: "Preset",
    harness_options: tuple[str, ...],
    overrides: dict[str, str],
    available_harnesses: dict[str, "Harness"],
    resolved_methods: dict[str, "InstallMethod"] | None = None,
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
    plan: "Plan",
    skip_confirmation: bool,
    verbose: bool,
    debug: bool,
) -> list["StepResult"]:
    """Execute installation plan with progress bars.

    Args:
        plan: Installation plan
        skip_confirmation: Skip user confirmations
        verbose: Show detailed command output
        debug: Enable debug logging

    Returns:
        List of step results
    """
    from reincheck.installer import StepResult, RiskLevel
    from reincheck import run_command_async, setup_logging

    setup_logging(debug)
    results = []

    # Show installation plan
    harness_names = [step.harness for step in plan.steps]
    if len(harness_names) <= 5:
        harness_list = ", ".join(harness_names)
    else:
        harness_list = (
            ", ".join(harness_names[:5]) + f", ... ({len(harness_names)} total)"
        )

    click.echo("\nInstallation plan:")
    click.echo(f"  Installing {len(plan.steps)} harness(es)")
    click.echo(f"  Harnesses: {harness_list}")

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


@cli.command()
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
    from reincheck import setup_logging
    from reincheck.data_loader import get_presets, get_harnesses, get_all_methods
    from reincheck.installer import plan_install, Preset as InstallerPreset

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
        from reincheck.installer import get_dependency_report

        report = get_dependency_report(presets, all_methods)
    except Exception as e:
        click.echo(f"Error loading data: {e}", err=True)
        sys.exit(EXIT_CONFIG_ERROR)

    # Interactive preset selection if not provided
    if preset is None:
        from reincheck.installer import get_dependency_report

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
                click.echo("[DRY-RUN] Would install harnesses:")
                harness_install_list = ", ".join(harnesses_to_install)
                click.echo(f"  {harness_install_list}")

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
        from reincheck.installer import confirm_installation, PresetStatus

        preset_status = report.preset_statuses.get(preset, PresetStatus.RED)

        # Final confirmation with warnings for non-green status and dangerous commands
        if not confirm_installation(plan, preset_status, skip_confirmation=yes):
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


# ============================================================================
# Config commands
# ============================================================================


@cli.group()
def config():
    """Configuration management commands."""
    pass


@config.command(name="fmt")
@click.argument("file", required=False, type=click.Path())
@click.option(
    "--write",
    "-w",
    is_flag=True,
    help="Overwrite the file instead of printing to stdout",
)
@click.pass_context
def config_fmt(ctx, file: str | None, write: bool):
    """Format a config file (accepts trailing commas and // comments).

    Reads a JSON config file, parses it with tolerant parsing (accepting
    trailing commas and // comments), and outputs strict JSON.

    Note: Comments are accepted on input but not preserved after formatting.

    FILE: Path to config file (default: ~/.config/reincheck/agents.json)
    """
    # Determine the file path
    if file is None:
        file_path = get_config_path(create=False)
    else:
        file_path = Path(file)

    # Check if file exists
    if not file_path.exists():
        click.echo(f"Error: File not found: {file_path}", err=True)
        sys.exit(1)

    try:
        # Load with tolerant parser (accepts trailing commas, // comments)
        data = load_config_raw(file_path)
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error reading config: {e}", err=True)
        sys.exit(1)

    # Output strict JSON
    formatted = json.dumps(data, indent=2, sort_keys=False)

    if write:
        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)
        # Write atomically with unique temp file name
        temp_path = file_path.with_suffix(f".tmp.{uuid.uuid4().hex[:8]}")
        try:
            with open(temp_path, "w") as f:
                f.write(formatted)
                f.write("\n")  # Trailing newline
            temp_path.replace(file_path)
            click.echo(f"Formatted {file_path}")
        except Exception as e:
            # Clean up temp file if it exists
            if temp_path.exists():
                temp_path.unlink()
            click.echo(f"Error writing file: {e}", err=True)
            sys.exit(1)
    else:
        click.echo(formatted)


@config.command(name="init")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force re-initialization, overwriting existing config",
)
@click.pass_context
def config_init(ctx, force: bool):
    """Initialize or re-initialize user config file.

    Creates ~/.config/reincheck/agents.json from packaged defaults.
    If a YAML config exists, it will be migrated to JSON format.

    Use --force to overwrite an existing config (creates backup first).
    """
    config_path = get_config_path(create=False)

    if config_path.exists() and not force:
        click.echo(f"Config file already exists: {config_path}")
        click.echo("Use --force to re-initialize (creates backup first).")
        sys.exit(1)

    if config_path.exists():
        backup_path = config_path.with_suffix(".json.bak")
        click.echo(f"Backing up existing config to {backup_path}...")
        config_path.rename(backup_path)
        click.echo("✅ Backup created")

    click.echo(f"Initializing config at {config_path}...")

    try:
        # If force mode, directly create from defaults or migrate
        # If normal mode (config doesn't exist), let ensure_user_config handle it
        if force:
            from reincheck import (
                get_config_dir,
                get_packaged_config_path,
                migrate_yaml_to_json,
            )

            config_dir = get_config_dir()
            yaml_path = config_dir / "agents.yaml"
            project_yaml = Path(__file__).parent.parent / "reincheck" / "agents.yaml"

            if yaml_path.exists():
                click.echo(f"⚠️  Found legacy YAML config at {yaml_path}")
                click.echo(f"   Migrating to {config_path}...")
                migrate_yaml_to_json(yaml_path, config_path)
            elif project_yaml.exists():
                click.echo(f"⚠️  Found legacy YAML config at {project_yaml}")
                click.echo(f"   Migrating to {config_path}...")
                migrate_yaml_to_json(project_yaml, config_path)
            else:
                packaged_default = get_packaged_config_path()
                if packaged_default.exists():
                    click.echo("📋 Creating user config from packaged defaults...")
                    config_path.parent.mkdir(parents=True, exist_ok=True)
                    config_path.write_text(packaged_default.read_text())
                else:
                    config_path.parent.mkdir(parents=True, exist_ok=True)
                    config_path.write_text('{"agents": []}\n')
        else:
            from reincheck import ensure_user_config

            ensure_user_config(config_path)

        click.echo("✅ Config initialized successfully")
    except ConfigError as e:
        click.echo(f"❌ Initialization failed: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()

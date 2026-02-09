"""Install command implementation."""

import asyncio
import logging
import sys

import click

from reincheck import (
    INSTALL_TIMEOUT,
    ConfigError,
    get_current_version,
    load_config,
    run_command_async,
    setup_logging,
)
from reincheck.adapter import get_effective_method


_logging = logging.getLogger(__name__)


@click.command()
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

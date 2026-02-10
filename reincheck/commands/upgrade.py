"""Upgrade command implementation."""

import asyncio
import logging
import sys

import click

from reincheck import (
    INSTALL_TIMEOUT,
    AgentConfig,
    ConfigError,
    compare_versions,
    format_error,
    get_current_version,
    load_config,
    run_command_async,
    setup_logging,
)
from reincheck.adapter import get_effective_method_from_config


_logging = logging.getLogger(__name__)


@click.command()
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
        click.echo(format_error(str(e)), err=True)
        sys.exit(1)


async def run_upgrade(agent: str | None, dry_run: bool, timeout: int, debug: bool):
    setup_logging(debug)
    config = load_config()
    agents = config.agents

    if agent:
        agents = [a for a in agents if a.name == agent]
        if not agents:
            click.echo(format_error(f"agent '{agent}' not found"), err=True)
            sys.exit(1)

    click.echo("Checking for available updates...")

    upgradeable_agents: list[AgentConfig] = []

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

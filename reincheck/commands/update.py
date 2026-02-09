"""Update command implementation."""

import asyncio
import logging
import sys

import click

from reincheck import ConfigError, get_latest_version, load_config, save_config
from reincheck.adapter import get_effective_method_from_config
from reincheck.commands.utils import filter_agent_by_name


_logging = logging.getLogger(__name__)


@click.command()
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
    from reincheck import setup_logging

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

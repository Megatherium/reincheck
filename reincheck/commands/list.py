"""List command implementation."""

import asyncio
import sys

import click

from reincheck import (
    ConfigError,
    format_error,
    get_current_version,
    load_config,
)
from reincheck.adapter import get_effective_method_from_config, list_available_methods


@click.command(name="list")
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
        click.echo(format_error(str(e)), err=True)
        sys.exit(1)


async def run_list_agents(verbose: bool, debug: bool):
    from reincheck import setup_logging

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

"""Check command implementation."""

import asyncio
import sys

import click

from reincheck import ConfigError, compare_versions, get_current_version, load_config
from reincheck.adapter import get_effective_method_from_config


@click.command()
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

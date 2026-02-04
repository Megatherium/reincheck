import asyncio
import click
import os
import subprocess
import sys
from pathlib import Path

from . import (
    load_config,
    get_current_version,
    fetch_release_notes,
    run_command_async,
    AgentConfig,
    save_config,
    set_debug,
    compare_versions,
    INSTALL_TIMEOUT,
)


def filter_agent_by_name(agents: list[AgentConfig], name: str) -> list[AgentConfig]:
    """Filter agents list by name, returning empty list if not found."""
    return [a for a in agents if a.name == name]


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
    asyncio.run(run_check(agent, quiet, debug))


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
        current, status = await get_current_version(agent_config)
        latest = agent_config.latest_version

        if latest is None:
            null_latest_count += 1
            if not quiet:
                click.echo(
                    f"⚠️  {agent_config.name}: latest_version is null - run 'reincheck update' first"
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
                click.echo(f"🔄 {agent_config.name}: {current} → {latest}")
                click.echo(f"   {agent_config.description}")
            elif not quiet:
                click.echo(f"✅ {agent_config.name}: {current} (up to date)")
        elif not quiet:
            if current and current.strip().lower() != "unknown":
                click.echo(f"⚪ {agent_config.name}: {current} (latest: {latest})")
            else:
                click.echo(f"⚪ {agent_config.name}: Not installed")

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
    asyncio.run(run_update(agent, quiet, debug))


async def run_update(agent: str | None, quiet: bool, debug: bool):
    set_debug(debug)
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
        from . import get_latest_version

        if debug:
            check_cmd = agent_config.check_latest_command
            click.echo(
                f"Checking {agent_config.name} with command: {check_cmd}", err=True
            )

        latest_version, status = await get_latest_version(agent_config)

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
                check_cmd = agent_config.check_latest_command
                click.echo(f"   Command: {check_cmd}", err=True)
                click.echo(f"   Status: {status}", err=True)

    save_config(config)

    if failed_agents:
        if not quiet:
            click.echo(f"\n{len(failed_agents)} agent(s) failed to update.")
        sys.exit(1)
    else:
        if not quiet:
            click.echo(f"\nAll agents updated successfully.")


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
    asyncio.run(run_upgrade(agent, dry_run, timeout, debug))


async def run_upgrade(agent: str | None, dry_run: bool, timeout: int, debug: bool):
    set_debug(debug)
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
            click.echo(f"  {agent_config.name}: {current} → {latest}")
        return

    click.echo(f"Upgrading {len(upgradeable_agents)} agents...")

    async def perform_upgrade(agent_config: AgentConfig) -> tuple[str, int, str]:
        upgrade_command = agent_config.upgrade_command
        if upgrade_command:
            click.echo(f"Upgrading {agent_config.name}...")
            if debug:
                click.echo(f"  Running: {upgrade_command}", err=True)
            output, returncode = await run_command_async(
                upgrade_command, timeout=timeout
            )
            return agent_config.name, returncode, output
        return agent_config.name, 1, "No upgrade command configured"

    upgrade_results = await asyncio.gather(
        *[perform_upgrade(a) for a in upgradeable_agents]
    )

    for name, returncode, output in upgrade_results:
        if returncode == 0:
            click.echo(f"✅ {name} upgraded successfully")
        else:
            click.echo(f"❌ {name} upgrade failed: {output}")
            if debug:
                click.echo(f"  Return code: {returncode}", err=True)


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
    asyncio.run(run_install(agent_name, force, timeout, debug))


async def run_install(agent_name: str, force: bool, timeout: int, debug: bool):
    set_debug(debug)
    config = load_config()
    agents = config.agents

    agent_config = next((a for a in agents if a.name == agent_name), None)
    if not agent_config:
        click.echo(f"Agent '{agent_name}' not found in configuration.", err=True)
        sys.exit(1)

    if debug:
        click.echo(f"Checking current version for {agent_name}...", err=True)

    current, status = await get_current_version(agent_config)

    if status == "success" and not force:
        click.echo(f"Agent '{agent_name}' is already installed (version: {current}).")
        click.echo("Use --force to reinstall.")
        return

    install_command = agent_config.install_command
    if not install_command:
        click.echo(f"No install command defined for agent '{agent_name}'.", err=True)
        sys.exit(1)

    click.echo(f"Installing {agent_name}...")
    if debug:
        click.echo(f"  Running: {install_command}", err=True)
    output, returncode = await run_command_async(install_command, timeout=timeout)

    if returncode == 0:
        click.echo(f"✅ {agent_name} installed successfully")
        new_ver, _ = await get_current_version(agent_config)
        if new_ver:
            click.echo(f"Installed version: {new_ver}")
    else:
        click.echo(f"❌ {agent_name} installation failed: {output}")
        if debug:
            click.echo(f"  Return code: {returncode}", err=True)
        sys.exit(1)


@cli.command(name="list")
@click.pass_context
def list_agents(ctx):
    """List all configured agents."""
    debug = ctx.obj.get("debug", False)
    asyncio.run(run_list_agents(debug))


async def run_list_agents(debug: bool):
    set_debug(debug)
    config = load_config()
    agents = config.agents

    click.echo("Configured agents:")
    click.echo("")

    # Parallelize fetching current versions for all agents
    results = await asyncio.gather(*[get_current_version(agent) for agent in agents])

    for i, agent in enumerate(agents):
        current, status = results[i]
        click.echo(f"• {agent.name}")
        click.echo(f"  {agent.description}")
        click.echo(f"  Current version: {current or 'Unknown'} ({status})")
        click.echo("")


async def run_release_notes(agent: str | None, debug: bool):
    set_debug(debug)
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

    pager_cmd = os.environ.get("REINCHECK_RN_PAGER", "cat")

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
        subprocess.run([pager_cmd, str(file_path)], check=False)
    else:
        # Render all
        subprocess.run([pager_cmd, str(combined_path)], check=False)


@cli.command(name="release-notes")
@click.option("--agent", "-a", help="Get release notes for specific agent")
@click.pass_context
def release_notes(ctx, agent: str | None):
    """Fetch and display release notes."""
    debug = ctx.obj.get("debug", False)
    asyncio.run(run_release_notes(agent, debug))


cli.add_command(release_notes, name="rn")

if __name__ == "__main__":
    cli()

import asyncio
import click
import os
import sys
from pathlib import Path

from . import (
    load_config,
    check_agent_updates,
    get_current_version,
    fetch_release_notes,
    run_command_async,
    AgentConfig,
)


@click.group()
def cli():
    """CLI tool to manage AI coding agents."""
    pass


@cli.command()
@click.option("--agent", "-a", help="Check specific agent")
@click.option("--quiet", "-q", is_flag=True, help="Show only agents with updates")
def check(agent: str | None, quiet: bool):
    """Check for updates for agents."""
    asyncio.run(run_check(agent, quiet))


async def run_check(agent: str | None, quiet: bool):
    config = load_config()
    agents = config["agents"]

    if agent:
        agents = [a for a in agents if a["name"] == agent]
        if not agents:
            click.echo(f"Agent '{agent}' not found in configuration.", err=True)
            sys.exit(1)

    click.echo(f"Checking {len(agents)} agents for updates...")

    results = await asyncio.gather(*[check_agent_updates(a) for a in agents])

    update_count = 0
    for result in results:
        if result["update_available"]:
            update_count += 1
            click.echo(
                f"🔄 {result['name']}: {result['current_version']} → {result['latest_version']}"
            )
            click.echo(f"   {result['description']}")
        elif not quiet:
            if (
                result["current_version"]
                and result["current_version"].strip().lower() != "unknown"
            ):
                click.echo(
                    f"✅ {result['name']}: {result['current_version']} (up to date)"
                )
            else:
                click.echo(f"⚪ {result['name']}: Not installed")

    if update_count > 0:
        click.echo(f"\n{update_count} agent(s) have updates available.")
    else:
        click.echo("\nAll agents are up to date.")


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
def upgrade(agent: str | None, dry_run: bool, timeout: int):
    """Upgrade agents to latest versions."""
    asyncio.run(run_upgrade(agent, dry_run, timeout))


async def run_upgrade(agent: str | None, dry_run: bool, timeout: int):
    config = load_config()
    agents = config["agents"]

    if agent:
        agents = [a for a in agents if a["name"] == agent]
        if not agents:
            click.echo(f"Agent '{agent}' not found in configuration.", err=True)
            sys.exit(1)

    click.echo("Checking for available updates...")
    check_results = await asyncio.gather(*[check_agent_updates(a) for a in agents])

    upgradeable_agents: list[AgentConfig] = []
    for i, result in enumerate(check_results):
        if result["update_available"]:
            upgradeable_agents.append(agents[i])

    if not upgradeable_agents:
        click.echo("No agents need updating.")
        return

    if dry_run:
        click.echo("The following upgrades would be performed:")
        for agent_config in upgradeable_agents:
            # Re-find version info from results
            result = next(r for r in check_results if r["name"] == agent_config["name"])
            click.echo(
                f"  {result['name']}: {result['current_version']} → {result['latest_version']}"
            )
        return

    click.echo(f"Upgrading {len(upgradeable_agents)} agents...")

    async def perform_upgrade(agent_config: AgentConfig) -> tuple[str, int, str]:
        upgrade_command = agent_config.get("upgrade_command")
        if upgrade_command:
            click.echo(f"Upgrading {agent_config['name']}...")
            output, returncode = await run_command_async(
                upgrade_command, timeout=timeout
            )
            return agent_config["name"], returncode, output
        return agent_config["name"], 1, "No upgrade command configured"

    upgrade_results = await asyncio.gather(
        *[perform_upgrade(a) for a in upgradeable_agents]
    )

    for name, returncode, output in upgrade_results:
        if returncode == 0:
            click.echo(f"✅ {name} upgraded successfully")
        else:
            click.echo(f"❌ {name} upgrade failed: {output}")


@cli.command()
@click.argument("agent_name")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force installation even if already installed",
)
@click.option(
    "--timeout", "-t", default=600, help="Command timeout in seconds (default: 600)"
)
def install(agent_name: str, force: bool, timeout: int):
    """Install a specific agent."""
    asyncio.run(run_install(agent_name, force, timeout))


async def run_install(agent_name: str, force: bool, timeout: int):
    config = load_config()
    agents = config["agents"]

    agent_config = next((a for a in agents if a["name"] == agent_name), None)
    if not agent_config:
        click.echo(f"Agent '{agent_name}' not found in configuration.", err=True)
        sys.exit(1)

    current, status = await get_current_version(agent_config)

    if status == "success" and not force:
        click.echo(f"Agent '{agent_name}' is already installed (version: {current}).")
        click.echo("Use --force to reinstall.")
        return

    install_command = agent_config.get("install_command")
    if not install_command:
        click.echo(f"No install command defined for agent '{agent_name}'.", err=True)
        sys.exit(1)

    click.echo(f"Installing {agent_name}...")
    output, returncode = await run_command_async(install_command, timeout=timeout)

    if returncode == 0:
        click.echo(f"✅ {agent_name} installed successfully")
        new_ver, _ = await get_current_version(agent_config)
        if new_ver:
            click.echo(f"Installed version: {new_ver}")
    else:
        click.echo(f"❌ {agent_name} installation failed: {output}")
        sys.exit(1)


@cli.command(name="list")
def list_agents():
    """List all configured agents."""
    asyncio.run(run_list_agents())


async def run_list_agents():
    config = load_config()
    agents = config["agents"]

    click.echo("Configured agents:")
    click.echo("")

    # Parallelize fetching current versions for all agents
    results = await asyncio.gather(*[get_current_version(agent) for agent in agents])

    for i, agent in enumerate(agents):
        current, status = results[i]
        click.echo(f"• {agent['name']}")
        click.echo(f"  {agent.get('description', '')}")
        click.echo(f"  Current version: {current or 'Unknown'} ({status})")
        click.echo("")


async def run_release_notes(agent: str | None):
    config = load_config()
    agents = config["agents"]

    if agent:
        agents = [a for a in agents if a["name"] == agent]
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
                _ = f.write(content)

            # Append to combined file
            _ = combined_f.write(f"\n\n# {name}\n\n")
            _ = combined_f.write(content)
            _ = combined_f.write("\n\n---\n\n")

    if agent:
        # Render the single file
        file_path = rn_dir / f"{agents[0]['name']}.md"
        _ = os.system(f"{pager_cmd} {file_path}")
    else:
        # Render all
        _ = os.system(f"{pager_cmd} {combined_path}")


@cli.command(name="release-notes")
@click.option("--agent", "-a", help="Get release notes for specific agent")
def release_notes(agent: str | None):
    """Fetch and display release notes."""
    asyncio.run(run_release_notes(agent))


cli.add_command(release_notes, name="rn")

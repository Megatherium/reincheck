#!/usr/bin/env python3

import click
import yaml
import asyncio
import sys
import json
import os
from typing import TypedDict, cast
from pathlib import Path


class AgentConfig(TypedDict):
    name: str
    description: str
    install_command: str
    version_command: str
    check_latest_command: str
    upgrade_command: str
    latest_version: str | None
    github_repo: str | None


class Config(TypedDict):
    agents: list[AgentConfig]


def load_config() -> Config:
    """Load agents configuration from YAML file."""
    config_path = Path(__file__).parent / "agents.yaml"
    if not config_path.exists():
        click.echo(f"Error: Configuration file {config_path} not found.", err=True)
        sys.exit(1)

    with open(config_path, "r") as f:
        return cast(Config, yaml.safe_load(f))


async def run_command_async(command: str, timeout: int = 30) -> tuple[str, int]:
    """Run a command asynchronously and return output and return code."""
    process = None
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=timeout)
            # Use stdout if available, otherwise stderr?
            # Original implementation used capture_output=True which captures both,
            # but returned result.stdout.strip().
            output = stdout.decode().strip()
            return output, process.returncode if process.returncode is not None else 1
        except asyncio.TimeoutError:
            process.kill()
            _ = await process.wait()
            return f"Command timed out after {timeout} seconds", 1
    except Exception as e:
        return f"Error: {str(e)}", 1
    finally:
        if process:
            transport = getattr(process, "_transport", None)
            if transport:
                transport.close()  # pyright: ignore[reportAny]


async def get_current_version(agent: AgentConfig) -> tuple[str | None, str]:
    """Get the current version of an agent."""
    version_command = agent.get("version_command")
    if not version_command:
        return None, "No version command configured"

    output, returncode = await run_command_async(version_command)
    if returncode == 0:
        return output, "success"
    else:
        return None, output or "Command failed"


async def get_latest_version(agent: AgentConfig) -> tuple[str | None, str]:
    """Get the latest version of an agent."""
    check_latest_command = agent.get("check_latest_command")
    if not check_latest_command:
        return None, "No version check command configured"

    output, returncode = await run_command_async(check_latest_command)
    if returncode == 0:
        return output, "success"
    else:
        return None, output or "Command failed"


def extract_version_number(version_str: str) -> str:
    """Extract version number from version string."""
    import re

    if not version_str:
        return ""

    # Look for version patterns like v1.2.3, 1.2.3, or version numbers in parentheses
    patterns = [
        r"v?(\d+\.\d+\.\d+(?:\.\d+)?)",  # v1.2.3 or 1.2.3
        r"v?(\d+\.\d+(?:\.\d+)?)",  # v1.2 or 1.2
        r"v?(\d+)",  # v1 or 1
    ]

    for pattern in patterns:
        match = re.search(pattern, version_str)
        if match:
            return match.group(1)

    # If no version found, return original string
    return version_str


def compare_versions(version1: str, version2: str) -> int:
    """Compare two version strings. Returns -1, 0, or 1."""

    def version_tuple(v: str) -> tuple[int, ...]:
        return tuple(map(int, v.split(".")))

    try:
        v1 = version_tuple(extract_version_number(version1))
        v2 = version_tuple(extract_version_number(version2))

        if v1 < v2:
            return -1
        elif v1 > v2:
            return 1
        else:
            return 0
    except:
        # If parsing fails, do string comparison
        if version1 < version2:
            return -1
        elif version1 > version2:
            return 1
        else:
            return 0


class UpdateResult(TypedDict):
    name: str
    current_version: str | None
    current_status: str
    latest_version: str | None
    latest_status: str
    update_available: bool
    description: str


async def check_agent_updates(agent: AgentConfig) -> UpdateResult:
    """Check if an agent has an update available."""
    # Run checks in parallel
    current_future = get_current_version(agent)
    latest_future = get_latest_version(agent)

    (current, current_status), (latest, latest_status) = await asyncio.gather(
        current_future, latest_future
    )

    result: UpdateResult = {
        "name": agent["name"],
        "current_version": current,
        "current_status": current_status,
        "latest_version": latest,
        "latest_status": latest_status,
        "update_available": False,
        "description": agent.get("description", ""),
    }

    if (
        current
        and latest
        and current_status == "success"
        and latest_status == "success"
    ):
        # Compare versions
        if compare_versions(current, latest) < 0:
            result["update_available"] = True

    return result


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


async def fetch_release_notes(agent: AgentConfig) -> tuple[str, str]:
    """Fetch release notes for an agent."""
    repo = agent.get("github_repo")
    if not repo:
        return agent["name"], "No GitHub repository configured for release notes."

    url = f"https://api.github.com/repos/{repo}/releases/latest"
    # Use curl to fetch
    cmd = f"curl -s -H 'Accept: application/vnd.github.v3+json' {url}"

    output, returncode = await run_command_async(cmd)

    if returncode != 0:
        return agent["name"], f"Failed to fetch release notes: {output}"

    try:
        data = cast(dict[str, object], json.loads(output))
        if "body" not in data:
            # Fallback to just the name and url if body is missing or it's not a release object
            return agent[
                "name"
            ], f"No release notes body found. Check {data.get('html_url', url)}"

        header = (
            f"# Release Notes: {agent['name']} ({data.get('tag_name', 'Latest')})\n\n"
        )
        return agent["name"], header + str(data["body"])
    except json.JSONDecodeError:
        return agent["name"], "Failed to parse release notes JSON."


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

    results = await asyncio.gather(*[fetch_release_notes(a) for a in agents])

    pager_cmd = os.environ.get("MYAGENTS_RN_PAGER", "cat")

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


if __name__ == "__main__":
    cli()

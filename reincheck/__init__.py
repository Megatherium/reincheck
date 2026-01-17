import asyncio
import json
import re
import sys
import yaml
from pathlib import Path
from typing import TypedDict, cast
import click


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


class UpdateResult(TypedDict):
    name: str
    current_version: str | None
    current_status: str
    latest_version: str | None
    latest_status: str
    update_available: bool
    description: str


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

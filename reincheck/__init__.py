import asyncio
import json
import os
import re
import sys
import yaml
from pathlib import Path
from typing import TypedDict, cast
import click


_debug_enabled = False


def set_debug(enabled: bool):
    """Enable or disable debug mode globally."""
    global _debug_enabled
    _debug_enabled = enabled


def is_debug() -> bool:
    """Check if debug mode is enabled."""
    return _debug_enabled


class AgentConfig(TypedDict):
    name: str
    description: str
    install_command: str
    version_command: str
    check_latest_command: str
    upgrade_command: str
    latest_version: str | None
    github_repo: str | None
    release_notes_url: str | None


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


def save_config(config: Config) -> None:
    """Save agents configuration to YAML file."""
    config_path = Path(__file__).parent / "agents.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


async def run_command_async(command: str, timeout: int = 30) -> tuple[str, int]:
    """Run a command asynchronously and return output and return code."""
    process = None
    try:
        if is_debug():
            click.echo(f"[DEBUG] Running command: {command}", err=True)
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            output = stdout.decode().strip()
            if is_debug() and stderr:
                click.echo(f"[DEBUG] stderr: {stderr.decode().strip()}", err=True)
            return output, process.returncode if process.returncode is not None else 1
        except asyncio.TimeoutError:
            process.kill()
            _ = await process.wait()
            return f"Command timed out after {timeout} seconds", 1
    except Exception as e:
        if is_debug():
            click.echo(f"[DEBUG] Exception: {type(e).__name__}: {e}", err=True)
        return f"Error: {str(e)}", 1
    finally:
        if process:
            transport = getattr(process, "_transport", None)
            if transport:
                transport.close()


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


def add_github_auth_if_needed(command: str) -> str:
    """Add Bearer token header to curl commands targeting GitHub API if GITHUB_TOKEN is set."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token or "api.github.com" not in command:
        return command

    if "Authorization:" in command:
        return command

    if "curl " in command or "curl" == command[:4]:
        header = " -H 'Authorization: Bearer $GITHUB_TOKEN'"
        if "-H " in command:
            command = command.replace("curl ", f"curl{header} ", 1)
        else:
            command = command.replace("curl", f"curl{header}", 1)

    return command


async def get_latest_version(agent: AgentConfig) -> tuple[str | None, str]:
    """Get the latest version of an agent."""
    check_latest_command = agent.get("check_latest_command")
    if not check_latest_command:
        return None, "No version check command configured"

    check_latest_command = add_github_auth_if_needed(check_latest_command)
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

    # If no version found, return empty string to avoid comparing "Unknown" vs "1.2.3"
    return ""


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


async def fetch_url_content(url: str) -> tuple[str | None, str]:
    """Fetch content from a URL using curl."""
    cmd = f"curl -s -L {url}"
    output, returncode = await run_command_async(cmd)
    if returncode != 0:
        return None, f"Failed to fetch URL: {output}"
    return output, "success"


async def get_npm_release_info(package_name: str) -> str | None:
    """Get release info from NPM."""
    # Get dist-tags to find the true 'latest'
    cmd_tags = f"npm view {package_name} dist-tags --json"
    output_tags, returncode_tags = await run_command_async(cmd_tags)

    latest_ver = None
    if returncode_tags == 0:
        try:
            tags = json.loads(output_tags)
            latest_ver = tags.get("latest")
        except:
            pass

    # Get time info
    cmd_time = f"npm view {package_name} time --json"
    output_time, returncode_time = await run_command_async(cmd_time)

    latest_time = "Unknown"
    if returncode_time == 0:
        try:
            data = json.loads(output_time)
            # If we didn't find latest from tags, try the last key
            if not latest_ver:
                versions = [k for k in data.keys() if k not in ["modified", "created"]]
                if versions:
                    latest_ver = versions[-1]

            if latest_ver:
                latest_time = data.get(latest_ver, "Unknown")
        except:
            pass

    if latest_ver:
        return (
            f"### Latest NPM Release: {latest_ver}\n"
            f"**Published:** {latest_time}\n\n"
            f"View on NPM: https://www.npmjs.com/package/{package_name}\n"
        )

    return None


async def get_pypi_release_info(package_name: str) -> str | None:
    """Get release info from PyPI."""
    url = f"https://pypi.org/pypi/{package_name}/json"
    output, returncode = await run_command_async(f"curl -s {url}")

    if returncode != 0:
        return None

    try:
        data = json.loads(output)
        info = data.get("info", {})
        latest_ver = info.get("version")

        if not latest_ver:
            return None

        # Try to find release time
        releases = data.get("releases", {})
        latest_release_data = releases.get(latest_ver, [])
        upload_time = "Unknown"
        if latest_release_data:
            upload_time = latest_release_data[0].get("upload_time", "Unknown")

        project_urls = info.get("project_urls") or {}
        changelog_url = (
            project_urls.get("Changelog")
            or project_urls.get("Changes")
            or project_urls.get("History")
        )

        notes = (
            f"### Latest PyPI Release: {latest_ver}\n"
            f"**Uploaded:** {upload_time}\n"
            f"**Summary:** {info.get('summary', '')}\n\n"
            f"View on PyPI: https://pypi.org/project/{package_name}/\n"
        )

        if changelog_url:
            notes += f"Changelog: {changelog_url}\n"

        return notes
    except:
        return None


async def fetch_release_notes(
    agent: AgentConfig, current_version: str | None
) -> tuple[str, str]:
    """Fetch release notes for an agent."""
    notes_parts = []

    # 1. Try GitHub
    repo = agent.get("github_repo")
    if repo:
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        cmd = add_github_auth_if_needed(f"curl -s -H 'Accept: application/vnd.github.v3+json' {url}")
        output, returncode = await run_command_async(cmd)

        if returncode == 0:
            try:
                data = cast(dict[str, object], json.loads(output))
                tag_name = str(data.get("tag_name", ""))
                body = str(data.get("body", ""))

                # Check version freshness
                github_ver = extract_version_number(tag_name)
                current_ver_num = extract_version_number(current_version or "")

                is_outdated = False
                if current_ver_num and github_ver:
                    # Simple check: if current is "larger" than github, github is outdated
                    # But we need to be careful about format.
                    if compare_versions(github_ver, current_ver_num) < 0:
                        is_outdated = True

                if is_outdated:
                    notes_parts.append(
                        f"⚠️ **Warning**: The latest GitHub release ({tag_name}) appears older than your installed version ({current_version}).\n"
                    )

                if body:
                    header = f"# Release Notes: {agent['name']} ({tag_name})\n\n"
                    notes_parts.append(header + body)
                else:
                    notes_parts.append(
                        f"No release body found on GitHub. Check {data.get('html_url', url)}"
                    )

            except json.JSONDecodeError:
                notes_parts.append("Failed to parse GitHub release notes JSON.")
        else:
            notes_parts.append(f"Failed to fetch GitHub release notes: {output}")

    # 2. Try Release Notes URL (Fallback or Supplement)
    rn_url = agent.get("release_notes_url")
    if rn_url:
        # If we already have notes and they aren't outdated, maybe skip?
        # But user might want to see both if configured.
        # Let's append if we have nothing or if we found GitHub was outdated.
        if not notes_parts or "⚠️" in notes_parts[0]:
            notes_parts.append(f"\n\n## External Release Notes\nSource: {rn_url}\n")
            # Try to fetch text content if it looks like a text file
            if rn_url.endswith(".md") or rn_url.endswith(".txt"):
                content, status = await fetch_url_content(rn_url)
                if status == "success" and content:
                    notes_parts.append(content)
                else:
                    notes_parts.append("Could not fetch content directly.")
            else:
                notes_parts.append(f"Please visit: {rn_url}")

    # 3. Try NPM Fallback
    install_cmd = agent.get("install_command", "")
    should_fallback = not notes_parts or any(
        x in notes_parts[0] for x in ["⚠️", "No release body", "Failed to fetch"]
    )

    if "npm" in install_cmd or "npm:" in install_cmd:
        # Extract package name
        match = re.search(r"npm:(@?[\w\-/]+)", install_cmd)
        if not match:
            match = re.search(r"npm install -g (@?[\w\-/]+)", install_cmd)

        if match:
            pkg_name = match.group(1)
            # Only add NPM info if we don't have good notes yet
            if should_fallback:
                npm_info = await get_npm_release_info(pkg_name)
                if npm_info:
                    notes_parts.append(f"\n\n## NPM Info\n{npm_info}")

    # 4. Try PyPI Fallback
    if "pip" in install_cmd or "uv tool" in install_cmd:
        # Extract package name
        # uv tool install package-name
        # pip install package-name
        match = re.search(r"uv tool install (@?[\w\-/]+)", install_cmd)
        if not match:
            match = re.search(r"pip install (@?[\w\-/]+)", install_cmd)

        if match:
            pkg_name = match.group(1)
            if should_fallback:
                pypi_info = await get_pypi_release_info(pkg_name)
                if pypi_info:
                    notes_parts.append(f"\n\n## PyPI Info\n{pypi_info}")

    if not notes_parts:
        return agent["name"], "No release notes found from configured sources."

    return agent["name"], "\n".join(notes_parts)

"""Release notes fetching utilities."""

import asyncio
import json
import re
from typing import cast

from .config import AgentConfig
from .execution import run_command_async
from .versions import (
    extract_version_number,
    compare_versions,
    add_github_auth_if_needed,
)


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
        except (json.JSONDecodeError, KeyError, TypeError):
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
        except (json.JSONDecodeError, KeyError, TypeError):
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
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


async def fetch_github_release_notes(
    agent: AgentConfig, current_version: str | None
) -> list[str]:
    """Fetch release notes from GitHub API."""
    notes_parts = []
    repo = agent.github_repo
    if not repo:
        return notes_parts

    url = f"https://api.github.com/repos/{repo}/releases/latest"
    cmd = add_github_auth_if_needed(
        f"curl -s -H 'Accept: application/vnd.github.v3+json' {url}"
    )
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
                if compare_versions(github_ver, current_ver_num) < 0:
                    is_outdated = True

            if is_outdated:
                notes_parts.append(
                    f"⚠️ **Warning**: The latest GitHub release ({tag_name}) appears older than your installed version ({current_version}).\n"
                )

            if body:
                header = f"# Release Notes: {agent.name} ({tag_name})\n\n"
                notes_parts.append(header + body)
            else:
                notes_parts.append(
                    f"No release body found on GitHub. Check {data.get('html_url', url)}"
                )

        except json.JSONDecodeError:
            notes_parts.append("Failed to parse GitHub release notes JSON.")
    else:
        notes_parts.append(f"Failed to fetch GitHub release notes: {output}")

    return notes_parts


async def fetch_external_release_notes(agent: AgentConfig) -> list[str]:
    """Fetch release notes from an external URL."""
    notes_parts = []
    rn_url = agent.release_notes_url
    if not rn_url:
        return notes_parts

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

    return notes_parts


async def fetch_npm_fallback(agent: AgentConfig) -> list[str]:
    """Fetch release info from NPM as a fallback."""
    notes_parts = []
    install_cmd = agent.install_command
    if "npm" in install_cmd or "npm:" in install_cmd:
        # Extract package name
        match = re.search(r"npm:(@?[\w\-/]+)", install_cmd)
        if not match:
            match = re.search(r"npm install -g (@?[\w\-/]+)", install_cmd)

        if match:
            pkg_name = match.group(1)
            npm_info = await get_npm_release_info(pkg_name)
            if npm_info:
                notes_parts.append(f"\n\n## NPM Info\n{npm_info}")
    return notes_parts


async def fetch_pypi_fallback(agent: AgentConfig) -> list[str]:
    """Fetch release info from PyPI as a fallback."""
    notes_parts = []
    install_cmd = agent.install_command
    if "pip" in install_cmd or "uv tool" in install_cmd:
        # Extract package name
        match = re.search(r"uv tool install (@?[\w\-/]+)", install_cmd)
        if not match:
            match = re.search(r"pip install (@?[\w\-/]+)", install_cmd)

        if match:
            pkg_name = match.group(1)
            pypi_info = await get_pypi_release_info(pkg_name)
            if pypi_info:
                notes_parts.append(f"\n\n## PyPI Info\n{pypi_info}")
    return notes_parts


async def fetch_release_notes(
    agent: AgentConfig, current_version: str | None
) -> tuple[str, str]:
    """Fetch release notes for an agent."""
    notes_parts = []

    # 1. Try GitHub
    notes_parts.extend(await fetch_github_release_notes(agent, current_version))

    # 2. Try Release Notes URL (Fallback or Supplement)
    if not notes_parts or "⚠️" in notes_parts[0]:
        notes_parts.extend(await fetch_external_release_notes(agent))

    # 3. Try NPM Fallback
    should_fallback = not notes_parts or any(
        x in notes_parts[0] for x in ["⚠️", "No release body", "Failed to fetch"]
    )
    if should_fallback:
        notes_parts.extend(await fetch_npm_fallback(agent))

    # 4. Try PyPI Fallback
    if should_fallback:
        notes_parts.extend(await fetch_pypi_fallback(agent))

    if not notes_parts:
        return agent.name, "No release notes found from configured sources."

    return agent.name, "\n".join(notes_parts)

"""Version comparison and retrieval utilities."""

import os
import re
import shlex
import subprocess
from typing import Tuple

from .config import AgentConfig
from .execution import run_command_async


def add_github_auth_if_needed(command: str) -> str:
    """Add Bearer token header to curl commands targeting GitHub API
    if GITHUB_TOKEN is set.
    
    Uses shlex for proper shell command parsing and reconstructs the command
    with the Authorization header inserted after the curl command.
    
    Args:
        command: Shell command string that may contain curl
        
    Returns:
        Modified command with GitHub auth header if applicable, otherwise original
    """
    token = os.environ.get("GITHUB_TOKEN")
    if not token or "api.github.com" not in command:
        return command

    if "Authorization:" in command:
        return command

    try:
        parts = command.split("|", 1)
        main_cmd = parts[0].strip()
        pipe_cmd = parts[1].strip() if len(parts) > 1 else None

        tokens = shlex.split(main_cmd)
        if not tokens or tokens[0] != "curl":
            return command

        auth_header = ["-H", f"Authorization: Bearer {token}"]
        new_tokens = [tokens[0]] + auth_header + tokens[1:]

        new_main_cmd = subprocess.list2cmdline(new_tokens)
        result = new_main_cmd
        if pipe_cmd:
            result = f"{new_main_cmd} | {pipe_cmd}"
        return result
    except (ValueError, IndexError):
        return command


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

    def version_tuple(v: str) -> Tuple[int, ...]:
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
    except (ValueError, TypeError):
        # If parsing fails, do string comparison
        if version1 < version2:
            return -1
        elif version1 > version2:
            return 1
        else:
            return 0


async def get_current_version(agent: AgentConfig) -> Tuple[str | None, str]:
    """Get the current version of an agent."""
    version_command = agent.version_command
    if not version_command:
        return None, "No version command configured"

    output, returncode = await run_command_async(version_command)
    if returncode == 0:
        return output, "success"
    else:
        return None, output or "Command failed"


async def get_latest_version(
    agent: AgentConfig | None = None, check_command: str | None = None
) -> Tuple[str | None, str]:
    """Get the latest version of an agent.

    Args:
        agent: Optional AgentConfig instance (for backward compatibility)
        check_command: Optional command string to check latest version

    Returns:
        Tuple of (version_string or None, status_message)

    Raises:
        ValueError: If neither agent nor check_command is provided
    """
    check_latest_command: str

    # Determine which command to use
    if check_command:
        check_latest_command = check_command
    elif agent:
        check_latest_command = agent.check_latest_command
    else:
        raise ValueError("Either agent or check_command must be provided")

    if not check_latest_command:
        return None, "No version check command configured"

    check_latest_command = add_github_auth_if_needed(check_latest_command)
    output, returncode = await run_command_async(check_latest_command)
    if returncode == 0:
        return output, "success"
    else:
        return None, output or "Command failed"

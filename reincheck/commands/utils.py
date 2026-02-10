"""Shared utility functions for commands."""

import os

from reincheck.config import AgentConfig


def filter_agent_by_name(agents: list[AgentConfig], name: str) -> list[AgentConfig]:
    """Filter agents list by name, returning empty list if not found.

    Args:
        agents: List of AgentConfig instances to filter
        name: Agent name to match (exact match)

    Returns:
        List of AgentConfig instances matching the given name, or empty list
    """
    return [a for a in agents if a.name == name]


def validate_pager(pager_cmd: str) -> str:
    """Validate pager command against whitelist for security.

    Args:
        pager_cmd: Pager command from environment variable or default

    Returns:
        The validated pager command

    Raises:
        ValueError: If pager command is not in the allowed list
    """
    SAFE_PAGERS = {
        "cat",
        "less",
        "more",
        "bat",
        "most",
        "pager",
    }

    # Handle absolute paths - extract base command
    if os.path.isabs(pager_cmd):
        base_cmd = os.path.basename(pager_cmd)
        if base_cmd in SAFE_PAGERS:
            return pager_cmd
        raise ValueError(
            f"Unsafe pager: '{pager_cmd}'. "
            f"Allowed commands: {', '.join(sorted(SAFE_PAGERS))}"
        )

    # Handle relative/bare commands
    if pager_cmd in SAFE_PAGERS:
        return pager_cmd

    raise ValueError(
        f"Unsafe pager: '{pager_cmd}'. "
        f"Allowed commands: {', '.join(sorted(SAFE_PAGERS))}"
    )

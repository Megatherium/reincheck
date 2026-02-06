"""Update checking utilities."""

import asyncio
from typing import TypedDict

from .config import AgentConfig
from .versions import get_current_version, get_latest_version, compare_versions


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
        "name": agent.name,
        "current_version": current,
        "current_status": current_status,
        "latest_version": latest,
        "latest_status": latest_status,
        "update_available": False,
        "description": agent.description,
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

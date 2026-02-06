"""Reincheck - AI coding agent management tool.

This module provides the main exports for the reincheck package.
Most functionality is split into specialized modules.
"""

import json
import logging
import sys
import click
from pathlib import Path

# Configuration
from .config import (
    ConfigError,
    AgentConfig,
    Config,
    validate_config,
    load_config as load_json_config,
)

# Path helpers
from .paths import (
    get_config_dir,
    get_config_path,
    get_packaged_config_path,
)

# Migration
from .migration import (
    migrate_yaml_to_json,
    ensure_user_config,
)

# Execution
from .execution import run_command_async

# Version utilities
from .versions import (
    get_current_version,
    get_latest_version,
    compare_versions,
    extract_version_number,
    add_github_auth_if_needed,
)

# Release notes
from .release_notes import (
    fetch_release_notes,
    fetch_github_release_notes,
    fetch_external_release_notes,
    fetch_npm_fallback,
    fetch_pypi_fallback,
    get_npm_release_info,
    get_pypi_release_info,
    fetch_url_content,
)

# Updates
from .updates import (
    UpdateResult,
    check_agent_updates,
)

# Timeouts
from .execution import DEFAULT_TIMEOUT, UPGRADE_TIMEOUT, INSTALL_TIMEOUT

_logging = logging.getLogger(__name__)


def setup_logging(debug: bool = False):
    """Configure logging for the application."""
    if not _logging.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        _logging.addHandler(handler)
        _logging.setLevel(logging.DEBUG if debug else logging.INFO)


def _dict_to_config(data: dict) -> Config:
    """Convert a raw dict to a Config object.

    Temporary bridge function - delegates to validate_config from config.py.
    Kept for backward compatibility during migration.
    """
    return validate_config(data)


def load_config(config_path: Path | None = None) -> Config:
    """Load agents configuration from a JSON file.

    Args:
        config_path: Optional path to config file. If None, uses get_config_path(create=True)

    Returns:
        Config object with agents list

    Raises:
        ConfigError: If the config cannot be loaded or parsed
    """
    if config_path is None:
        config_path = get_config_path(create=True)

    if not config_path.exists():
        raise ConfigError(
            f"Config file not found: {config_path}\n"
            f"Run 'reincheck config init' to create a default config."
        )

    try:
        data = load_json_config(config_path)
    except ConfigError as e:
        raise ConfigError(
            f"Config file is corrupted: {config_path}\n{e}\n\n"
            f"Run 'reincheck config init' to restore defaults."
        ) from e

    return _dict_to_config(data)


def save_config(config: Config, config_path: Path | None = None) -> None:
    """Save agents configuration to JSON file atomically.

    Args:
        config: Config object to save
        config_path: Optional path to config file. If None, uses get_config_path(create=True)
    """
    if config_path is None:
        config_path = get_config_path(create=True)

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise ConfigError(
            f"Failed to create config directory: {config_path.parent}\n{e}"
        )

    try:
        # Convert dataclass to dict for JSON serialization
        agents_data = []
        for agent in config.agents:
            agent_dict = {
                "name": agent.name,
                "description": agent.description,
                "install_command": agent.install_command,
                "version_command": agent.version_command,
                "check_latest_command": agent.check_latest_command,
                "upgrade_command": agent.upgrade_command,
            }
            if agent.latest_version is not None:
                agent_dict["latest_version"] = agent.latest_version
            if agent.github_repo is not None:
                agent_dict["github_repo"] = agent.github_repo
            if agent.release_notes_url is not None:
                agent_dict["release_notes_url"] = agent.release_notes_url
            agents_data.append(agent_dict)

        data = {"agents": agents_data}

        # Write to temp file first
        temp_path = config_path.with_suffix(".tmp")
        with open(temp_path, "w") as f:
            json.dump(data, f, indent=2)
        # Atomic rename (POSIX guarantees atomicity)
        temp_path.replace(config_path)
    except (IOError, OSError) as e:
        _logging.error(f"Error saving configuration: {e}")
        click.echo(f"Error saving configuration: {e}", err=True)
        raise


__all__ = [
    "ConfigError",
    "AgentConfig",
    "Config",
    "UpdateResult",
    "load_config",
    "save_config",
    "setup_logging",
    "DEFAULT_TIMEOUT",
    "UPGRADE_TIMEOUT",
    "INSTALL_TIMEOUT",
    "get_config_dir",
    "get_config_path",
    "get_packaged_config_path",
    "migrate_yaml_to_json",
    "ensure_user_config",
    "run_command_async",
    "get_current_version",
    "get_latest_version",
    "compare_versions",
    "extract_version_number",
    "add_github_auth_if_needed",
    "fetch_release_notes",
    "fetch_github_release_notes",
    "fetch_external_release_notes",
    "fetch_npm_fallback",
    "fetch_pypi_fallback",
    "get_npm_release_info",
    "get_pypi_release_info",
    "fetch_url_content",
    "check_agent_updates",
]

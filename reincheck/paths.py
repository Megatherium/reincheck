"""Configuration path helpers for reincheck."""

import os
from pathlib import Path


def get_config_dir() -> Path:
    """Return XDG-compliant config directory: ~/.config/reincheck"""
    return Path.home() / ".config" / "reincheck"


def get_packaged_config_path() -> Path:
    """Return path to packaged default config (read-only fallback)"""
    return Path(__file__).parent / "agents.json"


def get_config_path(create: bool = False) -> Path:
    """Return path to user config file.

    Priority:
    1. REINCHECK_CONFIG environment variable (if set)
    2. ~/.config/reincheck/agents.json (default XDG location)

    Args:
        create: If True, create config dir and seed from defaults if missing

    Returns:
        Path to config file
    """
    if "REINCHECK_CONFIG" in os.environ:
        custom_path = Path(os.environ["REINCHECK_CONFIG"])
        if create:
            custom_path.parent.mkdir(parents=True, exist_ok=True)
        return custom_path

    config_path = get_config_dir() / "agents.json"
    if create:
        from . import ensure_user_config

        ensure_user_config(config_path)
    return config_path

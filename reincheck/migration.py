"""YAML to JSON migration utilities."""

import json
import logging
import click

from .config import ConfigError
from .paths import get_config_dir, get_packaged_config_path

_logging = logging.getLogger(__name__)


def migrate_yaml_to_json(yaml_path, json_path) -> None:
    """Migrate YAML config to JSON format.

    Args:
        yaml_path: Path to source YAML file
        json_path: Path to destination JSON file

    Raises:
        ConfigError: If migration fails
    """
    try:
        import yaml
    except ImportError:
        _logging.warning("pyyaml not installed. Install with: pip install pyyaml")
        raise ConfigError(
            "Cannot migrate YAML config: pyyaml not installed.\n"
            "Install with: pip install pyyaml"
        )

    try:
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict) or "agents" not in data:
            raise ValueError("Invalid YAML config structure")

        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

        yaml_backup = yaml_path.with_suffix(".yaml.bak")
        yaml_path.rename(yaml_backup)

        click.echo("✅ Migrated config from {yaml_path} to {json_path}")
        click.echo("   Old YAML backed up to {yaml_backup}")
        click.echo("   You can manually remove the backup when you're ready.")

    except Exception as e:
        _logging.error(f"Migration failed: {e}")
        raise ConfigError(f"Failed to migrate YAML config: {e}")


def ensure_user_config(user_config_path) -> None:
    """Ensure user config exists with proper seeding/migration logic.

    Priority order:
    1. If user_config exists → do nothing
    2. If ~/.config/reincheck/agents.yaml exists → migrate YAML→JSON
    3. If old project agents.yaml exists (dev mode) → migrate YAML→JSON
    4. Seed from packaged default (reincheck/agents.json)

    Args:
        user_config_path: Path where user config should exist
    """
    if user_config_path.exists():
        return

    _logging.debug("User config not found, checking migration sources...")

    yaml_sources = [
        get_config_dir() / "agents.yaml",
        get_packaged_config_path().parent / "agents.yaml",
    ]

    for yaml_path in yaml_sources:
        if yaml_path.exists():
            click.echo(f"⚠️  Found legacy YAML config at {yaml_path}")
            click.echo(f"   Migrating to {user_config_path}...")
            try:
                migrate_yaml_to_json(yaml_path, user_config_path)
                return
            except ConfigError:
                _logging.warning(
                    f"Migration from {yaml_path} failed, trying next source"
                )
                continue

    packaged_default = get_packaged_config_path()
    if packaged_default.exists():
        click.echo("📋 Creating user config from packaged defaults...")
        user_config_path.parent.mkdir(parents=True, exist_ok=True)
        user_config_path.write_text(packaged_default.read_text())
        _logging.debug(f"Seeded config from {packaged_default}")
    else:
        user_config_path.parent.mkdir(parents=True, exist_ok=True)
        user_config_path.write_text('{"agents": []}\n')
        _logging.debug("Created empty config")

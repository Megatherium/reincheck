"""Initialize config command implementation."""

import sys
from pathlib import Path

import click

from reincheck import (
    ConfigError,
    ensure_user_config,
    format_error,
    get_config_dir,
    get_packaged_config_path,
    migrate_yaml_to_json,
)
from reincheck.paths import get_config_path


@click.command(name="init")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force re-initialization, overwriting existing config",
)
@click.pass_context
def config_init(ctx, force: bool):
    """Initialize or re-initialize user config file.

    Creates ~/.config/reincheck/agents.json from packaged defaults.
    If a YAML config exists, it will be migrated to JSON format.

    Use --force to overwrite an existing config (creates backup first).
    """
    config_path = get_config_path(create=False)

    if config_path.exists() and not force:
        click.echo(f"Config file already exists: {config_path}")
        click.echo("Use --force to re-initialize (creates backup first).")
        sys.exit(1)

    if config_path.exists():
        backup_path = config_path.with_suffix(".json.bak")
        click.echo(f"Backing up existing config to {backup_path}...")
        config_path.rename(backup_path)
        click.echo("✅ Backup created")

    click.echo(f"Initializing config at {config_path}...")

    try:
        # If force mode, directly create from defaults or migrate
        # If normal mode (config doesn't exist), let ensure_user_config handle it
        if force:
            config_dir = get_config_dir()
            yaml_path = config_dir / "agents.yaml"
            project_yaml = (
                Path(__file__).parent.parent.parent.parent / "reincheck" / "agents.yaml"
            )

            if yaml_path.exists():
                click.echo(f"⚠️  Found legacy YAML config at {yaml_path}")
                click.echo(f"   Migrating to {config_path}...")
                migrate_yaml_to_json(yaml_path, config_path)
            elif project_yaml.exists():
                click.echo(f"⚠️  Found legacy YAML config at {project_yaml}")
                click.echo(f"   Migrating to {config_path}...")
                migrate_yaml_to_json(project_yaml, config_path)
            else:
                packaged_default = get_packaged_config_path()
                if packaged_default.exists():
                    click.echo("📋 Creating user config from packaged defaults...")
                    config_path.parent.mkdir(parents=True, exist_ok=True)
                    config_path.write_text(packaged_default.read_text())
                else:
                    config_path.parent.mkdir(parents=True, exist_ok=True)
                    config_path.write_text('{"agents": []}\n')
        else:
            ensure_user_config(config_path)

        click.echo("✅ Config initialized successfully")
    except ConfigError as e:
        click.echo(format_error(f"initialization failed: {e}"), err=True)
        sys.exit(1)

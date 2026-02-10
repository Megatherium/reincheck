"""Format config command implementation."""

import json
import sys
import uuid
from pathlib import Path

import click

from reincheck import ConfigError, format_error
from reincheck.config import load_config as load_config_raw
from reincheck.paths import get_config_path


@click.command(name="fmt")
@click.argument("file", required=False, type=click.Path())
@click.option(
    "--write",
    "-w",
    is_flag=True,
    help="Overwrite the file instead of printing to stdout",
)
@click.pass_context
def config_fmt(ctx, file: str | None, write: bool):
    """Format a config file (accepts trailing commas and // comments).

    Reads a JSON config file, parses it with tolerant parsing (accepting
    trailing commas and // comments), and outputs strict JSON.

    Note: Comments are accepted on input but not preserved after formatting.

    FILE: Path to config file (default: ~/.config/reincheck/agents.json)
    """
    # Determine the file path
    if file is None:
        file_path = get_config_path(create=False)
    else:
        file_path = Path(file)

    # Check if file exists
    if not file_path.exists():
        click.echo(format_error(f"File not found: {file_path}"), err=True)
        sys.exit(1)

    try:
        # Load with tolerant parser (accepts trailing commas, // comments)
        data = load_config_raw(file_path)
    except ConfigError as e:
        click.echo(format_error(str(e)), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(format_error(f"Error reading config: {e}"), err=True)
        sys.exit(1)

    # Output strict JSON
    formatted = json.dumps(data, indent=2, sort_keys=False)

    if write:
        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)
        # Write atomically with unique temp file name
        temp_path = file_path.with_suffix(f".tmp.{uuid.uuid4().hex[:8]}")
        try:
            with open(temp_path, "w") as f:
                f.write(formatted)
                f.write("\n")  # Trailing newline
            temp_path.replace(file_path)
            click.echo(f"Formatted {file_path}")
        except Exception as e:
            # Clean up temp file if it exists
            if temp_path.exists():
                temp_path.unlink()
            click.echo(format_error(f"Error writing file: {e}"), err=True)
            sys.exit(1)
    else:
        click.echo(formatted)

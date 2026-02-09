"""CLI command definitions for reincheck."""

import click

from reincheck.commands.check import check
from reincheck.commands.update import update
from reincheck.commands.upgrade import upgrade
from reincheck.commands.install import install
from reincheck.commands.list import list_agents as list_command
from reincheck.commands.release_notes import release_notes
from reincheck.commands.setup import setup
from reincheck.commands.config import config
from reincheck.commands.utils import validate_pager

# Import functions for backward compatibility with tests
from reincheck import (
    get_current_version,
    get_effective_method_from_config,
    run_command_async,
)


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug output for troubleshooting")
@click.pass_context
def cli(ctx, debug):
    """CLI tool to manage AI coding agents."""
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug


# Register all commands
cli.add_command(check)
cli.add_command(update)
cli.add_command(upgrade)
cli.add_command(install)
cli.add_command(list_command, name="list")
cli.add_command(release_notes, name="release-notes")
cli.add_command(setup)
cli.add_command(config)

# Add alias for release-notes
cli.add_command(release_notes, name="rn")

# Re-export utilities for backward compatibility
__all__ = [
    "cli",
    "validate_pager",
    "get_current_version",
    "get_effective_method_from_config",
    "run_command_async",
]


if __name__ == "__main__":
    cli()

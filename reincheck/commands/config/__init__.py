"""Configuration management commands."""

import click

from reincheck.commands.config.fmt import config_fmt
from reincheck.commands.config.init import config_init


@click.group()
def config():
    """Configuration management commands."""
    pass


config.add_command(config_fmt, name="fmt")
config.add_command(config_init, name="init")

"""CLI command definitions for reincheck.

This module provides backward compatibility by re-exporting the CLI from the
new modular structure in commands/ subdirectory.
"""

from reincheck.commands import cli

__all__ = ["cli"]

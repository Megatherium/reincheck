"""Release notes command implementation."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import click

from reincheck import (
    ConfigError,
    fetch_release_notes,
    format_error,
    get_current_version,
    load_config,
    setup_logging,
)
from reincheck.commands.utils import validate_pager


async def run_release_notes(agent: str | None, debug: bool):
    setup_logging(debug)
    config = load_config()
    agents = config.agents

    if agent:
        agents = [a for a in agents if a.name == agent]
        if not agents:
            click.echo(format_error(f"agent '{agent}' not found"), err=True)
            sys.exit(1)

    # Create releasenotes directory
    rn_dir = Path("releasenotes")
    rn_dir.mkdir(exist_ok=True)

    click.echo(f"Fetching release notes for {len(agents)} agents...")

    # First fetch current versions to validate notes
    click.echo("  Checking installed versions...")
    version_results = await asyncio.gather(*[get_current_version(a) for a in agents])

    # Pair agents with their current versions
    tasks = []
    for i, a in enumerate(agents):
        current_ver, _ = version_results[i]
        tasks.append(fetch_release_notes(a, current_ver))

    results = await asyncio.gather(*tasks)

    raw_pager = os.environ.get("REINCHECK_RN_PAGER", "cat")

    try:
        pager_cmd = validate_pager(raw_pager)
    except ValueError as e:
        click.echo(format_error(str(e)), err=True)
        sys.exit(1)

    combined_path = rn_dir / "all_release_notes.md"

    # Clear combined file if it exists
    if combined_path.exists():
        combined_path.unlink()

    with open(combined_path, "w") as combined_f:
        for name, content in results:
            file_path = rn_dir / f"{name}.md"
            with open(file_path, "w") as f:
                f.write(content)

            # Append to combined file
            combined_f.write(f"\n\n# {name}\n\n")
            combined_f.write(content)
            combined_f.write("\n\n---\n\n")

    if agent:
        # Render single file
        file_path = rn_dir / f"{agents[0].name}.md"
        result = subprocess.run([pager_cmd, str(file_path)], check=False)
        if result.returncode != 0:
            click.echo(
                format_error(f"pager exited with code {result.returncode}"), err=True
            )
    else:
        # Render all
        result = subprocess.run([pager_cmd, str(combined_path)], check=False)
        if result.returncode != 0:
            click.echo(
                format_error(f"pager exited with code {result.returncode}"), err=True
            )


@click.command(name="release-notes")
@click.option("--agent", "-a", help="Get release notes for specific agent")
@click.pass_context
def release_notes(ctx, agent: str | None):
    """Fetch and display release notes."""
    debug = ctx.obj.get("debug", False)
    try:
        asyncio.run(run_release_notes(agent, debug))
    except ConfigError as e:
        click.echo(format_error(str(e)), err=True)
        sys.exit(1)

"""Dependency display functions for TUI."""

import sys
import click

from ..installer import DependencyStatus, get_dependency, scan_dependencies


def format_dep_line(status: DependencyStatus, max_name_width: int = 10) -> str:
    """Format a single dependency status line for display.

    Args:
        status: The dependency status to format
        max_name_width: Width to pad the name column for alignment

    Returns:
        Formatted string with icon, name, version/path info
    """
    icon = status.status_icon
    name = status.name.ljust(max_name_width)

    if not status.available:
        hint = ""
        dep = get_dependency(status.name)
        if dep:
            hint = f"({dep.install_hint})"
        return f"{icon} {name}  missing       {hint}"

    version = status.version or "unknown"
    version_display = f"v{version}" if not version.startswith("v") else version

    if not status.version_satisfied:
        dep = get_dependency(status.name)
        constraint = ""
        if dep:
            if dep.min_version:
                constraint = f"(requires >={dep.min_version})"
        return f"{icon} {name}  {version_display:<12} {constraint}"

    path_display = status.path or ""
    return f"{icon} {name}  {version_display:<12} {path_display}"


def get_color_for_status(status: DependencyStatus) -> str:
    """Get the color name for a dependency status.

    Args:
        status: The dependency status

    Returns:
        Color name for click.secho (green/yellow/red)
    """
    if not status.available:
        return "red"
    if not status.version_satisfied:
        return "yellow"
    return "green"


def display_dependency_table(
    statuses: dict[str, DependencyStatus],
    show_all: bool = True,
    required_deps: list[str] | None = None,
) -> None:
    """Display dependency status as a formatted table with colors.

    Args:
        statuses: Dictionary of dependency name to status
        show_all: If True, show all deps; if False, only show those with issues
        required_deps: If provided, only show these specific dependencies
    """
    if required_deps is not None:
        deps_to_show = [statuses.get(d) for d in required_deps if d in statuses]
        deps_to_show = [d for d in deps_to_show if d is not None]
    else:
        deps_to_show = list(statuses.values())

    if not show_all:
        deps_to_show = [
            d for d in deps_to_show if not (d.available and d.version_satisfied)
        ]

    if not deps_to_show:
        click.secho("All dependencies satisfied!", fg="green")
        return

    max_name_width = max(len(d.name) for d in deps_to_show)

    for status in deps_to_show:
        line = format_dep_line(status, max_name_width)
        color = get_color_for_status(status)
        click.secho(line, fg=color)


def _scan_and_display_deps(
    required_deps: list[str] | None = None,
    show_all: bool = True,
    non_interactive: bool = False,
) -> dict[str, DependencyStatus]:
    """Scan dependencies and display results with colored output.

    Reuses scan_dependencies() from installer.py. Shows ✅/❌/⚠️ icons
    with green/yellow/red colors indicating availability status.

    Args:
        required_deps: If provided, only scan and display these dependencies
        show_all: If True, show all deps; if False, only show those with issues
        non_interactive: If True, skip display and just return results (for CI)

    Returns:
        Dictionary mapping dependency name to DependencyStatus

    Example output:
        ✅ mise     2024.12.1    (/home/user/.local/bin/mise)
        ✅ npm      10.8.0       (/usr/bin/npm)
        ❌ brew     missing      (Install from https://brew.sh)
        ⚠️ python   3.10.5       (requires >=3.11)
    """
    statuses = scan_dependencies()

    if non_interactive or not sys.stdout.isatty():
        return statuses

    header = "Dependency Scan Results"
    click.echo("")
    click.secho(f"  {header}", bold=True)
    click.secho("  " + "-" * len(header), dim=True)
    click.echo("")

    display_dependency_table(statuses, show_all=show_all, required_deps=required_deps)

    available_count = sum(
        1 for s in statuses.values() if s.available and s.version_satisfied
    )
    total_count = len(statuses)

    click.echo("")
    if available_count == total_count:
        click.secho(
            f"  [{available_count}/{total_count}] All dependencies ready", fg="green"
        )
    else:
        missing = total_count - available_count
        click.secho(
            f"  [{available_count}/{total_count}] {missing} dependencies need attention",
            fg="yellow",
        )

    click.echo("")

    return statuses

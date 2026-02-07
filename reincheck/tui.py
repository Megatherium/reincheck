"""TUI utilities for interactive setup wizard.

This module provides terminal UI functions following ADR-004 patterns:
- questionary for rich interactive prompts (when TTY available)
- click as fallback for CI/headless scenarios
- TTY guards before all interactive prompts
"""

import sys

import click

from .installer import DependencyStatus, get_dependency, scan_dependencies
from .installer import Preset, PresetStatus, DependencyReport
from .data_loader import get_all_methods


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


def format_preset_choice(
    preset: Preset,
    status: PresetStatus,
    report: DependencyReport | None = None,
    methods: dict | None = None,
) -> str:
    """Format a preset choice for interactive selection.

    Creates a formatted string with status indicator, preset name,
    description, and dependency summary.

    Args:
        preset: The preset to format
        status: The computed preset status
        report: Optional dependency report for detailed info
        methods: Optional dict of install methods (harness.method -> InstallMethod)

    Returns:
        Formatted string suitable for questionary.Choice()
    """
    status_icons = {
        PresetStatus.GREEN: "✅",
        PresetStatus.PARTIAL: "⚠️ ",
        PresetStatus.RED: "❌",
    }
    
    icon = status_icons.get(status, "❓")
    
    # Build the choice text
    choice_text = f"{icon} {preset.name:<15} - {preset.description}"
    
    # Add dependency info if report available and not green
    if report and status != PresetStatus.GREEN and methods:
        required_deps = set()
        for harness_name, method_name in preset.methods.items():
            method_key = f"{harness_name}.{method_name}"
            method = methods.get(method_key)
            if method:
                required_deps.update(method.dependencies)
        
        if required_deps:
            missing_for_preset = [
                dep for dep in required_deps 
                if dep in report.missing_deps or dep in report.unsatisfied_versions
            ]
            if missing_for_preset:
                choice_text += f" [{len(missing_for_preset)} missing]"
    
    return choice_text


def select_preset_interactive(
    presets: dict[str, Preset],
    report: DependencyReport,
    default: str | None = None,
    methods: dict | None = None,
) -> str | None:
    """Display interactive preset selector with status colors.

    Uses questionary to show an interactive list of presets with
    color-coded status indicators (green/yellow/red).

    Args:
        presets: Dictionary of preset name to Preset objects
        report: Dependency report with computed preset statuses
        default: Optional default preset to pre-select
        methods: Optional dict of install methods (harness.method -> InstallMethod)

    Returns:
        Selected preset name, or None if user cancelled

    Raises:
        RuntimeError: If not running in a TTY (use TTY guard before calling)
    """
    if not sys.stdin.isatty():
        raise RuntimeError("Interactive preset selector requires a TTY")
    
    # Handle empty presets
    if not presets:
        return None
    
    try:
        import questionary
    except ImportError:
        click.secho("Warning: questionary not available, using fallback", fg="yellow")
        return None
    
    # Load methods if not provided
    if methods is None:
        methods = get_all_methods()
    
    # Sort presets by priority (greens first, then by priority value)
    def sort_key(item: tuple[str, Preset]) -> tuple[int, int, str]:
        name, preset = item
        status = report.preset_statuses.get(name, PresetStatus.RED)
        # Sort: GREEN first (0), then PARTIAL (1), then RED (2)
        status_order = {
            PresetStatus.GREEN: 0,
            PresetStatus.PARTIAL: 1,
            PresetStatus.RED: 2,
        }.get(status, 2)
        return (status_order, preset.priority, name)
    
    sorted_presets = sorted(presets.items(), key=sort_key)
    
    # Build choices with formatted labels
    choices = []
    default_value = None
    
    for name, preset in sorted_presets:
        status = report.preset_statuses.get(name, PresetStatus.RED)
        label = format_preset_choice(preset, status, report, methods)
        
        # Create Choice object
        choice = questionary.Choice(
            title=label,
            value=name,
        )
        choices.append(choice)
        
        # Track default value (string, not Choice object)
        if name == default:
            default_value = name
    
    # Add cancel option
    choices.append(questionary.Separator())
    choices.append(questionary.Choice("Cancel", value=None))
    
    try:
        result = questionary.select(
            "Select a preset for installation:",
            choices=choices,
            default=default_value,
            instruction="Use ↑↓ to navigate, Enter to select",
        ).ask()
        
        return result
    except KeyboardInterrupt:
        return None


__all__ = [
    "format_dep_line",
    "get_color_for_status",
    "display_dependency_table",
    "_scan_and_display_deps",
    "scan_dependencies",
    "DependencyStatus",
    "format_preset_choice",
    "select_preset_interactive",
]

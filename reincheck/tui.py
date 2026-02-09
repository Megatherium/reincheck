"""TUI utilities for interactive setup wizard.

This module provides terminal UI functions following ADR-004 patterns:
- questionary for rich interactive prompts (when TTY available)
- click as fallback for CI/headless scenarios
- TTY guards before all interactive prompts
"""

import sys

import click
from prompt_toolkit.application import Application
from prompt_toolkit.layout import Layout, FloatContainer, Float, Window, HSplit, ConditionalContainer, DynamicContainer
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.widgets import Dialog, Label, Button
from prompt_toolkit.styles import Style
from prompt_toolkit.filters import Condition

from .installer import DependencyStatus, get_dependency, scan_dependencies
from .installer import Preset, PresetStatus, DependencyReport, InstallMethod
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


def _get_preset_dependencies_info(
    preset: Preset, report: DependencyReport, methods: dict[str, InstallMethod]
) -> list[str]:
    """Get detailed dependency info for a preset.

    Args:
        preset: The preset to check
        report: Dependency report
        methods: Dict of install methods

    Returns:
        List of formatted dependency status strings
    """
    required_deps = set()
    for harness_name, method_name in preset.methods.items():
        method_key = f"{harness_name}.{method_name}"
        method = methods.get(method_key)
        if method:
            required_deps.update(method.dependencies)

    info = []
    for dep_name in sorted(required_deps):
        status = report.all_deps.get(dep_name)
        if status:
            icon = status.status_icon
            desc = ""
            if not status.available:
                dep_obj = get_dependency(dep_name)
                hint = f" ({dep_obj.install_hint})" if dep_obj else ""
                desc = f"missing{hint}"
            elif not status.version_satisfied:
                dep_obj = get_dependency(dep_name)
                constraint = (
                    f" (requires >={dep_obj.min_version})"
                    if dep_obj and dep_obj.min_version
                    else ""
                )
                desc = f"v{status.version} {constraint}"
            else:
                desc = f"v{status.version}"
            info.append(f"{icon} {dep_name:<10} {desc}")
    return info


class _SelectorState:
    """State class for preset selector UI."""
    
    def __init__(self, default_index: int = 0):
        self.index = default_index
        self.show_modal = False
        self.result: str | None = None
        self.empty_label: "Label" = Label("")


def select_preset_interactive(
    presets: dict[str, Preset],
    report: DependencyReport,
    default: str | None = None,
    methods: dict | None = None,
) -> str | None:
    """Display interactive preset selector with status colors and details modal.

    Uses prompt_toolkit to show an interactive list of presets with
    color-coded status indicators and a dependency details modal on 'u'.

    Args:
        presets: Dictionary of preset name to Preset objects
        report: Dependency report with computed preset statuses
        default: Optional default preset to pre-select
        methods: Optional dict of install methods (harness.method -> InstallMethod)

    Returns:
        Selected preset name, or None if user cancelled
    """
    if not sys.stdin.isatty():
        raise RuntimeError("Interactive preset selector requires a TTY")

    if not presets:
        return None

    if methods is None:
        methods = get_all_methods()

    # Sort presets: GREEN first, then PARTIAL, then RED
    def sort_key(item: tuple[str, Preset]) -> tuple[int, int, str]:
        name, preset = item
        status = report.preset_statuses.get(name, PresetStatus.RED)
        status_order = {
            PresetStatus.GREEN: 0,
            PresetStatus.PARTIAL: 1,
            PresetStatus.RED: 2,
        }.get(status, 2)
        return (status_order, preset.priority, name)

    sorted_items = sorted(presets.items(), key=sort_key)
    preset_names = [name for name, _ in sorted_items]

    if not preset_names:
        return None

    default_index = 0
    if default in preset_names:
        default_index = preset_names.index(default)

    state = _SelectorState(default_index)

    kb = KeyBindings()

    def _close_modal():
        state.show_modal = False

    @kb.add("up")
    def _(event):
        if not state.show_modal and len(preset_names) > 1:
            state.index = (state.index - 1) % len(preset_names)

    @kb.add("down")
    def _(event):
        if not state.show_modal and len(preset_names) > 1:
            state.index = (state.index + 1) % len(preset_names)

    @kb.add("enter", eager=True)
    def _(event):
        if state.show_modal:
            _close_modal()
        else:
            state.result = preset_names[state.index]
            event.app.exit()

    @kb.add("u")
    def _(event):
        state.show_modal = True

    @kb.add("escape")
    @kb.add("c")
    def _(event):
        if state.show_modal:
            _close_modal()
        else:
            state.result = None
            event.app.exit()

    def get_list_text():
        tokens = []
        tokens.append(("", "\n"))
        for i, (name, preset) in enumerate(sorted_items):
            status = report.preset_statuses.get(name, PresetStatus.RED)
            label = format_preset_choice(preset, status, report, methods)
            if i == state.index:
                tokens.append(("class:selected", f" > {label}\n"))
            else:
                tokens.append(("", f"   {label}\n"))

        tokens.append(("", "\n"))
        tokens.append(
            ("class:help", " Use ↑↓ to navigate, Enter to select, 'u' for details, 'c' to cancel")
        )
        return tokens

    def get_modal_content():
        if not state.show_modal:
            return state.empty_label

        name, preset = sorted_items[state.index]
        info = _get_preset_dependencies_info(preset, report, methods)

        text = f"Dependencies for {name}:\n\n"
        if not info:
            text += "No dependencies defined."
        else:
            text += "\n".join(info)

        return Label(text=text)

    # Style matching questionary defaults
    style = Style.from_dict(
        {
            "selected": "fg:#00ffff bold",  # Cyan
            "help": "fg:#888888",  # Gray
            "dialog": "bg:#333333",
            "dialog.body": "bg:#222222 fg:#ffffff",
            "dialog frame.label": "fg:#00ffff bold",
        }
    )

    layout = FloatContainer(
        content=HSplit(
            [
                Window(
                    content=FormattedTextControl(
                        [("class:header", "Select a preset for installation:")]
                    ),
                    height=1,
                ),
                Window(content=FormattedTextControl(get_list_text)),
            ]
        ),
        floats=[
            Float(
                content=ConditionalContainer(
                    content=Dialog(
                        title="Dependency Details",
                        body=DynamicContainer(get_modal_content),
                        buttons=[
                            Button(
                                text="Close", handler=_close_modal
                            )
                        ],
                    ),
                    filter=Condition(lambda: state.show_modal),
                )
            )
        ],
    )

    app = Application(
        layout=Layout(layout), key_bindings=kb, style=style, full_screen=False
    )

    app.run()
    return state.result


def get_method_names_for_harness(
    harness_name: str,
    methods: dict,
    preset_default: str | None = None,
) -> list[str]:
    """Get available method names for a harness from the methods dict.

    Args:
        harness_name: Harness name (e.g., "claude")
        methods: Dict of method key ("harness.method") to InstallMethod
        preset_default: If provided, this method is placed first in the list

    Returns:
        List of method name strings (e.g., ["mise_binary", "homebrew", ...])
    """
    prefix = f"{harness_name}."
    names = sorted(
        key[len(prefix) :]
        for key in methods
        if key.startswith(prefix)
    )

    if preset_default and preset_default in names:
        names.remove(preset_default)
        names.insert(0, preset_default)

    return names


def _format_harness_choice(
    harness_name: str,
    harnesses: dict,
    preset_method: str | None = None,
) -> str:
    """Format a harness choice label for checkbox display.

    Args:
        harness_name: Harness key name
        harnesses: Dict of harness name to Harness objects
        preset_method: The preset's default method for this harness

    Returns:
        Formatted label string
    """
    harness = harnesses.get(harness_name)
    display = harness.display_name if harness else harness_name
    if preset_method:
        return f"{display}  (method: {preset_method})"
    return display


HarnessSelection = tuple[list[str], dict[str, str]] | None


def select_harnesses_interactive(
    preset: Preset,
    methods: dict,
    harnesses: dict,
) -> HarnessSelection:
    """Interactive harness selection with optional method overrides.

    Two-phase wizard:
    1. Checkbox to select which harnesses to include (all pre-checked)
    2. Optional method override for harnesses with multiple available methods

    Args:
        preset: The selected preset (determines default methods)
        methods: All install methods (keyed "harness.method_name")
        harnesses: All harness metadata objects

    Returns:
        Tuple of (selected_harnesses, overrides) where overrides only
        contains entries that differ from preset defaults.
        Returns None if user cancels.

    Raises:
        RuntimeError: If not running in a TTY
    """
    if not sys.stdin.isatty():
        raise RuntimeError("Interactive harness selector requires a TTY")

    try:
        import questionary
    except ImportError:
        return None

    preset_harness_names = list(preset.methods.keys())

    if not preset_harness_names:
        return ([], {})

    choices = []
    for h_name in preset_harness_names:
        label = _format_harness_choice(h_name, harnesses, preset.methods.get(h_name))
        choices.append(questionary.Choice(title=label, value=h_name, checked=True))

    try:
        selected = questionary.checkbox(
            "Select harnesses to include:",
            choices=choices,
            instruction="Space to toggle, Enter to confirm",
        ).ask()
    except KeyboardInterrupt:
        return None

    if selected is None:
        return None

    if not selected:
        return ([], {})

    overrides = _prompt_method_overrides(selected, preset, methods, harnesses)
    if overrides is None:
        return None

    return (selected, overrides)


def _prompt_method_overrides(
    selected_harnesses: list[str],
    preset: Preset,
    methods: dict,
    harnesses: dict,
) -> dict[str, str] | None:
    """Prompt for per-harness method overrides (opt-in).

    Only offers customization for harnesses with >1 available method.
    Returns None if user cancels via Ctrl+C.

    Args:
        selected_harnesses: Harnesses the user chose to include
        preset: Active preset (for default method names)
        methods: All install methods
        harnesses: All harness metadata

    Returns:
        Dict of harness_name -> overridden method_name (only changed entries),
        or None on cancel.
    """
    try:
        import questionary
    except ImportError:
        return None

    customizable = [
        h
        for h in selected_harnesses
        if len(get_method_names_for_harness(h, methods)) > 1
    ]

    if not customizable:
        return {}

    try:
        want_custom = questionary.confirm(
            "Override install methods for any harness?",
            default=False,
        ).ask()
    except KeyboardInterrupt:
        return None

    if want_custom is None:
        return None

    if not want_custom:
        return {}

    custom_choices = []
    for h_name in customizable:
        default_method = preset.methods.get(h_name, "?")
        label = _format_harness_choice(h_name, harnesses, default_method)
        custom_choices.append(
            questionary.Choice(title=label, value=h_name, checked=False)
        )

    try:
        to_customize = questionary.checkbox(
            "Which harnesses to customize?",
            choices=custom_choices,
            instruction="Space to toggle, Enter to confirm",
        ).ask()
    except KeyboardInterrupt:
        return None

    if not to_customize:
        return {}

    overrides: dict[str, str] = {}

    for h_name in to_customize:
        preset_default = preset.methods.get(h_name)
        available = get_method_names_for_harness(h_name, methods, preset_default)

        if not available:
            continue

        harness = harnesses.get(h_name)
        display = harness.display_name if harness else h_name

        method_choices = []
        for m_name in available:
            suffix = " (preset default)" if m_name == preset_default else ""
            method_choices.append(
                questionary.Choice(title=f"{m_name}{suffix}", value=m_name)
            )

        try:
            chosen = questionary.select(
                f"Method for {display}:",
                choices=method_choices,
                default=preset_default if preset_default in available else None,
            ).ask()
        except KeyboardInterrupt:
            return None

        if chosen is None:
            return None

        if chosen != preset_default:
            overrides[h_name] = chosen

    return overrides


__all__ = [
    "format_dep_line",
    "get_color_for_status",
    "display_dependency_table",
    "_scan_and_display_deps",
    "scan_dependencies",
    "DependencyStatus",
    "format_preset_choice",
    "select_preset_interactive",
    "get_method_names_for_harness",
    "select_harnesses_interactive",
]

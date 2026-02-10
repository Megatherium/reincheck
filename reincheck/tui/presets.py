"""Preset selection UI functions."""

import sys

from prompt_toolkit.application import Application
from prompt_toolkit.layout import (
    Layout,
    FloatContainer,
    Float,
    Window,
    HSplit,
    ConditionalContainer,
    DynamicContainer,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.widgets import Dialog, Label, Button
from prompt_toolkit.styles import Style
from prompt_toolkit.filters import Condition

from ..installer import (
    Preset,
    PresetStatus,
    DependencyReport,
    InstallMethod,
    get_dependency,
)
from ..data_loader import get_all_methods


def format_preset_choice(
    preset: Preset,
    status: PresetStatus,
    report: DependencyReport | None = None,
    methods: dict[str, InstallMethod] | None = None,
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
                dep
                for dep in required_deps
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
    methods: dict[str, InstallMethod] | None = None,
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
            (
                "class:help",
                " Use ↑↓ to navigate, Enter to select, 'u' for details, 'c' to cancel",
            )
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
                        buttons=[Button(text="Close", handler=_close_modal)],
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

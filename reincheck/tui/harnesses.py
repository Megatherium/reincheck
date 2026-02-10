"""Harness selection UI functions."""

import sys

from ..installer import Preset


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
    names = sorted(key[len(prefix) :] for key in methods if key.startswith(prefix))

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
    preset: "Preset",
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
    preset: "Preset",
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

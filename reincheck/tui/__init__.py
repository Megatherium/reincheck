"""TUI utilities for interactive setup wizard.

This module provides terminal UI functions following ADR-004 patterns:
- questionary for rich interactive prompts (when TTY available)
- click as fallback for CI/headless scenarios
- TTY guards before all interactive prompts

This package is split into submodules for better organization:
- dependencies: Dependency status display
- presets: Preset selection UI
- harnesses: Harness selection UI
- resolution: Failed harness resolution

The public API is re-exported from this __init__ file for backward compatibility.
"""

# Import all public functions from submodules
from .dependencies import (
    format_dep_line,
    get_color_for_status,
    display_dependency_table,
    _scan_and_display_deps,
)
from .presets import (
    format_preset_choice,
    select_preset_interactive,
    _get_preset_dependencies_info,
    _SelectorState,
)
from .harnesses import (
    get_method_names_for_harness,
    select_harnesses_interactive,
    _format_harness_choice,
    HarnessSelection,
)
from .resolution import (
    resolve_failed_harnesses_interactive,
)

__all__ = [
    "format_dep_line",
    "get_color_for_status",
    "display_dependency_table",
    "_scan_and_display_deps",
    "format_preset_choice",
    "select_preset_interactive",
    "get_method_names_for_harness",
    "select_harnesses_interactive",
    "resolve_failed_harnesses_interactive",
    "_format_harness_choice",
    "_get_preset_dependencies_info",
    "_SelectorState",
    "HarnessSelection",
]

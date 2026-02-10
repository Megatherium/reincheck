"""Failed harness resolution UI functions."""

import sys
import click

from ..installer import DependencyReport
from .harnesses import get_method_names_for_harness


def resolve_failed_harnesses_interactive(
    failed_harnesses: list[str],
    methods: dict,
    harnesses: dict,
    dep_report: DependencyReport | None = None,
) -> dict[str, str] | None:
    """Interactive loop to resolve failed harness methods.

    Prompts the user to select a method for each harness that failed resolution.

    Args:
        failed_harnesses: List of harness names that failed
        methods: All install methods
        harnesses: All harness metadata
        dep_report: Optional dependency report to check method availability

    Returns:
        Dict of harness_name -> selected_method_name (for overrides),
        or None if user cancels.
    """
    if not sys.stdin.isatty():
        raise RuntimeError("Interactive resolution requires a TTY")

    try:
        import questionary
        from prompt_toolkit.styles import Style
    except ImportError:
        return None

    overrides = {}

    # Custom style for red missing dependencies
    style = Style(
        [
            ("missing", "fg:ansired"),
            ("available", ""),
        ]
    )

    for harness_name in failed_harnesses:
        # Get all available methods for this harness
        available = get_method_names_for_harness(harness_name, methods)

        if not available:
            # Nothing to offer
            click.echo(f"No methods available for {harness_name}, skipping.")
            continue

        harness = harnesses.get(harness_name)
        display_name = harness.display_name if harness else harness_name

        choices = []
        for method_name in available:
            method_key = f"{harness_name}.{method_name}"
            method = methods.get(method_key)
            install_cmd = method.install if method else "unknown command"

            # Check dependencies if report provided
            missing_deps = False
            if dep_report and method:
                for dep in method.dependencies:
                    if dep in dep_report.missing_deps:
                        missing_deps = True
                        break

            label = f"{method_name}: {install_cmd}"

            if missing_deps:
                # Add warning suffix
                label += " (missing dependencies)"
                choices.append(
                    questionary.Choice(
                        title=[("class:missing", label)], value=method_name
                    )
                )
            else:
                choices.append(
                    questionary.Choice(
                        title=[("class:available", label)], value=method_name
                    )
                )

        # Add "Don't configure" option
        choices.append(questionary.Choice(title="Don't configure (skip)", value=None))

        try:
            selection = questionary.select(
                f"Select install method for {display_name}:",
                choices=choices,
                style=style,
            ).ask()
        except KeyboardInterrupt:
            return None

        if selection:
            overrides[harness_name] = selection
        else:
            # User chose to skip
            pass

    return overrides

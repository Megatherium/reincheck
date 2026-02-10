"""Error formatting utilities for consistent error messages.

This module provides helper functions for formatting error messages consistently
across the codebase. All user-facing errors should use these utilities.

Error Style Guide:
- User-facing errors use 'Error: ' prefix
- Field errors use structured format: '<entity> field '<field>' <issue>'
- Use present tense: 'must be', 'is required'
- Avoid emojis in error messages (keep in progress displays only)
- Include actionable hints where helpful
- Be concise but informative
"""


def format_error(message: str) -> str:
    """Format an error message with consistent prefix.

    Args:
        message: The error message to format

    Returns:
        Formatted error message with 'Error: ' prefix

    Examples:
        >>> format_error("file not found")
        'Error: file not found'

        >>> format_error("agent 'foo' not found")
        "Error: agent 'foo' not found"
    """
    return f"Error: {message}"


def format_field_error(entity: str, field: str, issue: str) -> str:
    """Format a field validation error with structured format.

    Args:
        entity: Name of the entity being validated (e.g., "Harness 'claude'")
        field: Name of the field that failed validation
        issue: Description of the issue (e.g., "must be a non-empty string")

    Returns:
        Formatted field error message

    Examples:
        >>> format_field_error("Harness 'claude'", "name", "must be a non-empty string")
        "Harness 'claude' field 'name' must be a non-empty string"

        >>> format_field_error("Dependency 'node'", "version_command", "is required")
        "Dependency 'node' field 'version_command' is required"
    """
    return f"{entity} field '{field}' {issue}"


def format_suggestion(message: str, suggestion: str) -> str:
    """Format an error message with a helpful suggestion.

    Args:
        message: The error message
        suggestion: Helpful suggestion or hint for the user

    Returns:
        Formatted error with suggestion

    Examples:
        >>> format_suggestion("agent 'foo' not found", "run 'reincheck list' to see available agents")
        "Error: agent 'foo' not found. Hint: run 'reincheck list' to see available agents"

        >>> format_suggestion("config file not found", "run 'reincheck config init' to create one")
        "Error: config file not found. Hint: run 'reincheck config init' to create one"
    """
    return f"{format_error(message)}. Hint: {suggestion}"


__all__ = [
    "format_error",
    "format_field_error",
    "format_suggestion",
]

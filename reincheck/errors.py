"""Error formatting utilities for consistent user-facing error messages.

This module provides functions for formatting error messages in a consistent
style across the reincheck codebase.

Error Style Guide:
- User-facing errors use 'Error: ' prefix
- Field errors use structured format: '<entity> field <field> <issue>'
- Use present tense: 'must be', 'is required'
- Avoid emojis in error messages (keep in progress displays only)
- Include actionable hints where helpful
"""


def format_error(message: str) -> str:
    """Format a general error message with consistent prefix.

    Args:
        message: The error message to format

    Returns:
        Formatted error message with 'Error: ' prefix

    Example:
        >>> format_error("agent not found")
        'Error: agent not found'
    """
    return f"Error: {message}"


def format_field_error(entity: str, field: str, issue: str) -> str:
    """Format a field validation error in structured format.

    Args:
        entity: The entity name (e.g., "Harness 'claude'", "Dependency 'npm'")
        field: The field name that failed validation
        issue: The issue description (e.g., "must be a non-empty string")

    Returns:
        Formatted field error message

    Example:
        >>> format_field_error("Harness 'claude'", "name", "must be a non-empty string")
        "Harness 'claude' field 'name' must be a non-empty string"
    """
    return f"{entity} field '{field}' {issue}"


def format_suggestion(message: str, suggestion: str) -> str:
    """Format an error message with a helpful suggestion.

    Args:
        message: The error message
        suggestion: Helpful suggestion or hint for the user

    Returns:
        Formatted error message with suggestion

    Example:
        >>> format_suggestion("agent not found", "run 'reincheck list' to see available agents")
        "Error: agent not found. Hint: run 'reincheck list' to see available agents"
    """
    return f"{format_error(message)}. Hint: {suggestion}"


__all__ = [
    "format_error",
    "format_field_error",
    "format_suggestion",
]

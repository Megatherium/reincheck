"""Configuration loading and JSON preprocessing utilities."""

import json
from pathlib import Path


class ConfigError(Exception):
    """Raised when config loading or parsing fails.
    
    Provides detailed error messages including line numbers,
    column positions, and caret indicators for syntax errors.
    """
    pass


def preprocess_jsonish(text: str) -> str:
    """
    Preprocess JSON-ish text into strict JSON.

    Handles:
    - // line comments (replaced with spaces)
    - Trailing commas before ] or } (replaced with space)
    - Properly handles strings (escaped quotes don't end strings)

    Replaces stripped characters with spaces to preserve line/column positions
    for error messages.

    Args:
        text: JSON-ish text with optional // comments and trailing commas

    Returns:
        Strict JSON text ready for json.loads()
    """
    result = []
    i = 0
    n = len(text)

    # State constants
    NORMAL = 0
    IN_STRING = 1
    ESCAPE = 2
    SLASH = 3  # Saw '/', checking if next is '/' for comment
    IN_COMMENT = 4

    state = NORMAL

    # Track potential trailing comma: we need to know if a comma
    # is followed only by whitespace then ] or }
    # We'll do a lookahead when we see a comma in NORMAL state

    while i < n:
        char = text[i]

        if state == IN_COMMENT:
            # Inside a // comment - replace everything with space until newline
            if char == "\n":
                result.append(char)  # Keep newline
                state = NORMAL
            else:
                result.append(" ")  # Replace comment chars with space
            i += 1

        elif state == ESCAPE:
            # Previous char was backslash in a string
            # Current char is escaped, pass it through
            result.append(char)
            state = IN_STRING
            i += 1

        elif state == IN_STRING:
            if char == "\\":
                result.append(char)
                state = ESCAPE
            elif char == '"':
                result.append(char)
                state = NORMAL
            else:
                result.append(char)
            i += 1

        elif state == SLASH:
            # Previous char was '/', check if this is '//'
            if char == "/":
                # It's a comment start - replace both slashes with spaces
                result[-1] = " "  # Replace previous '/'
                result.append(" ")  # Replace this '/'
                state = IN_COMMENT
            else:
                # Not a comment, just a single '/'
                result.append(char)
                state = NORMAL
            i += 1

        else:  # state == NORMAL
            if char == '"':
                result.append(char)
                state = IN_STRING
                i += 1
            elif char == "/":
                result.append(char)
                state = SLASH
                i += 1
            elif char == ",":
                # Check if this is a trailing comma
                # Look ahead for whitespace and // comments, then ] or }
                j = i + 1
                while j < n:
                    if text[j] in " \t\r\n":
                        j += 1
                    elif text[j] == "/" and j + 1 < n and text[j + 1] == "/":
                        # Skip to end of comment (newline or EOF)
                        j += 2
                        while j < n and text[j] != "\n":
                            j += 1
                    else:
                        break
                if j < n and text[j] in "]}":
                    # It's a trailing comma - replace with space
                    result.append(" ")
                else:
                    # Not trailing, keep it
                    result.append(char)
                i += 1
            else:
                result.append(char)
                i += 1

    # Handle edge case: file ends while in SLASH state
    # (single '/' at end that's not a comment)
    if state == SLASH:
        # Already added the '/', which is correct
        pass

    return "".join(result)


def _format_syntax_error(original_text: str, error: json.JSONDecodeError) -> str:
    """Format a JSON syntax error with line, caret, and context.
    
    Args:
        original_text: The original text before preprocessing
        error: The JSONDecodeError raised by json.loads()
        
    Returns:
        A formatted error message string
    """
    lines = original_text.split('\n')
    line_num = error.lineno
    col_num = error.colno
    
    # Build the message
    msg_parts = [
        f"Config syntax error at line {line_num}, col {col_num}: {error.msg}"
    ]
    
    # Add the offending line if it exists
    if 1 <= line_num <= len(lines):
        offending_line = lines[line_num - 1]
        msg_parts.append(offending_line)
        
        # Build caret (handle tabs by counting them as single chars)
        caret_pos = col_num - 1  # Convert to 0-indexed
        caret = ' ' * caret_pos + '^'
        msg_parts.append(caret)
    
    return '\n'.join(msg_parts)


def load_config(path_or_text: Path | str) -> dict:
    """Load and parse a JSON config file.
    
    Accepts either a file path or raw text. The input can be 'JSON-ish':
    trailing commas and // line comments are tolerated.
    
    Args:
        path_or_text: Either a Path to a JSON file, or a string containing
            JSON or JSON-ish text
            
    Returns:
        A dict containing the parsed config data
        
    Raises:
        ConfigError: If the file cannot be read or contains syntax errors.
        TypeError: If path_or_text is neither Path nor str.
    """
    # Determine if we have a path or text
    if isinstance(path_or_text, Path):
        file_path = path_or_text
        try:
            original_text = file_path.read_text(encoding='utf-8')
        except FileNotFoundError:
            raise ConfigError(f"Config file not found: {file_path}")
        except PermissionError:
            raise ConfigError(f"Permission denied reading config file: {file_path}")
        except UnicodeDecodeError:
            raise ConfigError(f"Config file is not valid UTF-8: {file_path}")
        except IOError as e:
            raise ConfigError(f"Error reading config file {file_path}: {e}")
    elif isinstance(path_or_text, str):
        original_text = path_or_text
    else:
        raise TypeError(f"path_or_text must be Path or str, got {type(path_or_text).__name__}")
    
    # Preprocess to handle trailing commas and comments
    preprocessed = preprocess_jsonish(original_text)
    
    # Parse the JSON
    try:
        result = json.loads(preprocessed)
    except json.JSONDecodeError as e:
        # Re-raise with friendly error message
        error_msg = _format_syntax_error(original_text, e)
        raise ConfigError(error_msg) from e
    
    # Validate that we got a dict (not a list, string, etc.)
    if not isinstance(result, dict):
        raise ConfigError(f"Config must be a JSON object, got {type(result).__name__}")
    
    return result


__all__ = ['ConfigError', 'preprocess_jsonish', 'load_config']

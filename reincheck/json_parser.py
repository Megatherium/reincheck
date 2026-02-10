"""JSON preprocessing utilities.

This module provides tools for converting JSON-ish text (with comments
and trailing commas) into strict JSON.

The state machine approach ensures that:
- Line comments (//) are handled correctly
- Trailing commas before ] or } are removed
- Strings with escaped quotes are handled properly
- Error messages preserve original line/column positions
"""

from typing import Final


# State constants for the state machine
_NORMAL: Final[int] = 0
_IN_STRING: Final[int] = 1
_ESCAPE: Final[int] = 2
_SLASH: Final[int] = 3
_IN_COMMENT: Final[int] = 4


class JsonPreprocessor:
    """State machine for preprocessing JSON-ish text.

    This class handles the conversion of JSON-like text that may contain
    // line comments and trailing commas into strict JSON.

    Example:
        >>> preprocessor = JsonPreprocessor()
        >>> text = '{"a": 1, // comment\\n}'
        >>> result = preprocessor.preprocess(text)
        >>> import json
        >>> json.loads(result)
        {'a': 1}
    """

    def __init__(self) -> None:
        """Initialize the preprocessor."""
        self.state: int = _NORMAL

    def preprocess(self, text: str) -> str:
        """Preprocess JSON-ish text into strict JSON.

        Handles:
        - // line comments (replaced with spaces)
        - Trailing commas before ] or } (replaced with space)
        - Properly handles strings (escaped quotes don't end strings)

        Replaces stripped characters with spaces to preserve line/column
        positions for error messages.

        Args:
            text: JSON-ish text with optional // comments and trailing commas

        Returns:
            Strict JSON text ready for json.loads()

        Example:
            >>> preprocessor = JsonPreprocessor()
            >>> text = '{"items": [1, 2, 3,]}'
            >>> result = preprocessor.preprocess(text)
            >>> result
            '{"items": [1, 2, 3 ]}'
        """
        result: list[str] = []
        i = 0
        n = len(text)
        self.state = _NORMAL

        while i < n:
            char = text[i]

            if self.state == _IN_COMMENT:
                i = self._process_comment_state(char, result, i)
            elif self.state == _ESCAPE:
                i = self._process_escape_state(char, result, i)
            elif self.state == _IN_STRING:
                i = self._process_string_state(char, result, i)
            elif self.state == _SLASH:
                i = self._process_slash_state(char, result, text, i, n)
            else:
                i = self._process_normal_state(char, result, text, i, n)

        self._handle_end_state(result)

        return "".join(result)

    def _process_normal_state(
        self, char: str, result: list[str], text: str, i: int, n: int
    ) -> int:
        """Handle character in NORMAL state.

        Args:
            char: Current character
            result: Result list to append to
            text: Full input text
            i: Current index
            n: Length of text

        Returns:
            Updated index after processing
        """
        if char == '"':
            result.append(char)
            self.state = _IN_STRING
        elif char == "/":
            result.append(char)
            self.state = _SLASH
        elif char == ",":
            if self._is_trailing_comma(text, i, n):
                result.append(" ")
            else:
                result.append(char)
        else:
            result.append(char)
        return i + 1

    def _process_string_state(self, char: str, result: list[str], i: int) -> int:
        """Handle character in IN_STRING state.

        Args:
            char: Current character
            result: Result list to append to
            i: Current index

        Returns:
            Updated index after processing
        """
        if char == "\\":
            result.append(char)
            self.state = _ESCAPE
        elif char == '"':
            result.append(char)
            self.state = _NORMAL
        else:
            result.append(char)
        return i + 1

    def _process_escape_state(self, char: str, result: list[str], i: int) -> int:
        """Handle character in ESCAPE state.

        Previous char was backslash in a string. Current char is escaped,
        pass it through and return to IN_STRING.

        Args:
            char: Current character
            result: Result list to append to
            i: Current index

        Returns:
            Updated index after processing
        """
        result.append(char)
        self.state = _IN_STRING
        return i + 1

    def _process_slash_state(
        self, char: str, result: list[str], text: str, i: int, n: int
    ) -> int:
        """Handle character in SLASH state.

        Previous char was '/', check if this is '//' for comment start.

        Args:
            char: Current character
            result: Result list to append to
            text: Full input text
            i: Current index
            n: Length of text

        Returns:
            Updated index after processing
        """
        if char == "/":
            result[-1] = " "
            result.append(" ")
            self.state = _IN_COMMENT
        else:
            result.append(char)
            self.state = _NORMAL
        return i + 1

    def _process_comment_state(self, char: str, result: list[str], i: int) -> int:
        """Handle character in IN_COMMENT state.

        Replace everything with space until newline.

        Args:
            char: Current character
            result: Result list to append to
            i: Current index

        Returns:
            Updated index after processing
        """
        if char == "\n":
            result.append(char)
            self.state = _NORMAL
        else:
            result.append(" ")
        return i + 1

    def _is_trailing_comma(self, text: str, i: int, n: int) -> bool:
        """Check if comma at position i is a trailing comma.

        A trailing comma is followed only by whitespace and // comments,
        then ] or }.

        Args:
            text: Full input text
            i: Current index (position of comma)
            n: Length of text

        Returns:
            True if this is a trailing comma, False otherwise
        """
        j = i + 1
        while j < n:
            if text[j] in " \t\r\n":
                j += 1
            elif text[j] == "/" and j + 1 < n and text[j + 1] == "/":
                j += 2
                while j < n and text[j] != "\n":
                    j += 1
            else:
                break
        return j < n and text[j] in "]}"

    def _handle_end_state(self, result: list[str]) -> None:
        """Handle edge case: file ends while in SLASH state.

        Args:
            result: Result list (unchanged in this case)
        """
        if self.state == _SLASH:
            pass


def preprocess_jsonish(text: str) -> str:
    """Preprocess JSON-ish text into strict JSON.

    This is the public interface for JSON preprocessing. It creates
    an instance of JsonPreprocessor and delegates to it.

    Handles:
    - // line comments (replaced with spaces)
    - Trailing commas before ] or } (replaced with space)
    - Properly handles strings (escaped quotes don't end strings)

    Replaces stripped characters with spaces to preserve line/column
    positions for error messages.

    Args:
        text: JSON-ish text with optional // comments and trailing commas

    Returns:
        Strict JSON text ready for json.loads()

    Examples:
        >>> import json
        >>> result = preprocess_jsonish('{"a": 1,}')
        >>> json.loads(result)
        {'a': 1}

        >>> result = preprocess_jsonish('{"a": 1} // comment')
        >>> json.loads(result)
        {'a': 1}

        >>> result = preprocess_jsonish('{"url": "https://example.com//path"}')
        >>> json.loads(result)
        {'url': 'https://example.com//path'}

        >>> result = preprocess_jsonish('{"s": "He said \\"hi\\""}')
        >>> json.loads(result)
        {'s': 'He said "hi"'}
    """
    preprocessor = JsonPreprocessor()
    return preprocessor.preprocess(text)


__all__ = ["preprocess_jsonish", "JsonPreprocessor"]

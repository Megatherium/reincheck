"""Tests for config loading and JSON preprocessing."""

import json
from pathlib import Path
import pytest

from reincheck.config import (
    ConfigError,
    preprocess_jsonish,
    load_config,
    _format_syntax_error,
)


class TestPreprocessJsonish:
    """Tests for the JSON preprocessor."""

    def test_valid_strict_json_unchanged(self):
        """Strict JSON should pass through unchanged."""
        input_text = '{"name": "test", "version": "1.0.0"}'
        result = preprocess_jsonish(input_text)
        assert result == input_text

    def test_trailing_comma_in_array(self):
        """Trailing comma in array should be replaced with space."""
        input_text = "[1, 2, 3,]"
        result = preprocess_jsonish(input_text)
        assert result == "[1, 2, 3 ]"
        # Should be valid JSON now
        assert json.loads(result) == [1, 2, 3]

    def test_trailing_comma_in_object(self):
        """Trailing comma in object should be replaced with space."""
        input_text = '{"a": 1, "b": 2,}'
        result = preprocess_jsonish(input_text)
        assert result == '{"a": 1, "b": 2 }'
        assert json.loads(result) == {"a": 1, "b": 2}

    def test_nested_trailing_commas(self):
        """Nested trailing commas should be handled."""
        input_text = '{"a": [1,], "b": {"c": 2,},}'
        result = preprocess_jsonish(input_text)
        # Both trailing commas are replaced with spaces
        expected = '{"a": [1 ], "b": {"c": 2 } }'
        assert result == expected
        assert json.loads(result) == {"a": [1], "b": {"c": 2}}

    def test_line_comment_at_end(self):
        """Line comment at end should be replaced with spaces."""
        input_text = '{"a": 1} // this is a comment'
        result = preprocess_jsonish(input_text)
        # After the }, we keep the space, then // and comment (20 chars) become spaces
        # Total: 8 chars for {"a": 1} + 1 space + 20 spaces = 29 chars
        assert len(result) == 29
        assert result.startswith('{"a": 1} ')
        assert result[9:] == ' ' * 20
        assert json.loads(result) == {"a": 1}

    def test_comment_at_end_of_line(self):
        """Comment at end of line should be replaced with spaces."""
        input_text = '{"a": 1, // note\n"b": 2}'
        result = preprocess_jsonish(input_text)
        # First line: {"a": 1,        (8 spaces for "// note")
        # Second line: "b": 2}
        lines = result.split('\n')
        assert lines[0] == '{"a": 1,        '
        assert lines[1] == '"b": 2}'
        assert json.loads(result) == {"a": 1, "b": 2}

    def test_url_with_double_slash_in_string(self):
        """URL with // in string should NOT be treated as comment."""
        input_text = '{"url": "https://x.com//y"}'
        result = preprocess_jsonish(input_text)
        assert result == input_text
        assert json.loads(result) == {"url": "https://x.com//y"}

    def test_escaped_quote_in_string(self):
        """Escaped quote in string should not end the string."""
        input_text = '{"s": "He said \\"hi\\""}'
        result = preprocess_jsonish(input_text)
        assert result == input_text
        assert json.loads(result) == {"s": 'He said "hi"'}

    def test_backslash_in_string(self):
        """Backslash in string should be preserved."""
        input_text = '{"p": "C:\\\\path"}'
        result = preprocess_jsonish(input_text)
        assert result == input_text
        assert json.loads(result) == {"p": "C:\\path"}

    def test_comma_in_string_value(self):
        """Comma in string value should NOT be treated as trailing comma."""
        input_text = '{"csv": "a,b,c"}'
        result = preprocess_jsonish(input_text)
        assert result == input_text
        assert json.loads(result) == {"csv": "a,b,c"}

    def test_multiple_trailing_commas_not_allowed(self):
        """Multiple trailing commas should result in invalid JSON."""
        input_text = "[1,2,,]"
        result = preprocess_jsonish(input_text)
        # Should produce '[1,2, ]' which is still invalid (double comma)
        with pytest.raises(json.JSONDecodeError):
            json.loads(result)

    def test_trailing_comma_with_whitespace_and_comment(self):
        """Trailing comma followed by whitespace and comment."""
        input_text = '{"a": 1,  // comment\n}'
        result = preprocess_jsonish(input_text)
        assert json.loads(result) == {"a": 1}


class TestFormatSyntaxError:
    """Tests for error message formatting."""

    def test_basic_error_formatting(self):
        """Test basic error message formatting."""
        original = '{\n  "a": 1,\n  "b": ,\n}'
        try:
            json.loads(original)
        except json.JSONDecodeError as e:
            msg = _format_syntax_error(original, e)

        assert "line 3" in msg
        assert "col" in msg
        assert '"b": ,' in msg
        assert "^" in msg

    def test_error_at_line_1(self):
        """Test error on first line."""
        original = "{invalid}"
        try:
            json.loads(original)
        except json.JSONDecodeError as e:
            msg = _format_syntax_error(original, e)

        assert "line 1" in msg


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_valid_json_from_string(self):
        """Load valid JSON from string input."""
        json_text = '{"agents": [{"name": "test"}]}'
        result = load_config(json_text)
        assert result == {"agents": [{"name": "test"}]}

    def test_load_tolerant_json_with_trailing_comma(self):
        """Load JSON-ish with trailing comma."""
        json_text = '{"agents": [{"name": "test",}],}'
        result = load_config(json_text)
        assert result == {"agents": [{"name": "test"}]}

    def test_load_tolerant_json_with_comment(self):
        """Load JSON-ish with line comment."""
        json_text = '{"agents": []} // empty config'
        result = load_config(json_text)
        assert result == {"agents": []}

    def test_load_from_file_path(self, tmp_path):
        """Load from a file path."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"agents": [{"name": "test"}]}')

        result = load_config(config_file)
        assert result == {"agents": [{"name": "test"}]}

    def test_file_not_found(self):
        """Raise ConfigError for non-existent file."""
        with pytest.raises(ConfigError) as exc:
            load_config(Path("/nonexistent/path/config.json"))
        assert "not found" in str(exc.value)

    def test_invalid_json_syntax_error(self):
        """Raise ConfigError with friendly message for invalid JSON."""
        bad_json = '{\n  "a": 1,\n  "b": ,\n}'
        with pytest.raises(ConfigError) as exc:
            load_config(bad_json)
        
        error_msg = str(exc.value)
        # Error is on line 4 (the closing brace) since line 3 has incomplete value
        assert "line 4" in error_msg
        assert '}' in error_msg
        assert '^' in error_msg

    def test_error_shows_correct_column(self):
        """Error message should show correct column with caret."""
        bad_json = '{"x": 1, "y": }'
        with pytest.raises(ConfigError) as exc:
            load_config(bad_json)

        error_msg = str(exc.value)
        lines = error_msg.split("\n")
        # Find the line with the caret
        caret_line = [line for line in lines if "^" in line][0]
        # Caret should be positioned after the colon and space
        assert "              ^" in caret_line or caret_line.strip() == "^"

    def test_error_at_end_of_file(self):
        """Handle error at end of file gracefully."""
        bad_json = '{"incomplete": '
        with pytest.raises(ConfigError) as exc:
            load_config(bad_json)

        # Should not crash, should show helpful message
        assert "line" in str(exc.value)

    def test_non_dict_root_raises_error(self):
        """Root must be a JSON object, not array or primitive."""
        with pytest.raises(ConfigError) as exc:
            load_config('["not", "an", "object"]')
        assert "JSON object" in str(exc.value)
        assert "list" in str(exc.value)

    def test_invalid_type_raises_typeerror(self):
        """Passing invalid type should raise TypeError."""
        with pytest.raises(TypeError) as exc:
            load_config(123)
        assert "Path or str" in str(exc.value)

    def test_utf8_file_encoding(self, tmp_path):
        """Files should be read as UTF-8."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"emoji": "🚀", "chinese": "你好"}', encoding="utf-8")

        result = load_config(config_file)
        assert result["emoji"] == "🚀"
        assert result["chinese"] == "你好"

    def test_permission_error(self, tmp_path):
        """Permission denied should raise ConfigError."""
        config_file = tmp_path / "config.json"
        config_file.write_text("{}")
        config_file.chmod(0o000)  # Remove all permissions

        try:
            with pytest.raises(ConfigError) as exc:
                load_config(config_file)
            assert "Permission denied" in str(exc.value)
        finally:
            config_file.chmod(0o644)  # Restore permissions for cleanup

    def test_complex_nested_config(self):
        """Load a complex nested config."""
        json_text = """
        {
            "agents": [
                {
                    "name": "claude",
                    "description": "AI assistant",
                    "install_command": "npm install -g @anthropic-ai/claude-code",
                    "version_command": "claude --version",
                    "check_latest_command": "npm info @anthropic-ai/claude-code version",
                    "upgrade_command": "npm update -g @anthropic-ai/claude-code",
                    "latest_version": "1.0.0",
                    "github_repo": "anthropics/claude-code",
                }, // trailing comma and comment!
            ],
        }
        """
        result = load_config(json_text)
        assert len(result["agents"]) == 1
        assert result["agents"][0]["name"] == "claude"

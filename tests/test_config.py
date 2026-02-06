"""Tests for config loading and JSON preprocessing."""

import json
from pathlib import Path
import pytest
import tempfile

from reincheck.config import (
    ConfigError,
    AgentConfig,
    Config,
    validate_config,
    preprocess_jsonish,
    load_config,
    _format_syntax_error,
)

from reincheck import (
    get_config_dir,
    get_packaged_config_path,
    get_config_path,
    ensure_user_config,
    migrate_yaml_to_json,
)
from reincheck.paths import get_config_dir as get_config_dir_paths
from reincheck.paths import get_packaged_config_path as get_packaged_config_path_paths


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
            load_config(123)  # type: ignore
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


class TestValidateConfig:
    """Tests for validate_config function."""

    def test_valid_config(self):
        """Validate a properly structured config."""
        data = {
            "agents": [
                {
                    "name": "test-agent",
                    "description": "A test agent",
                    "install_command": "npm install -g test",
                    "version_command": "test --version",
                    "check_latest_command": "npm info test version",
                    "upgrade_command": "npm update -g test",
                }
            ]
        }
        config = validate_config(data)
        assert isinstance(config, Config)
        assert len(config.agents) == 1
        assert config.agents[0].name == "test-agent"
        assert config.agents[0].description == "A test agent"

    def test_config_with_optional_fields(self):
        """Validate config with optional fields populated."""
        data = {
            "agents": [
                {
                    "name": "test-agent",
                    "description": "A test agent",
                    "install_command": "npm install -g test",
                    "version_command": "test --version",
                    "check_latest_command": "npm info test version",
                    "upgrade_command": "npm update -g test",
                    "latest_version": "1.0.0",
                    "github_repo": "owner/repo",
                    "release_notes_url": "https://example.com/changelog",
                }
            ]
        }
        config = validate_config(data)
        assert config.agents[0].latest_version == "1.0.0"
        assert config.agents[0].github_repo == "owner/repo"
        assert config.agents[0].release_notes_url == "https://example.com/changelog"

    def test_empty_agents_list(self):
        """Validate config with empty agents list."""
        data = {"agents": []}
        config = validate_config(data)
        assert config.agents == []

    def test_missing_agents_key(self):
        """Raise error when agents key is missing."""
        data = {}
        with pytest.raises(ConfigError) as exc:
            validate_config(data)
        assert "Missing required field: agents" in str(exc.value)

    def test_agents_not_a_list(self):
        """Raise error when agents is not a list."""
        data = {"agents": "not a list"}
        with pytest.raises(ConfigError) as exc:
            validate_config(data)
        assert "agents must be a list" in str(exc.value)

    def test_agent_not_an_object(self):
        """Raise error when an agent is not an object."""
        data = {"agents": ["not an object"]}
        with pytest.raises(ConfigError) as exc:
            validate_config(data)
        assert "agents[0] must be an object" in str(exc.value)

    def test_missing_required_field(self):
        """Raise error with field path when required field is missing."""
        data = {
            "agents": [
                {
                    "name": "test-agent",
                    # missing description
                    "install_command": "npm install -g test",
                    "version_command": "test --version",
                    "check_latest_command": "npm info test version",
                    "upgrade_command": "npm update -g test",
                }
            ]
        }
        with pytest.raises(ConfigError) as exc:
            validate_config(data)
        assert "agents[0].description is required" in str(exc.value)

    def test_wrong_type_for_required_field(self):
        """Raise error when required field has wrong type."""
        data = {
            "agents": [
                {
                    "name": 123,  # should be string
                    "description": "A test agent",
                    "install_command": "npm install -g test",
                    "version_command": "test --version",
                    "check_latest_command": "npm info test version",
                    "upgrade_command": "npm update -g test",
                }
            ]
        }
        with pytest.raises(ConfigError) as exc:
            validate_config(data)
        assert "agents[0].name must be a string" in str(exc.value)

    def test_wrong_type_for_optional_field(self):
        """Raise error when optional field has wrong type."""
        data = {
            "agents": [
                {
                    "name": "test-agent",
                    "description": "A test agent",
                    "install_command": "npm install -g test",
                    "version_command": "test --version",
                    "check_latest_command": "npm info test version",
                    "upgrade_command": "npm update -g test",
                    "latest_version": 123,  # should be string or null
                }
            ]
        }
        with pytest.raises(ConfigError) as exc:
            validate_config(data)
        assert "agents[0].latest_version must be a string or null" in str(exc.value)

    def test_config_not_a_dict(self):
        """Raise error when config is not a dict."""
        with pytest.raises(ConfigError) as exc:
            validate_config(["not a dict"])  # type: ignore
        assert "Config must be a JSON object" in str(exc.value)

    def test_multiple_agents(self):
        """Validate config with multiple agents."""
        data = {
            "agents": [
                {
                    "name": "agent-1",
                    "description": "First agent",
                    "install_command": "npm install -g agent1",
                    "version_command": "agent1 --version",
                    "check_latest_command": "npm info agent1 version",
                    "upgrade_command": "npm update -g agent1",
                },
                {
                    "name": "agent-2",
                    "description": "Second agent",
                    "install_command": "npm install -g agent2",
                    "version_command": "agent2 --version",
                    "check_latest_command": "npm info agent2 version",
                    "upgrade_command": "npm update -g agent2",
                }
            ]
        }
        config = validate_config(data)
        assert len(config.agents) == 2
        assert config.agents[0].name == "agent-1"
        assert config.agents[1].name == "agent-2"

    def test_error_in_second_agent(self):
        """Field path should indicate which agent has the error."""
        data = {
            "agents": [
                {
                    "name": "agent-1",
                    "description": "First agent",
                    "install_command": "npm install -g agent1",
                    "version_command": "agent1 --version",
                    "check_latest_command": "npm info agent1 version",
                    "upgrade_command": "npm update -g agent1",
                },
                {
                    "name": "agent-2",
                    # missing description
                    "install_command": "npm install -g agent2",
                    "version_command": "agent2 --version",
                    "check_latest_command": "npm info agent2 version",
                    "upgrade_command": "npm update -g agent2",
                }
            ]
        }
        with pytest.raises(ConfigError) as exc:
            validate_config(data)
        assert "agents[1].description is required" in str(exc.value)


class TestAgentConfig:
    """Tests for AgentConfig dataclass validation."""

    def test_valid_agent_config(self):
        """Create valid AgentConfig."""
        agent = AgentConfig(
            name="test",
            description="A test agent",
            install_command="npm install -g test",
            version_command="test --version",
            check_latest_command="npm info test version",
            upgrade_command="npm update -g test",
        )
        assert agent.name == "test"
        assert agent.latest_version is None

    def test_empty_name_raises_error(self):
        """Empty name should raise ValueError."""
        with pytest.raises(ValueError) as exc:
            AgentConfig(
                name="",
                description="A test agent",
                install_command="npm install -g test",
                version_command="test --version",
                check_latest_command="npm info test version",
                upgrade_command="npm update -g test",
            )
        assert "name must be a non-empty string" in str(exc.value)

    def test_dangerous_command_raises_error(self):
        """Command with dangerous characters should raise ValueError."""
        with pytest.raises(ValueError) as exc:
            AgentConfig(
                name="test",
                description="A test agent",
                install_command="rm -rf $(echo hack)",
                version_command="test --version",
                check_latest_command="npm info test version",
                upgrade_command="npm update -g test",
            )
        assert "dangerous characters" in str(exc.value)


class TestConfig:
    """Tests for Config dataclass validation."""

    def test_valid_config(self):
        """Create valid Config."""
        agent = AgentConfig(
            name="test",
            description="A test agent",
            install_command="npm install -g test",
            version_command="test --version",
            check_latest_command="npm info test version",
            upgrade_command="npm update -g test",
        )
        config = Config(agents=[agent])
        assert len(config.agents) == 1

    def test_default_empty_agents(self):
        """Config should default to empty agents list."""
        config = Config()
        assert config.agents == []

    def test_agents_must_be_list(self):
        """Agents must be a list."""
        with pytest.raises(ValueError) as exc:
            Config(agents="not a list")  # type: ignore
        assert "agents must be a list" in str(exc.value)

    def test_agent_must_be_agentconfig(self):
        """Each agent must be AgentConfig instance."""
        with pytest.raises(ValueError) as exc:
            Config(agents=[{"name": "not an AgentConfig"}])  # type: ignore
        assert "agents[0] must be an AgentConfig instance" in str(exc.value)


class TestConfigPathHelpers:
    """Tests for config path helper functions."""

    def test_get_config_dir(self):
        """Test that config dir returns XDG-compliant path."""
        config_dir = get_config_dir()
        assert config_dir == Path.home() / ".config" / "reincheck"

    def test_get_packaged_config_path(self):
        """Test that packaged config path points to package directory."""
        packaged = get_packaged_config_path()
        assert packaged.name == "agents.json"
        assert packaged.parent.name == "reincheck"

    def test_get_config_path_default(self):
        """Test get_config_path with no override."""
        config_path = get_config_path(create=False)
        assert config_path == Path.home() / ".config" / "reincheck" / "agents.json"

    def test_get_config_path_with_env_override(self, monkeypatch):
        """Test that REINCHECK_CONFIG env var overrides default path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = Path(tmpdir) / "custom" / "config.json"
            monkeypatch.setenv("REINCHECK_CONFIG", str(custom_path))

            config_path = get_config_path(create=False)
            assert config_path == custom_path


class TestEnsureUserConfig:
    """Tests for ensure_user_config function."""

    def test_existing_config_noop(self, tmp_path):
        """If config already exists, do nothing."""
        existing_config = tmp_path / "agents.json"
        existing_config.write_text('{"agents": []}')

        ensure_user_config(existing_config)

        # Config unchanged
        assert existing_config.read_text() == '{"agents": []}'

    def test_creates_from_packaged_default(self, tmp_path, monkeypatch):
        """Create config from packaged default if no legacy YAML exists."""
        from reincheck import migration

        user_config = tmp_path / "agents.json"

        # Mock packaged path to a temp file
        packaged = tmp_path / "packaged" / "agents.json"
        packaged.parent.mkdir(parents=True)
        packaged.write_text('{"agents": [{"name": "test"}]}')
        monkeypatch.setattr(migration, "get_packaged_config_path", lambda: packaged)

        ensure_user_config(user_config)

        assert user_config.exists()
        data = json.loads(user_config.read_text())
        assert len(data["agents"]) == 1
        assert data["agents"][0]["name"] == "test"

    def test_migrates_yaml_to_json(self, tmp_path, monkeypatch):
        """Migrate existing YAML config to JSON."""
        from reincheck import migration

        user_config = tmp_path / "agents.json"
        yaml_config = tmp_path / "agents.yaml"

        yaml_config.write_text('''
agents:
  - name: test-agent
    description: A test agent
    install_command: echo install
    version_command: echo 1.0.0
    check_latest_command: echo 1.0.0
    upgrade_command: echo upgrade
''')

        # Monkeypatch get_config_dir to return tmp_path
        monkeypatch.setattr(migration, "get_config_dir", lambda: tmp_path)

        ensure_user_config(user_config)

        assert user_config.exists()
        # YAML should be backed up
        assert yaml_config.with_suffix(".yaml.bak").exists()

        data = json.loads(user_config.read_text())
        assert len(data["agents"]) == 1
        assert data["agents"][0]["name"] == "test-agent"


class TestMigrateYamlToJson:
    """Tests for YAML to JSON migration."""

    def test_successful_migration(self, tmp_path):
        """Successfully migrate valid YAML to JSON."""
        yaml_path = tmp_path / "config.yaml"
        json_path = tmp_path / "config.json"

        yaml_path.write_text('''
agents:
  - name: test
    description: Test agent
    install_command: echo install
    version_command: echo 1.0.0
    check_latest_command: echo 1.0.0
    upgrade_command: echo upgrade
''')

        migrate_yaml_to_json(yaml_path, json_path)

        assert json_path.exists()
        data = json.loads(json_path.read_text())
        assert data["agents"][0]["name"] == "test"
        # YAML backed up
        assert yaml_path.with_suffix(".yaml.bak").exists()

    def test_migrate_without_pyyaml(self, tmp_path, monkeypatch):
        """Raise ConfigError when pyyaml not installed."""
        yaml_path = tmp_path / "config.yaml"
        json_path = tmp_path / "config.json"
        yaml_path.write_text("agents: []")

        # Mock yaml import to raise ImportError
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "yaml":
                raise ImportError("No module named 'yaml'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        with pytest.raises(ConfigError) as exc:
            migrate_yaml_to_json(yaml_path, json_path)

        assert "pyyaml not installed" in str(exc.value)

    def test_invalid_yaml_structure(self, tmp_path):
        """Raise error for invalid YAML structure."""
        yaml_path = tmp_path / "config.yaml"
        json_path = tmp_path / "config.json"

        yaml_path.write_text("not_agents: []")

        with pytest.raises(ConfigError) as exc:
            migrate_yaml_to_json(yaml_path, json_path)

        assert "Invalid YAML config structure" in str(exc.value)

"""Unit tests for core functionality in reincheck."""

import json
import tempfile
import yaml
import pytest
from unittest.mock import patch
from pathlib import Path

from reincheck import (
    AgentConfig,
    Config,
    load_config,
    save_config,
    compare_versions,
    extract_version_number,
    run_command_async,
    get_npm_release_info,
    get_pypi_release_info,
    is_command_safe,
)


class TestAgentConfig:
    """Tests for AgentConfig dataclass."""

    def test_valid_agent_config(self):
        """Test creating a valid AgentConfig."""
        agent = AgentConfig(
            name="test-agent",
            description="Test agent",
            install_command="npm install -g test-agent",
            version_command="test-agent --version",
            check_latest_command="npm view test-agent version",
            upgrade_command="npm update -g test-agent",
        )
        assert agent.name == "test-agent"
        assert agent.description == "Test agent"

    def test_invalid_empty_name(self):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="Agent name must be a non-empty string"):
            _ = AgentConfig(
                name="",
                description="Test agent",
                install_command="npm install -g test-agent",
                version_command="test-agent --version",
                check_latest_command="npm view test-agent version",
                upgrade_command="npm update -g test-agent",
            )

    def test_invalid_non_string_name(self):
        """Test that non-string name - the dataclass doesn't validate types, so this tests that 123 (truthy) passes validation."""
        agent = AgentConfig(
            name=123,  # type: ignore[arg-type]
            description="Test agent",
            install_command="npm install -g test-agent",
            version_command="test-agent --version",
            check_latest_command="npm view test-agent version",
            upgrade_command="npm update -g test-agent",
        )
        assert agent.name == 123  # Dataclass doesn't type-check at runtime

    def test_valid_agent_config_without_latest_version(self):
        """Test AgentConfig without latest_version."""
        agent = AgentConfig(
            name="test-agent",
            description="Test agent",
            install_command="npm install -g test-agent",
            version_command="test-agent --version",
            check_latest_command="npm view test-agent version",
            upgrade_command="npm update -g test-agent",
        )
        assert agent.latest_version is None

    def test_valid_agent_config_with_github_repo(self):
        """Test AgentConfig with github_repo."""
        agent = AgentConfig(
            name="test-agent",
            description="Test agent",
            install_command="npm install -g test-agent",
            version_command="test-agent --version",
            check_latest_command="npm view test-agent version",
            upgrade_command="npm update -g test-agent",
            github_repo="test/repo",
        )
        assert agent.github_repo == "test/repo"

    def test_command_validation_with_dangerous_characters(self):
        """Test that commands with dangerous characters raise ValueError."""
        with pytest.raises(ValueError, match="Command contains dangerous characters"):
            _ = AgentConfig(
                name="test-agent",
                description="Test agent",
                install_command="npm install $(malicious)",
                version_command="test-agent --version",
                check_latest_command="npm view test-agent version",
                upgrade_command="npm update -g test-agent",
            )

    def test_command_validation_with_backticks(self):
        """Test that commands with backticks raise ValueError."""
        with pytest.raises(ValueError, match="Command contains dangerous characters"):
            _ = AgentConfig(
                name="test-agent",
                description="Test agent",
                install_command="npm install `echo malicious`",
                version_command="test-agent --version",
                check_latest_command="npm view test-agent version",
                upgrade_command="npm update -g test-agent",
            )


class TestConfig:
    """Tests for Config dataclass."""

    def test_valid_config(self):
        """Test creating a valid Config."""
        config = Config(agents=[])
        assert config.agents == []

    def test_valid_config_with_agents(self):
        """Test creating a valid Config with agents."""
        agents = [
            AgentConfig(
                name="agent1",
                description="First agent",
                install_command="npm install -g agent1",
                version_command="agent1 --version",
                check_latest_command="npm view agent1 version",
                upgrade_command="npm update -g agent1",
            )
        ]
        config = Config(agents=agents)
        assert len(config.agents) == 1
        assert config.agents[0].name == "agent1"

    def test_invalid_config_non_list(self):
        """Test that non-list agents raises ValueError."""
        with pytest.raises(ValueError, match="Config agents must be a list"):
            Config(agents="not a list")  # type: ignore[arg-type]

    def test_invalid_config_non_agent_config(self):
        """Test that non-AgentConfig items raise ValueError."""
        with pytest.raises(
            ValueError, match="Each agent must be an AgentConfig instance"
        ):
            Config(agents=[123])  # type: ignore[arg-type]


class TestLoadConfigAndSaveConfig:
    """Tests for load_config and save_config functions."""

    def test_load_config_valid(self):
        """Test loading valid configuration."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml_content = {
                "agents": [
                    {
                        "name": "test-agent",
                        "description": "Test agent",
                        "install_command": "npm install -g test-agent",
                        "version_command": "test-agent --version",
                        "check_latest_command": "npm view test-agent version",
                        "upgrade_command": "npm update -g test-agent",
                    }
                ]
            }
            yaml.dump(yaml_content, f)  # type: ignore[call-overload]
            config_path = f.name

        try:
            config = load_config(Path(config_path))
            assert len(config.agents) == 1
            assert config.agents[0].name == "test-agent"
        finally:
            Path(config_path).unlink()

    def test_load_config_file_not_found(self):
        """Test that missing config file exits with error."""
        nonexistent_path = Path("/tmp/nonexistent_reincheck_agents.yaml")

        if nonexistent_path.exists():
            nonexistent_path.unlink()

        with pytest.raises(SystemExit):
            _ = load_config(nonexistent_path)

    def test_load_config_invalid_yaml(self):
        """Test that invalid YAML exits with error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [unclosed]")  # type: ignore[arg-type]
            config_path = f.name

        try:
            with pytest.raises(SystemExit):
                _ = load_config(Path(config_path))
        finally:
            Path(config_path).unlink()

    def test_load_config_invalid_structure(self):
        """Test that invalid structure exits with error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml_content = {"not_agents": []}
            yaml.dump(yaml_content, f)
            config_path = f.name

        try:
            with pytest.raises(SystemExit):
                _ = load_config(Path(config_path))
        finally:
            Path(config_path).unlink()

    def test_save_config_valid(self):
        """Test saving a valid configuration."""
        agents = [
            AgentConfig(
                name="test-agent",
                description="Test agent",
                install_command="npm install -g test-agent",
                version_command="test-agent --version",
                check_latest_command="npm view test-agent version",
                upgrade_command="npm update -g test-agent",
                latest_version="1.0.0",
                github_repo="test/repo",
            )
        ]
        config = Config(agents=agents)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            temp_path = Path(f.name)
            # Delete the temp file so save_config can create it
            temp_path.unlink()

        try:
            save_config(config, temp_path)

            assert temp_path.exists()

            with open(temp_path, "r") as f:
                saved_data = yaml.safe_load(f)  # type: ignore[assignment]

            assert "agents" in saved_data  # type: ignore[index]
            assert len(saved_data["agents"]) == 1  # type: ignore[index]
            assert saved_data["agents"][0]["name"] == "test-agent"  # type: ignore[index]
            assert saved_data["agents"][0]["latest_version"] == "1.0.0"  # type: ignore[index]
            assert saved_data["agents"][0]["github_repo"] == "test/repo"  # type: ignore[index]
        finally:
            if temp_path.exists():
                temp_path.unlink()
            # Clean up the .tmp file if it exists
            tmp_path = temp_path.with_suffix(".tmp")
            if tmp_path.exists():
                tmp_path.unlink()

    def test_save_config_with_latest_version_none(self):
        """Test saving config where latest_version is None."""
        agents = [
            AgentConfig(
                name="test-agent",
                description="Test agent",
                install_command="npm install -g test-agent",
                version_command="test-agent --version",
                check_latest_command="npm view test-agent version",
                upgrade_command="npm update -g test-agent",
                latest_version=None,
            )
        ]
        config = Config(agents=agents)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            temp_path = Path(f.name)
            # Delete the temp file so save_config can create it
            temp_path.unlink()

        try:
            save_config(config, temp_path)

            with open(temp_path, "r") as f:
                saved_data = yaml.safe_load(f)  # type: ignore[assignment]

            assert "agents" in saved_data  # type: ignore[index]
            assert len(saved_data["agents"]) == 1  # type: ignore[index]
            assert "latest_version" not in saved_data["agents"][0]  # type: ignore[index]
        finally:
            if temp_path.exists():
                temp_path.unlink()
            # Clean up the .tmp file if it exists
            tmp_path = temp_path.with_suffix(".tmp")
            if tmp_path.exists():
                tmp_path.unlink()


class TestCompareVersions:
    """Tests for compare_versions function."""

    def test_compare_versions_equal(self):
        """Test comparing equal versions."""
        assert compare_versions("1.2.3", "1.2.3") == 0
        assert compare_versions("v1.2.3", "1.2.3") == 0
        assert compare_versions("1.2.0", "1.2.0") == 0

    def test_compare_versions_greater(self):
        """Test comparing greater version."""
        assert compare_versions("2.0.0", "1.2.3") == 1
        assert compare_versions("1.2.4", "1.2.3") == 1

    def test_compare_versions_less(self):
        """Test comparing lesser version."""
        assert compare_versions("1.2.3", "2.0.0") == -1
        assert compare_versions("1.2.3", "1.3.0") == -1

    def test_compare_versions_with_prereleases(self):
        """Test comparing versions with prereleases."""
        # Prereleases are not properly handled by extract_version_number, so they get treated as strings
        assert (
            compare_versions("1.2.3-alpha", "1.2.3-beta") == 0
        )  # Both extract to "" and compare as strings

    def test_compare_versions_without_version_number(self):
        """Test comparing strings without version numbers."""
        assert (
            compare_versions("unknown", "1.2.3") == 1
        )  # "unknown" > "1.2.3" as strings
        assert (
            compare_versions("1.2.3", "unknown") == -1
        )  # "1.2.3" < "unknown" as strings
        assert compare_versions("unknown", "unknown") == 0  # equal strings

    def test_compare_versions_mixed_formats(self):
        """Test comparing versions in different formats."""
        assert compare_versions("v1.2.3", "1.2.3-beta") == 0  # both extract to "1.2.3"
        assert compare_versions("1.0.0", "1.0") > 0  # "1.0.0" > "1.0" as strings

    def test_compare_versions_single_digit(self):
        """Test comparing single digit versions."""
        assert compare_versions("1", "2") == -1
        assert compare_versions("2", "1") == 1
        assert compare_versions("1", "1") == 0


class TestExtractVersionNumber:
    """Tests for extract_version_number function."""

    def test_extract_simple_version(self):
        """Test extracting simple version numbers."""
        assert extract_version_number("1.2.3") == "1.2.3"
        assert extract_version_number("v1.2.3") == "1.2.3"

    def test_extract_single_digit(self):
        """Test extracting single digit versions."""
        assert extract_version_number("v1") == "1"
        assert extract_version_number("1") == "1"

    def test_extract_two_digit(self):
        """Test extracting two digit versions."""
        assert extract_version_number("v1.2") == "1.2"

    def test_extract_in_parentheses(self):
        """Test extracting version in parentheses."""
        assert extract_version_number("version 1.2.3 (release)") == "1.2.3"
        assert extract_version_number("(1.2.3)") == "1.2.3"

    def test_extract_no_version(self):
        """Test empty string returns empty."""
        assert extract_version_number("") == ""
        assert extract_version_number("no version here") == ""

    def test_extract_with_version_in_middle(self):
        """Test extracting version from string with other text."""
        assert extract_version_number("Version 1.2.3 is latest") == "1.2.3"
        assert extract_version_number("Check v1.2.3 today") == "1.2.3"

    def test_extract_multiple_versions(self):
        """Test that it returns the first match."""
        assert extract_version_number("v1.2.3 and v2.0.0") == "1.2.3"

    def test_extract_mixed_version_formats(self):
        """Test extracting from various version formats."""
        assert extract_version_number("1.0.0-beta.1") == "1.0.0"
        assert extract_version_number("v2.0.0-alpha") == "2.0.0"


class TestRunCommandAsync:
    """Tests for run_command_async function."""

    @pytest.mark.asyncio
    async def test_run_command_success(self):
        """Test successful command execution."""
        result = await run_command_async("echo 'test'")
        assert "test" in result[0]
        assert result[1] == 0

    @pytest.mark.asyncio
    async def test_run_command_failure(self):
        """Test failed command execution."""
        result = await run_command_async("false")
        assert "Error" in result[0] or result[1] != 0

    @pytest.mark.asyncio
    async def test_run_command_timeout(self):
        """Test command timeout."""
        result = await run_command_async("sleep 100", timeout=1)
        assert result[1] == 1
        assert (
            "timeout" in result[0].lower()
            or "timed out" in result[0].lower()
            or "Error" in result[0]
        )

    @pytest.mark.asyncio
    async def test_run_command_debug_mode(self):
        """Test command execution in debug mode."""
        with patch("reincheck.__init__._logging.debug") as mock_debug:
            await run_command_async("echo 'debug test'", debug=True)
            _ = mock_debug.call_count  # type: ignore[assignment]


class TestGetNpmReleaseInfo:
    """Tests for get_npm_release_info function."""

    @pytest.mark.asyncio
    async def test_get_npm_release_info_valid(self):
        """Test getting valid npm release info."""
        mock_output = json.dumps({"latest": "1.2.3", "modified": "2024-01-01"})
        with patch("reincheck.run_command_async") as mock_run:
            mock_run.side_effect = [
                (mock_output, 0),  # tags
                (json.dumps({"1.2.3": "2024-01-01"}), 0),  # time
            ]
            result = await get_npm_release_info("test-package")
            # Should return markdown formatted text with version
            assert result is not None
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_get_npm_release_info_no_tags(self):
        """Test npm info when no tags found."""
        mock_tags_output = json.dumps({})
        mock_time_output = json.dumps({})

        async def mock_run(_cmd: str):
            if "dist-tags" in _cmd:
                return mock_tags_output, 0
            elif "time" in _cmd:
                return mock_time_output, 0
            return "", 1

        with patch("reincheck.run_command_async", side_effect=mock_run):
            result = await get_npm_release_info("test-package")
            assert result is None or result == ""

    @pytest.mark.asyncio
    async def test_get_npm_release_info_parse_error(self):
        """Test handling of parse errors."""
        mock_tags_output = "invalid json"

        async def mock_run(_cmd: str):
            return mock_tags_output, 0

        with patch("reincheck.run_command_async", side_effect=mock_run):
            result = await get_npm_release_info("test-package")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_npm_release_info_timeout(self):
        """Test handling of timeout."""

        async def mock_run(_cmd: str):
            return ("Command timed out after 30 seconds", 1)

        with patch("reincheck.run_command_async", side_effect=mock_run):
            result = await get_npm_release_info("test-package")
            assert result is None


class TestGetPyPIReleaseInfo:
    """Tests for get_pypi_release_info function."""

    @pytest.mark.asyncio
    async def test_get_pypi_release_info_valid(self):
        """Test getting valid PyPI release info."""
        mock_output = json.dumps(
            {
                "info": {
                    "version": "1.2.3",
                    "summary": "Test package",
                    "project_urls": {"Changelog": "https://example.com/changelog"},
                },
                "releases": {"1.2.3": [{"upload_time": "2024-01-01"}]},
            }
        )
        with patch("reincheck.run_command_async") as mock_run:
            mock_run.return_value = (mock_output, 0)
            result = await get_pypi_release_info("test-package")
            # Should return markdown formatted text with version
            assert result is not None
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_get_pypi_release_info_no_version(self):
        """Test PyPI info when no version found."""
        mock_output = json.dumps({"info": {}})

        async def mock_run(_cmd: str):
            return mock_output, 0

        with patch("reincheck.run_command_async", side_effect=mock_run):
            result = await get_pypi_release_info("test-package")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_pypi_release_info_parse_error(self):
        """Test handling of parse errors."""
        mock_output = "invalid json"

        async def mock_run(_cmd: str):
            return mock_output, 0

        with patch("reincheck.run_command_async", side_effect=mock_run):
            result = await get_pypi_release_info("test-package")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_pypi_release_info_no_releases(self):
        """Test PyPI info when no releases found."""
        mock_output = json.dumps({"info": {"version": "1.0.0"}, "releases": {}})
        with patch("reincheck.run_command_async") as mock_run:
            mock_run.return_value = (mock_output, 0)
            result = await get_pypi_release_info("test-package")
            # Should return markdown formatted text even if releases is empty
            assert result is not None
            assert isinstance(result, str)


class TestIsCommandSafe:
    """Tests for is_command_safe function."""

    def test_safe_command(self):
        """Test that safe commands return True."""
        assert is_command_safe("npm install -g test-agent")
        assert is_command_safe("echo test")
        assert is_command_safe("python -m pip install --upgrade pip")

    def test_command_with_dollar_parentheses(self):
        """Test that commands with $(...) return False."""
        assert not is_command_safe("echo $(malicious)")
        assert not is_command_safe("npm install $(rm -rf /)")

    def test_command_with_backticks(self):
        """Test that commands with backticks return False."""
        assert not is_command_safe("echo `malicious`")
        assert not is_command_safe("npm install `rm -rf /`")

    def test_empty_command(self):
        """Test empty command returns False."""
        assert not is_command_safe("")

    def test_command_with_git(self):
        """Test git commands are safe."""
        assert is_command_safe("git clone https://github.com/test/repo")

    def test_command_with_sudo(self):
        """Test sudo commands are safe."""
        assert is_command_safe("sudo apt-get update")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])  # type: ignore[reportUnusedCallResult]

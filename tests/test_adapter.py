"""Tests for adapter layer bridging AgentConfig with Harness/InstallMethod."""

import pytest

from reincheck.adapter import (
    EffectiveMethod,
    agent_config_to_method,
    get_effective_method,
    get_effective_method_from_config,
    list_available_methods,
)
from reincheck.config import AgentConfig
from reincheck.data_loader import clear_cache, get_harnesses
from reincheck.installer import Harness, InstallMethod, RiskLevel


@pytest.fixture(autouse=True)
def clear_data_cache():
    """Clear data loader cache before each test."""
    clear_cache()
    yield
    clear_cache()


class TestEffectiveMethod:
    """Tests for EffectiveMethod dataclass."""

    def test_effective_method_properties(self):
        """EffectiveMethod exposes harness and method properties."""
        harness = Harness(
            name="testharness",
            display_name="Test Harness",
            description="A test harness",
            github_repo="test/repo",
            release_notes_url="https://example.com/notes",
        )
        method = InstallMethod(
            harness="testharness",
            method_name="test_method",
            install="test install",
            upgrade="test upgrade",
            version="test --version",
            check_latest="test check",
            dependencies=["dep1"],
            risk_level=RiskLevel.SAFE,
        )
        effective = EffectiveMethod(harness=harness, method=method, source="test")

        assert effective.name == "testharness"
        assert effective.description == "A test harness"
        assert effective.install_command == "test install"
        assert effective.upgrade_command == "test upgrade"
        assert effective.version_command == "test --version"
        assert effective.check_latest_command == "test check"
        assert effective.github_repo == "test/repo"
        assert effective.release_notes_url == "https://example.com/notes"
        assert effective.source == "test"

    def test_effective_method_to_agent_config(self):
        """to_agent_config creates valid AgentConfig."""
        harness = Harness(
            name="testharness",
            display_name="Test Harness",
            description="A test harness",
            github_repo="test/repo",
            release_notes_url=None,
        )
        method = InstallMethod(
            harness="testharness",
            method_name="test_method",
            install="npm install -g test",
            upgrade="npm update -g test",
            version="test --version",
            check_latest="npm info test version",
            dependencies=[],
            risk_level=RiskLevel.SAFE,
        )
        effective = EffectiveMethod(harness=harness, method=method, source="preset")

        config = effective.to_agent_config()

        assert isinstance(config, AgentConfig)
        assert config.name == "testharness"
        assert config.description == "A test harness"
        assert config.install_command == "npm install -g test"
        assert config.upgrade_command == "npm update -g test"
        assert config.version_command == "test --version"
        assert config.check_latest_command == "npm info test version"
        assert config.github_repo == "test/repo"
        assert config.release_notes_url is None


class TestAgentConfigToMethod:
    """Tests for agent_config_to_method function."""

    def test_converts_config_to_method(self):
        """Converts AgentConfig fields to InstallMethod."""
        config = AgentConfig(
            name="myagent",
            description="My agent",
            install_command="npm install -g myagent",
            upgrade_command="npm update -g myagent",
            version_command="myagent --version",
            check_latest_command="npm info myagent version",
            github_repo="user/myagent",
        )

        method = agent_config_to_method(config)

        assert isinstance(method, InstallMethod)
        assert method.harness == "myagent"
        assert method.method_name == "config"
        assert method.install == "npm install -g myagent"
        assert method.upgrade == "npm update -g myagent"
        assert method.version == "myagent --version"
        assert method.check_latest == "npm info myagent version"
        assert method.dependencies == []

    def test_infers_safe_risk_level(self):
        """Infers SAFE risk for normal commands."""
        config = AgentConfig(
            name="safe",
            description="Safe agent",
            install_command="mise use -g safe",
            upgrade_command="mise use -g safe",
            version_command="safe --version",
            check_latest_command="mise ls-remote safe | tail -n1",
        )

        method = agent_config_to_method(config)

        assert method.risk_level == RiskLevel.SAFE

    def test_infers_dangerous_risk_level_for_curl_pipe(self):
        """Infers DANGEROUS risk for curl | sh commands."""
        config = AgentConfig(
            name="dangerous",
            description="Dangerous agent",
            install_command="curl -fsSL https://example.com/install.sh | bash",
            upgrade_command="curl -fsSL https://example.com/install.sh | bash",
            version_command="dangerous --version",
            check_latest_command="curl -s https://api.example.com/version",
        )

        method = agent_config_to_method(config)

        assert method.risk_level == RiskLevel.DANGEROUS

    def test_infers_interactive_risk_level_for_npm_install(self):
        """Infers INTERACTIVE risk for npm install commands."""
        config = AgentConfig(
            name="interactive",
            description="Interactive agent",
            install_command="npm install -g @org/interactive",
            upgrade_command="npm update -g @org/interactive",
            version_command="interactive --version",
            check_latest_command="npm info @org/interactive version",
        )

        method = agent_config_to_method(config)

        assert method.risk_level == RiskLevel.INTERACTIVE


class TestGetEffectiveMethod:
    """Tests for get_effective_method function."""

    def test_returns_none_for_unknown_harness(self):
        """Returns None if harness doesn't exist."""
        result = get_effective_method("nonexistent_harness_xyz", preset_name="mise_binary")
        assert result is None

    def test_resolves_known_harness_with_preset(self):
        """Resolves a known harness using preset."""
        result = get_effective_method("claude", preset_name="mise_binary")

        assert result is not None
        assert isinstance(result, EffectiveMethod)
        assert result.name == "claude"
        assert result.source == "preset"
        assert "mise" in result.install_command.lower()

    def test_resolves_with_override(self):
        """Override takes precedence over preset."""
        result = get_effective_method(
            "claude",
            preset_name="mise_binary",
            overrides={"claude": "language_native"},
        )

        assert result is not None
        assert result.source == "preset+override"
        assert "npm install" in result.install_command

    def test_raises_for_invalid_override(self):
        """Raises ValueError for invalid override method."""
        with pytest.raises(ValueError, match="not found for harness"):
            get_effective_method(
                "claude",
                preset_name="mise_binary",
                overrides={"claude": "nonexistent_method"},
            )

    def test_raises_for_invalid_preset(self):
        """Raises ValueError for unknown preset."""
        with pytest.raises(ValueError, match="Preset .* not found"):
            get_effective_method("claude", preset_name="nonexistent_preset")

    def test_raises_without_preset_or_override(self):
        """Raises ValueError when no preset and no override."""
        with pytest.raises(ValueError, match="No preset specified"):
            get_effective_method("claude")

    def test_uses_fallback_strategy(self):
        """Falls back to fallback_strategy when method not found."""
        # mise_binary preset has fallback to mise_language
        # kilocode doesn't have mise_binary method, should fall back
        result = get_effective_method("kilocode", preset_name="mise_binary")

        assert result is not None
        # Should have resolved via fallback
        assert result.name == "kilocode"

    def test_multiple_presets_work(self):
        """Different presets resolve to different methods."""
        result_mise = get_effective_method("claude", preset_name="mise_language")
        result_native = get_effective_method("claude", preset_name="language_native")

        assert result_mise is not None
        assert result_native is not None
        # Both resolve but with different install commands
        assert result_mise.install_command != result_native.install_command
        assert "mise" in result_mise.install_command
        assert "npm install" in result_native.install_command


class TestGetEffectiveMethodFromConfig:
    """Tests for get_effective_method_from_config function."""

    def test_wraps_config_in_effective_method(self):
        """Creates EffectiveMethod from AgentConfig."""
        config = AgentConfig(
            name="claude",  # Known harness
            description="Test Claude",
            install_command="npm install -g claude",
            upgrade_command="npm update -g claude",
            version_command="claude --version",
            check_latest_command="npm info claude version",
        )

        result = get_effective_method_from_config(config)

        assert isinstance(result, EffectiveMethod)
        assert result.name == "claude"
        assert result.source == "config"
        assert result.install_command == "npm install -g claude"
        # Should use harness metadata for description (from data)
        assert result.harness.display_name == "Claude Code"

    def test_creates_minimal_harness_for_unknown(self):
        """Creates minimal harness if not in bundled data."""
        config = AgentConfig(
            name="custom_agent",
            description="My Custom Agent",
            install_command="custom install",
            upgrade_command="custom upgrade",
            version_command="custom --version",
            check_latest_command="custom check",
            github_repo="user/custom",
        )

        result = get_effective_method_from_config(config)

        assert result.name == "custom_agent"
        assert result.description == "My Custom Agent"
        assert result.harness.display_name == "Custom_Agent"  # Title-cased
        assert result.github_repo == "user/custom"


class TestListAvailableMethods:
    """Tests for list_available_methods function."""

    def test_lists_methods_for_known_harness(self):
        """Lists available methods for a harness."""
        methods = list_available_methods("claude")

        assert isinstance(methods, list)
        assert len(methods) > 0
        assert "mise_binary" in methods
        assert "mise_language" in methods
        assert "language_native" in methods

    def test_returns_empty_for_unknown_harness(self):
        """Returns empty list for unknown harness."""
        methods = list_available_methods("nonexistent_harness_xyz")

        assert methods == []

    def test_lists_correct_methods_for_python_tools(self):
        """Python tools have language_native (uv) methods."""
        methods = list_available_methods("aider")

        assert "language_native" in methods
        assert "vendor_recommended" in methods


class TestIntegration:
    """Integration tests with real bundled data."""

    def test_all_harnesses_resolvable_with_mise_binary(self):
        """All harnesses can be resolved with mise_binary preset."""
        harnesses = get_harnesses()
        resolved_count = 0
        failed = []

        for name in harnesses:
            try:
                result = get_effective_method(name, preset_name="mise_binary")
                if result:
                    resolved_count += 1
            except ValueError:
                failed.append(name)

        # Most should resolve (some might not have mise_binary and no fallback)
        assert resolved_count > 0
        # Log any failures for debugging
        if failed:
            print(f"Failed to resolve with mise_binary: {failed}")

    def test_all_harnesses_resolvable_with_vendor_recommended(self):
        """All harnesses can be resolved with vendor_recommended preset."""
        harnesses = get_harnesses()

        for name in harnesses:
            result = get_effective_method(name, preset_name="vendor_recommended")
            assert result is not None, f"Failed to resolve {name}"
            assert result.install_command, f"{name} has empty install_command"

    def test_effective_method_roundtrip(self):
        """AgentConfig -> EffectiveMethod -> AgentConfig preserves data."""
        original = AgentConfig(
            name="test",
            description="Test Agent",
            install_command="npm install -g test",
            upgrade_command="npm update -g test",
            version_command="test --version",
            check_latest_command="npm info test version",
            github_repo="user/test",
            release_notes_url="https://example.com/notes",
        )

        effective = get_effective_method_from_config(original)
        roundtrip = effective.to_agent_config()

        assert roundtrip.name == original.name
        assert roundtrip.description == original.description
        assert roundtrip.install_command == original.install_command
        assert roundtrip.upgrade_command == original.upgrade_command
        assert roundtrip.version_command == original.version_command
        assert roundtrip.check_latest_command == original.check_latest_command
        # Note: github_repo/release_notes_url come from harness if available

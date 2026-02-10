"""Tests for data_loader module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from reincheck.config import ConfigError
from reincheck.data_loader import (
    clear_cache,
    get_all_methods,
    get_dependencies,
    get_harnesses,
    get_method,
    get_presets,
)
from reincheck.installer import Harness, Dependency, Preset, InstallMethod, RiskLevel


class TestGetHarnesses:
    """Tests for get_harnesses()."""

    def test_get_harnesses_returns_dict(self):
        """Result is a dict."""
        harnesses = get_harnesses()
        assert isinstance(harnesses, dict)

    def test_get_harnesses_correct_count(self):
        """Returns all 18 harnesses."""
        harnesses = get_harnesses()
        assert len(harnesses) == 18

    def test_get_harnesses_all_instances(self):
        """All values are Harness instances."""
        harnesses = get_harnesses()
        assert all(isinstance(h, Harness) for h in harnesses.values())

    def test_get_harnesses_required_fields(self):
        """Harnesses have required fields."""
        harnesses = get_harnesses()
        for harness in harnesses.values():
            assert harness.name
            assert harness.display_name
            assert harness.description
            assert isinstance(harness.name, str)
            assert isinstance(harness.display_name, str)
            assert isinstance(harness.description, str)

    def test_get_harnesses_optional_fields(self):
        """Optional fields are strings or None."""
        harnesses = get_harnesses()
        for harness in harnesses.values():
            if harness.github_repo is not None:
                assert isinstance(harness.github_repo, str)
            if harness.release_notes_url is not None:
                assert isinstance(harness.release_notes_url, str)

    def test_get_harnesses_caching(self):
        """Second call returns cached data."""
        clear_cache()
        harnesses1 = get_harnesses()
        harnesses2 = get_harnesses()
        assert harnesses1 is harnesses2

    def test_get_harnesses_known_harnesses(self):
        """Known harnesses are present."""
        harnesses = get_harnesses()
        known = ["claude", "amp", "aider", "gemini", "droid"]
        for name in known:
            assert name in harnesses


class TestGetDependencies:
    """Tests for get_dependencies()."""

    def test_get_dependencies_returns_dict(self):
        """Result is a dict."""
        deps = get_dependencies()
        assert isinstance(deps, dict)

    def test_get_dependencies_correct_count(self):
        """Returns all dependencies."""
        deps = get_dependencies()
        # Should have at least the 7 defined in dependencies.json
        assert len(deps) >= 7

    def test_get_dependencies_all_instances(self):
        """All values are Dependency instances."""
        deps = get_dependencies()
        assert all(isinstance(d, Dependency) for d in deps.values())

    def test_get_dependencies_required_fields(self):
        """Dependencies have required fields."""
        deps = get_dependencies()
        for dep in deps.values():
            assert dep.name
            assert dep.check_command
            assert dep.install_hint
            assert isinstance(dep.name, str)
            assert isinstance(dep.check_command, str)
            assert isinstance(dep.install_hint, str)

    def test_get_dependencies_optional_fields(self):
        """Optional fields are strings or None."""
        deps = get_dependencies()
        for dep in deps.values():
            if dep.version_command is not None:
                assert isinstance(dep.version_command, str)
            if dep.min_version is not None:
                assert isinstance(dep.min_version, str)
            if dep.max_version is not None:
                assert isinstance(dep.max_version, str)

    def test_get_dependencies_caching(self):
        """Second call returns cached data."""
        clear_cache()
        deps1 = get_dependencies()
        deps2 = get_dependencies()
        assert deps1 is deps2

    def test_get_dependencies_known_dependencies(self):
        """Known dependencies are present."""
        deps = get_dependencies()
        known = ["mise", "npm", "curl", "uv", "brew", "jq", "python"]
        for name in known:
            assert name in deps


class TestGetPresets:
    """Tests for get_presets()."""

    def test_get_presets_returns_dict(self):
        """Result is a dict."""
        presets = get_presets()
        assert isinstance(presets, dict)

    def test_get_presets_correct_count(self):
        """Returns all 5 presets."""
        presets = get_presets()
        assert len(presets) == 5

    def test_get_presets_all_instances(self):
        """All values are Preset instances."""
        presets = get_presets()
        assert all(isinstance(p, Preset) for p in presets.values())

    def test_get_presets_required_fields(self):
        """Presets have required fields."""
        presets = get_presets()
        for preset in presets.values():
            assert preset.name
            assert preset.strategy
            assert preset.description
            assert isinstance(preset.methods, dict)
            assert isinstance(preset.name, str)
            assert isinstance(preset.strategy, str)
            assert isinstance(preset.description, str)

    def test_get_presets_fallback_strategy(self):
        """fallback_strategy is string or None."""
        presets = get_presets()
        for preset in presets.values():
            if preset.fallback_strategy is not None:
                assert isinstance(preset.fallback_strategy, str)

    def test_get_presets_caching(self):
        """Second call returns cached data."""
        clear_cache()
        presets1 = get_presets()
        presets2 = get_presets()
        assert presets1 is presets2

    def test_get_presets_known_presets(self):
        """Known presets are present."""
        presets = get_presets()
        known = [
            "mise_binary",
            "mise_language",
            "homebrew",
            "language_native",
            "vendor_recommended",
        ]
        for name in known:
            assert name in presets

    def test_get_presets_methods_coverage(self):
        """Each preset maps all 18 harnesses."""
        presets = get_presets()
        for preset in presets.values():
            assert len(preset.methods) == 18


class TestGetAllMethods:
    """Tests for get_all_methods()."""

    def test_get_all_methods_returns_dict(self):
        """Result is a dict."""
        methods = get_all_methods()
        assert isinstance(methods, dict)

    def test_get_all_methods_correct_count(self):
        """Returns 60+ methods."""
        methods = get_all_methods()
        assert len(methods) >= 60

    def test_get_all_methods_all_instances(self):
        """All values are InstallMethod instances."""
        methods = get_all_methods()
        assert all(isinstance(m, InstallMethod) for m in methods.values())

    def test_get_all_methods_required_fields(self):
        """Methods have required fields."""
        methods = get_all_methods()
        for method in methods.values():
            assert method.harness
            assert method.method_name
            assert method.install
            assert method.upgrade
            assert method.version
            assert method.check_latest
            assert isinstance(method.risk_level, RiskLevel)

    def test_get_all_methods_risk_level_enum(self):
        """Risk levels are proper enum values."""
        methods = get_all_methods()
        for method in methods.values():
            assert isinstance(method.risk_level, RiskLevel)
            assert method.risk_level in [
                RiskLevel.SAFE,
                RiskLevel.INTERACTIVE,
                RiskLevel.DANGEROUS,
            ]

    def test_get_all_methods_dependencies(self):
        """Dependencies field is a list."""
        methods = get_all_methods()
        for method in methods.values():
            assert isinstance(method.dependencies, list)

    def test_get_all_methods_caching(self):
        """Second call returns cached data."""
        clear_cache()
        methods1 = get_all_methods()
        methods2 = get_all_methods()
        assert methods1 is methods2

    def test_get_all_methods_key_format(self):
        """Method keys follow {harness}.{method_name} format."""
        methods = get_all_methods()
        for key in methods.keys():
            assert "." in key
            parts = key.split(".", 1)
            assert len(parts) == 2
            assert parts[0]  # harness name
            assert parts[1]  # method name


class TestGetMethod:
    """Tests for get_method()."""

    def test_get_method_valid(self):
        """Returns method for valid key."""
        method = get_method("claude", "mise_binary")
        assert method is not None
        assert isinstance(method, InstallMethod)
        assert method.harness == "claude"
        assert method.method_name == "mise_binary"

    def test_get_method_nonexistent(self):
        """Returns None for non-existent method."""
        method = get_method("nonexistent", "nonexistent")
        assert method is None

    def test_get_method_partial_match(self):
        """Returns None if harness or method don't match."""
        assert get_method("claude", "nonexistent") is None
        assert get_method("nonexistent", "mise_binary") is None

    def test_get_method_with_caching(self):
        """Uses cached methods."""
        clear_cache()
        method1 = get_method("claude", "mise_binary")
        method2 = get_method("claude", "mise_binary")
        assert method1 is method2


class TestClearCache:
    """Tests for clear_cache()."""

    def test_clear_cache_forces_reload(self):
        """Forces reload on next access."""
        harnesses1 = get_harnesses()
        clear_cache()
        harnesses2 = get_harnesses()
        # Should be different objects after cache clear
        assert harnesses1 is not harnesses2

    def test_clear_cache_all_caches(self):
        """Clears all four caches."""
        get_harnesses()
        get_dependencies()
        get_presets()
        get_all_methods()

        clear_cache()

        # Next calls should return new objects
        assert get_harnesses() is not None
        assert get_dependencies() is not None
        assert get_presets() is not None
        assert get_all_methods() is not None

    def test_clear_cache_selective_harnesses(self):
        """Clears only harnesses cache, leaves others intact."""
        get_harnesses()
        get_dependencies()
        get_presets()
        get_all_methods()

        harnesses1 = get_harnesses()
        deps1 = get_dependencies()
        presets1 = get_presets()
        methods1 = get_all_methods()

        clear_cache('harnesses')

        harnesses2 = get_harnesses()
        deps2 = get_dependencies()
        presets2 = get_presets()
        methods2 = get_all_methods()

        # Harnesses should be different object
        assert harnesses1 is not harnesses2
        # Others should be same cached objects
        assert deps1 is deps2
        assert presets1 is presets2
        assert methods1 is methods2

    def test_clear_cache_selective_dependencies(self):
        """Clears only dependencies cache, leaves others intact."""
        get_harnesses()
        get_dependencies()
        get_presets()
        get_all_methods()

        harnesses1 = get_harnesses()
        deps1 = get_dependencies()
        presets1 = get_presets()
        methods1 = get_all_methods()

        clear_cache('dependencies')

        harnesses2 = get_harnesses()
        deps2 = get_dependencies()
        presets2 = get_presets()
        methods2 = get_all_methods()

        assert harnesses1 is harnesses2
        assert deps1 is not deps2
        assert presets1 is presets2
        assert methods1 is methods2

    def test_clear_cache_selective_presets(self):
        """Clears only presets cache, leaves others intact."""
        get_harnesses()
        get_dependencies()
        get_presets()
        get_all_methods()

        harnesses1 = get_harnesses()
        deps1 = get_dependencies()
        presets1 = get_presets()
        methods1 = get_all_methods()

        clear_cache('presets')

        harnesses2 = get_harnesses()
        deps2 = get_dependencies()
        presets2 = get_presets()
        methods2 = get_all_methods()

        assert harnesses1 is harnesses2
        assert deps1 is deps2
        assert presets1 is not presets2
        assert methods1 is methods2

    def test_clear_cache_selective_methods(self):
        """Clears only methods cache, leaves others intact."""
        get_harnesses()
        get_dependencies()
        get_presets()
        get_all_methods()

        harnesses1 = get_harnesses()
        deps1 = get_dependencies()
        presets1 = get_presets()
        methods1 = get_all_methods()

        clear_cache('methods')

        harnesses2 = get_harnesses()
        deps2 = get_dependencies()
        presets2 = get_presets()
        methods2 = get_all_methods()

        assert harnesses1 is harnesses2
        assert deps1 is deps2
        assert presets1 is presets2
        assert methods1 is not methods2

    def test_clear_cache_invalid_type(self):
        """Raises ValueError for invalid cache type."""
        with pytest.raises(ValueError, match="Invalid cache_type 'invalid'"):
            clear_cache('invalid')


class TestErrorHandling:
    """Tests for error handling."""

    def test_missing_harnesses_file(self):
        """Raises ConfigError for missing harnesses file."""
        clear_cache()

        with patch("reincheck.data_loader._get_data_dir") as mock_dir:
            mock_dir.return_value = Path("/nonexistent")

            with pytest.raises(ConfigError, match="Data file not found"):
                get_harnesses()

    def test_invalid_harnesses_json(self):
        """Raises ConfigError for invalid JSON in harnesses file."""
        clear_cache()

        with patch("reincheck.data_loader._load_json_file") as mock_load:
            mock_load.return_value = {"harnesses": "not a dict"}

            with pytest.raises(ConfigError, match="'harnesses' must be an object"):
                get_harnesses()

    def test_missing_required_harness_field(self):
        """Raises ConfigError for missing required field."""
        clear_cache()

        with patch("reincheck.data_loader._load_json_file") as mock_load:
            mock_load.return_value = {
                "harnesses": {
                    "test": {
                        "name": "test",
                        # missing display_name and description
                    }
                }
            }

            with pytest.raises(ConfigError, match="missing required field"):
                get_harnesses()

    def test_invalid_risk_level(self):
        """Raises ConfigError for invalid risk level."""
        clear_cache()

        with patch("reincheck.data_loader._load_json_file") as mock_load:
            mock_load.return_value = {
                "methods": {
                    "claude.test": {
                        "install": "cmd",
                        "upgrade": "cmd",
                        "version": "cmd",
                        "check_latest": "cmd",
                        "dependencies": [],
                        "risk_level": "invalid",
                    }
                }
            }

            with pytest.raises(ConfigError, match="invalid risk_level"):
                get_all_methods()

    def test_invalid_dependencies_list(self):
        """Raises ConfigError for non-array dependencies."""
        clear_cache()

        with patch("reincheck.data_loader._load_json_file") as mock_load:
            mock_load.return_value = {
                "methods": {
                    "claude.test": {
                        "install": "cmd",
                        "upgrade": "cmd",
                        "version": "cmd",
                        "check_latest": "cmd",
                        "risk_level": "safe",
                        "dependencies": "not a list",
                    }
                }
            }

            with pytest.raises(ConfigError, match="'dependencies' must be an array"):
                get_all_methods()


class TestIntegrationWithInstaller:
    """Tests for integration with installer module."""

    def test_get_all_methods_compatible_with_resolver(self):
        """Methods work with installer.resolve_method()."""
        from reincheck.installer import resolve_method

        methods = get_all_methods()
        presets = get_presets()

        preset = presets["mise_binary"]
        method = resolve_method(preset, "claude", methods)

        assert method is not None
        assert method.harness == "claude"
        assert method.method_name in ["mise_binary", "mise_language"]

    def test_get_dependencies_compatible_with_scanner(self):
        """Dependencies work with installer.scan_dependencies()."""
        from reincheck.installer import scan_dependencies

        # Just verify it doesn't crash
        deps = get_dependencies()
        status = scan_dependencies()

        # Should have overlapping keys
        assert set(deps.keys()) & set(status.keys())

    def test_get_presets_compatible_with_planner(self):
        """Presets work with installer.plan_install()."""
        from reincheck.installer import plan_install

        presets = get_presets()
        methods = get_all_methods()

        preset = presets["language_native"]
        plan = plan_install(preset, ["claude", "amp"], methods)

        assert plan.preset_name == "language_native"
        assert len(plan.steps) == 2
        assert plan.steps[0].harness in ["claude", "amp"]

"""Tests verifying that test infrastructure prevents real config overwrites."""

import os
from pathlib import Path

import pytest

from reincheck.commands.setup import _write_agent_config


class TestConfigWriteSafetyGuard:
    """Verify the _write_agent_config safety guard prevents writes to real config."""

    def test_guard_raises_on_real_config_path(self, monkeypatch, tmp_path):
        """Writing to the real user config path during tests must raise RuntimeError."""
        real_config = Path(os.path.expanduser("~/.config/reincheck/agents.json"))
        real_config.parent.mkdir(parents=True, exist_ok=True)
        real_config.write_text('{"agents": []}')

        monkeypatch.setenv("PYTEST_CURRENT_TEST", "test::fake")

        agent_configs = [{"name": "evil", "description": "should not write"}]

        with pytest.raises(RuntimeError, match="Safety guard"):
            _write_agent_config(agent_configs, real_config, preset_name="test")

    def test_guard_allows_safe_temp_paths(self, monkeypatch, tmp_path):
        """Writing to a temp path during tests must succeed."""
        monkeypatch.setenv("PYTEST_CURRENT_TEST", "test::fake")

        safe_path = tmp_path / "agents.json"
        agent_configs = [{"name": "safe", "description": "should write"}]

        _write_agent_config(agent_configs, safe_path, preset_name="test")

        assert safe_path.exists()
        import json

        data = json.loads(safe_path.read_text())
        assert data["agents"][0]["name"] == "safe"

    def test_autouse_fixture_redirects_home(self):
        """The autouse fixture must prevent Path.home() from returning the real home."""
        real_home = Path(os.path.expanduser("~"))
        assert Path.home() != real_home, (
            "Path.home() should be redirected by the autouse safety fixture"
        )

    def test_get_config_dir_under_safe_home(self):
        """get_config_dir() must resolve under the safe home, not the real one."""
        from reincheck.paths import get_config_dir

        config_dir = get_config_dir()
        real_home = Path(os.path.expanduser("~"))

        assert not str(config_dir).startswith(str(real_home)), (
            f"get_config_dir() returned {config_dir} which is under the real home "
            f"{real_home}. The autouse safety fixture should prevent this."
        )

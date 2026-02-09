import pytest
from click.testing import CliRunner
from pathlib import Path
import json
from reincheck.commands import validate_pager, cli


@pytest.fixture
def runner():
    """Create a CliRunner for testing."""
    return CliRunner()


class TestValidatePager:
    """Test pager validation security."""

    def test_allowed_bare_commands(self):
        """Test that allowed bare commands pass validation."""
        allowed_pagers = ["cat", "less", "more", "bat", "most", "pager"]
        for pager in allowed_pagers:
            assert validate_pager(pager) == pager

    def test_allowed_absolute_paths(self):
        """Test that allowed commands with absolute paths pass validation."""
        assert validate_pager("/usr/bin/cat") == "/usr/bin/cat"
        assert validate_pager("/usr/local/bin/less") == "/usr/local/bin/less"
        assert validate_pager("/bin/cat") == "/bin/cat"

    def test_rejected_bare_commands(self):
        """Test that disallowed bare commands raise ValueError."""
        dangerous = ["rm", "sh", "bash", "evil", "curl", "wget", "nc"]
        for cmd in dangerous:
            with pytest.raises(ValueError, match="Unsafe pager"):
                _ = validate_pager(cmd)

    def test_rejected_absolute_paths(self):
        """Test that disallowed commands with absolute paths raise ValueError."""
        dangerous = ["/bin/rm", "/usr/bin/sh", "/bin/bash"]
        for cmd in dangerous:
            with pytest.raises(ValueError, match="Unsafe pager"):
                _ = validate_pager(cmd)

    def test_rejected_with_args(self):
        """Test that commands with arguments are rejected."""
        with pytest.raises(ValueError, match="Unsafe pager"):
            _ = validate_pager("less -R")
        with pytest.raises(ValueError, match="Unsafe pager"):
            _ = validate_pager("cat file.txt")

    def test_error_message_includes_allowed_list(self):
        """Test that error message includes list of allowed pagers."""
        with pytest.raises(ValueError) as exc_info:
            validate_pager("rm -rf /")

        error_msg = str(exc_info.value)
        assert "Unsafe pager" in error_msg
        assert "cat" in error_msg
        assert "less" in error_msg
        assert "more" in error_msg


class TestConfigFmt:
    """Test config fmt command."""

    def test_fmt_stdout_with_comments_and_trailing_commas(self, runner):
        """Test that fmt outputs strict JSON, stripping comments and trailing commas."""
        # Create a file with comments and trailing commas
        json_with_comments = """{
            // This is a comment
            "agents": [
                {
                    "name": "test-agent",
                    "description": "A test agent",
                    "install_command": "echo install",
                    "version_command": "echo 1.0.0",
                    "check_latest_command": "echo 1.0.0",
                    "upgrade_command": "echo upgrade",
                    "latest_version": "1.0.0", // trailing comma
                },
            ],
        }"""

        with runner.isolated_filesystem() as tmpdir:
            config_file = Path(tmpdir) / "test.json"
            config_file.write_text(json_with_comments)

            result = runner.invoke(cli, ["config", "fmt", str(config_file)])

            assert result.exit_code == 0
            # Comments should be stripped
            assert "//" not in result.output
            # Trailing commas should be removed
            assert '"1.0.0",' not in result.output
            assert '"1.0.0"' in result.output
            # Should be valid JSON
            assert '"agents"' in result.output
            assert '"name": "test-agent"' in result.output

    def test_fmt_write_flag(self):
        """Test that --write flag overwrites the file."""
        runner = CliRunner()

        json_with_comments = """{
            // Comment to be removed
            "agents": [],
        }"""

        with runner.isolated_filesystem() as tmpdir:
            config_file = Path(tmpdir) / "test.json"
            config_file.write_text(json_with_comments)

            result = runner.invoke(cli, ["config", "fmt", str(config_file), "--write"])

            assert result.exit_code == 0
            assert "Formatted" in result.output

            # File should now contain strict JSON
            content = config_file.read_text()
            assert "//" not in content
            assert '"agents": []' in content

    def test_fmt_file_not_found(self):
        """Test error handling when file doesn't exist."""
        runner = CliRunner()

        result = runner.invoke(cli, ["config", "fmt", "/nonexistent/path/config.json"])

        assert result.exit_code == 1
        assert "File not found" in result.output

    def test_fmt_invalid_json(self):
        """Test error handling for invalid JSON."""
        runner = CliRunner()

        with runner.isolated_filesystem() as tmpdir:
            config_file = Path(tmpdir) / "bad.json"
            config_file.write_text('{"invalid json')

            result = runner.invoke(cli, ["config", "fmt", str(config_file)])

            assert result.exit_code == 1
            assert "Config syntax error" in result.output or "Error" in result.output

    def test_fmt_preserves_key_order(self):
        """Test that fmt preserves key order (sort_keys=False)."""
        runner = CliRunner()

        json_ordered = """{
            "z_last": 1,
            "a_first": 2,
            "m_middle": 3
        }"""

        with runner.isolated_filesystem() as tmpdir:
            config_file = Path(tmpdir) / "test.json"
            config_file.write_text(json_ordered)

            result = runner.invoke(cli, ["config", "fmt", str(config_file)])

            assert result.exit_code == 0
            # Check that z_last comes before a_first in output (preserves input order)
            z_pos = result.output.find('"z_last"')
            a_pos = result.output.find('"a_first"')
            assert z_pos < a_pos, "Key order should be preserved"

    def test_fmt_write_adds_trailing_newline(self):
        """Test that --write adds trailing newline."""
        runner = CliRunner()

        json_content = '{"agents": []}'

        with runner.isolated_filesystem() as tmpdir:
            config_file = Path(tmpdir) / "test.json"
            config_file.write_text(json_content)

            result = runner.invoke(cli, ["config", "fmt", str(config_file), "--write"])

            assert result.exit_code == 0
            content = config_file.read_text()
            # File should end with newline
            assert content.endswith("\n"), "File should end with trailing newline"

    def test_fmt_default_path_not_found(self):
        """Test that default path shows error when file doesn't exist."""
        runner = CliRunner()

        # Override HOME to a temp directory so default path doesn't exist
        with runner.isolated_filesystem() as tmpdir:
            env = {"HOME": str(tmpdir)}
            result = runner.invoke(cli, ["config", "fmt"], env=env)

            assert result.exit_code == 1
            assert ".config/reincheck/agents.json" in result.output

    def test_fmt_default_path_success(self):
        """Test that default path works when file exists."""
        runner = CliRunner()

        with runner.isolated_filesystem() as tmpdir:
            # Create the default config path
            config_dir = Path(tmpdir) / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"
            config_file.write_text('{"agents": []}')

            env = {"HOME": str(tmpdir)}
            result = runner.invoke(cli, ["config", "fmt"], env=env)

            assert result.exit_code == 0
            assert '"agents": []' in result.output


class TestConfigInit:
    """Test config init command."""

    def test_init_creates_config_from_defaults(self, runner, monkeypatch):
        """Test that init creates config from defaults."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            # Mock Path.home() to return tmpdir
            monkeypatch.setattr(Path, "home", lambda: tmpdir_path)

            result = runner.invoke(cli, ["config", "init"])
            assert result.exit_code == 0
            assert "initialized successfully" in result.output.lower()
            assert (tmpdir_path / ".config" / "reincheck" / "agents.json").exists()

    def test_init_force_overwrites_existing(self, runner, monkeypatch):
        """Test that --force overwrites existing config with backup."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"
            config_file.write_text('{"agents": []}')

            # Mock Path.home() to return tmpdir
            monkeypatch.setattr(Path, "home", lambda: tmpdir_path)

            result = runner.invoke(cli, ["config", "init", "--force"])
            assert result.exit_code == 0
            assert "backup created" in result.output.lower()
            assert (config_dir / "agents.json.bak").exists()
            assert config_file.exists()

    def test_init_existing_without_force(self, runner, monkeypatch):
        """Test that init without --force fails if config exists."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"
            config_file.write_text('{"agents": []}')

            # Mock Path.home() to return tmpdir
            monkeypatch.setattr(Path, "home", lambda: tmpdir_path)

            result = runner.invoke(cli, ["config", "init"])
            assert result.exit_code == 1
            assert "already exists" in result.output.lower()
            assert "--force" in result.output


class TestSetupCommand:
    """Test the setup command functionality."""

    def test_setup_list_presets(self, runner):
        """Test --list-presets flag."""
        result = runner.invoke(cli, ["setup", "--list-presets"])
        assert result.exit_code == 0
        assert "Available presets" in result.output
        assert "mise_binary" in result.output
        assert "homebrew" in result.output or "language_native" in result.output

    def test_setup_list_presets_standalone(self, runner):
        """Test that --list-presets cannot be combined with other options."""
        result = runner.invoke(
            cli, ["setup", "--list-presets", "--preset", "mise_binary"]
        )
        assert result.exit_code != 0
        assert "--list-presets cannot be used" in result.output

    def test_setup_requires_preset(self, runner):
        """Test that --preset is required unless --list-presets."""
        result = runner.invoke(cli, ["setup", "--harness", "claude"])
        assert result.exit_code != 0
        assert "--preset is required" in result.output

    def test_setup_apply_requires_harness(self, runner):
        """Test that --apply requires --harness."""
        result = runner.invoke(cli, ["setup", "--preset", "mise_binary", "--apply"])
        assert result.exit_code != 0
        assert "--apply requires --harness" in result.output

    def test_setup_custom_requires_override(self, runner):
        """Test that preset 'custom' requires at least one --override."""
        result = runner.invoke(cli, ["setup", "--preset", "custom"])
        assert result.exit_code != 0
        assert "preset 'custom' requires at least one --override" in result.output

    def test_setup_invalid_preset(self, runner):
        """Test error for invalid preset name."""
        result = runner.invoke(cli, ["setup", "--preset", "nonexistent"])
        assert result.exit_code == 3  # EXIT_PRESET_NOT_FOUND
        assert "not found" in result.output

    def test_setup_invalid_harness(self, runner):
        """Test error for invalid harness name."""
        result = runner.invoke(
            cli, ["setup", "--preset", "mise_binary", "--harness", "nonexistent"]
        )
        assert result.exit_code != 0
        assert "Unknown harness" in result.output

    def test_setup_dry_run(self, runner):
        """Test --dry-run flag shows preview without changes."""
        result = runner.invoke(cli, ["setup", "--preset", "mise_binary", "--dry-run"])
        assert result.exit_code == 0
        assert "[DRY-RUN]" in result.output
        assert "Would generate config" in result.output
        assert "No changes made" in result.output

    def test_setup_dry_run_with_harnesses(self, runner):
        """Test --dry-run with --harness shows installation plan."""
        result = runner.invoke(
            cli,
            [
                "setup",
                "--preset",
                "mise_binary",
                "--harness",
                "claude",
                "--harness",
                "cline",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "[DRY-RUN]" in result.output
        assert "Would generate config" in result.output
        assert "No changes made" in result.output
        assert "INSTALLATION PLAN PREVIEW" in result.output
        assert "claude" in result.output
        assert "cline" in result.output

    def test_setup_config_only(self, runner, monkeypatch):
        """Test generating config without installation."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)

            # Mock get_config_dir to return tmpdir
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            result = runner.invoke(cli, ["setup", "--preset", "mise_binary", "--yes"])
            assert result.exit_code == 0
            assert "Configured" in result.output
            assert "No harnesses selected for installation" in result.output

            # Verify config was created
            config_file = config_dir / "agents.json"
            assert config_file.exists()
            data = json.loads(config_file.read_text())
            assert "agents" in data
            assert len(data["agents"]) > 0

    def test_setup_custom_preset(self, runner, monkeypatch):
        """Test custom preset with overrides."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)

            # Mock get_config_dir to return tmpdir
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            result = runner.invoke(
                cli,
                [
                    "setup",
                    "--preset",
                    "custom",
                    "--override",
                    "claude=language_native",
                    "--yes",
                ],
            )
            assert result.exit_code == 0
            assert "Configured" in result.output

            # Verify config was created with only overridden harnesses
            config_file = config_dir / "agents.json"
            data = json.loads(config_file.read_text())
            assert "agents" in data
            agent_names = [a["name"] for a in data["agents"]]
            assert "claude" in agent_names
            # Should only have the overridden harness
            assert len(agent_names) == 1

    def test_setup_invalid_override_format(self, runner):
        """Test error for malformed --override argument."""
        result = runner.invoke(
            cli, ["setup", "--preset", "custom", "--override", "invalid"]
        )
        assert result.exit_code != 0
        assert "Invalid override format" in result.output

    def test_setup_dry_run_golden_output(self, runner):
        """Golden test: verify --dry-run output is stable for known preset."""
        result = runner.invoke(cli, ["setup", "--preset", "mise_binary", "--dry-run"])

        assert result.exit_code == 0

        # Verify expected sections
        assert "[DRY-RUN]" in result.output
        assert "Would generate config" in result.output
        assert "preset 'mise_binary'" in result.output
        assert "No changes made" in result.output

        # Verify it mentions the number of harnesses
        assert "Configuring" in result.output or "harness" in result.output.lower()

        # Verify determinism - run twice and compare
        result2 = runner.invoke(cli, ["setup", "--preset", "mise_binary", "--dry-run"])
        assert result2.exit_code == 0
        assert result.output == result2.output, "Dry-run output should be deterministic"

    def test_setup_dry_run_with_harnesses_golden_output(self, runner):
        """Golden test: verify --dry-run with --harness output stability."""
        result = runner.invoke(
            cli,
            [
                "setup",
                "--preset",
                "mise_binary",
                "--harness",
                "claude",
                "--harness",
                "cline",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0

        # Verify expected sections
        assert "[DRY-RUN]" in result.output
        assert "Would generate config" in result.output
        assert "INSTALLATION PLAN PREVIEW" in result.output
        assert "claude" in result.output
        assert "cline" in result.output

        # Verify determinism
        result2 = runner.invoke(
            cli,
            [
                "setup",
                "--preset",
                "mise_binary",
                "--harness",
                "claude",
                "--harness",
                "cline",
                "--dry-run",
            ],
        )
        assert result2.exit_code == 0
        assert result.output == result2.output, "Dry-run output should be deterministic"

    def test_setup_dry_run_custom_preset_golden_output(self, runner):
        """Golden test: verify --dry-run with custom preset is stable."""
        result = runner.invoke(
            cli,
            [
                "setup",
                "--preset",
                "custom",
                "--override",
                "claude=mise_binary",
                "--override",
                "cline=mise_binary",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0

        # Verify expected sections
        assert "[DRY-RUN]" in result.output
        assert "Would generate config" in result.output
        assert "preset 'custom'" in result.output
        assert "No changes made" in result.output

        # Verify only overridden harnesses are shown
        assert "claude" in result.output
        assert "cline" in result.output

        # Verify determinism
        result2 = runner.invoke(
            cli,
            [
                "setup",
                "--preset",
                "custom",
                "--override",
                "claude=mise_binary",
                "--override",
                "cline=mise_binary",
                "--dry-run",
            ],
        )
        assert result2.exit_code == 0
        assert result.output == result2.output, "Dry-run output should be deterministic"


class TestUpgradeCommand:
    """Tests for upgrade command behavior."""

    def test_upgrade_uses_adapter_layer(self, runner, monkeypatch):
        """Test that upgrade command uses adapter layer for upgrade command."""
        import logging

        # Reset logging
        _logging = logging.getLogger("reincheck")
        _logging.handlers.clear()
        _logging.setLevel(logging.DEBUG)

        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            # Create test config with agent that needs upgrade
            test_config = {
                "agents": [
                    {
                        "name": "test-agent",
                        "description": "Test agent",
                        "install_command": "echo install",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 2.0.0",
                        "upgrade_command": "echo upgrade",
                        "latest_version": "2.0.0",
                    }
                ]
            }
            config_file.write_text(json.dumps(test_config))

            # Mock get_config_dir to return tmpdir
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            # Import original adapter before patching
            from reincheck.adapter import get_effective_method_from_config

            original_adapter = get_effective_method_from_config

            # Track if adapter was called
            adapter_called = {"count": 0}

            def mock_adapter(config):
                adapter_called["count"] += 1
                return original_adapter(config)

            # Import upgrade module to enable monkeypatching
            import sys
            import importlib

            importlib.import_module("reincheck.commands.upgrade")

            # Mock get_current_version to return lower version
            async def mock_get_current_version(agent_config):
                return "1.0.0", "success"

            monkeypatch.setattr(
                sys.modules["reincheck.commands.upgrade"],
                "get_current_version",
                mock_get_current_version,
            )

            # Mock run_command_async for upgrade
            async def mock_run_command_async(command, **kwargs):
                return "upgraded successfully", 0

            monkeypatch.setattr(
                sys.modules["reincheck.commands.upgrade"],
                "run_command_async",
                mock_run_command_async,
            )

            # Patch the adapter on the upgrade module
            monkeypatch.setattr(
                sys.modules["reincheck.commands.upgrade"],
                "get_effective_method_from_config",
                mock_adapter,
            )

            result = runner.invoke(cli, ["upgrade"])

            assert result.exit_code == 0
            assert adapter_called["count"] > 0, "Adapter should have been called"
            assert "✅ test-agent upgraded successfully" in result.output

    def test_upgrade_dry_run(self, runner, monkeypatch):
        """Test that dry-run mode shows what would be upgraded without executing."""

        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            # Create test config with multiple agents
            test_config = {
                "agents": [
                    {
                        "name": "agent-a",
                        "description": "Agent A",
                        "install_command": "echo install",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 2.0.0",
                        "upgrade_command": "echo upgrade-a",
                        "latest_version": "2.0.0",
                    },
                    {
                        "name": "agent-b",
                        "description": "Agent B",
                        "install_command": "echo install",
                        "version_command": "echo 1.5.0",
                        "check_latest_command": "echo 3.0.0",
                        "upgrade_command": "echo upgrade-b",
                        "latest_version": "3.0.0",
                    },
                ]
            }
            config_file.write_text(json.dumps(test_config))

            # Mock get_config_dir to return tmpdir
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            # Import upgrade module to enable monkeypatching
            import sys
            import importlib

            importlib.import_module("reincheck.commands.upgrade")

            # Mock get_current_version to return lower versions
            async def mock_get_current_version(agent_config):
                if agent_config.name == "agent-a":
                    return "1.0.0", "success"
                return "1.5.0", "success"

            monkeypatch.setattr(
                sys.modules["reincheck.commands.upgrade"],
                "get_current_version",
                mock_get_current_version,
            )

            result = runner.invoke(cli, ["upgrade", "--dry-run"])

            assert result.exit_code == 0
            assert "The following upgrades would be performed:" in result.output
            assert "agent-a: 1.0.0 → 2.0.0" in result.output
            assert "agent-b: 1.5.0 → 3.0.0" in result.output

    def test_upgrade_specific_agent(self, runner, monkeypatch):
        """Test that --agent flag upgrades only specified agent."""

        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            # Create test config with multiple agents
            test_config = {
                "agents": [
                    {
                        "name": "agent-a",
                        "description": "Agent A",
                        "install_command": "echo install",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 2.0.0",
                        "upgrade_command": "echo upgrade-a",
                        "latest_version": "2.0.0",
                    },
                    {
                        "name": "agent-b",
                        "description": "Agent B",
                        "install_command": "echo install",
                        "version_command": "echo 1.5.0",
                        "check_latest_command": "echo 3.0.0",
                        "upgrade_command": "echo upgrade-b",
                        "latest_version": "3.0.0",
                    },
                ]
            }
            config_file.write_text(json.dumps(test_config))

            # Mock get_config_dir to return tmpdir
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            # Import upgrade module to enable monkeypatching
            import sys
            import importlib

            importlib.import_module("reincheck.commands.upgrade")

            # Mock get_current_version to return lower versions
            async def mock_get_current_version(agent_config):
                if agent_config.name == "agent-a":
                    return "1.0.0", "success"
                return "1.5.0", "success"

            monkeypatch.setattr(
                sys.modules["reincheck.commands.upgrade"],
                "get_current_version",
                mock_get_current_version,
            )

            # Track which upgrade commands were executed
            executed_upgrades = []

            async def mock_run_command_async(command, **kwargs):
                executed_upgrades.append(command)
                return "upgraded", 0

            monkeypatch.setattr(
                sys.modules["reincheck.commands.upgrade"],
                "run_command_async",
                mock_run_command_async,
            )

            result = runner.invoke(cli, ["upgrade", "--agent", "agent-a"])

            assert result.exit_code == 0
            assert len(executed_upgrades) == 1
            assert "echo upgrade-a" in executed_upgrades[0]
            assert "✅ agent-a upgraded successfully" in result.output

    def test_upgrade_no_updates_available(self, runner, monkeypatch):
        """Test that upgrade reports no updates when all agents are current."""

        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            # Create test config with agents already at latest version
            test_config = {
                "agents": [
                    {
                        "name": "current-agent",
                        "description": "Current agent",
                        "install_command": "echo install",
                        "version_command": "echo 2.0.0",
                        "check_latest_command": "echo 2.0.0",
                        "upgrade_command": "echo upgrade",
                        "latest_version": "2.0.0",
                    }
                ]
            }
            config_file.write_text(json.dumps(test_config))

            # Mock get_config_dir to return tmpdir
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            # Import upgrade module to enable monkeypatching
            import sys
            import importlib

            importlib.import_module("reincheck.commands.upgrade")

            # Mock get_current_version to return latest version
            async def mock_get_current_version(agent_config):
                return "2.0.0", "success"

            monkeypatch.setattr(
                sys.modules["reincheck.commands.upgrade"],
                "get_current_version",
                mock_get_current_version,
            )

            result = runner.invoke(cli, ["upgrade"])

            assert result.exit_code == 0
            assert "No agents need updating" in result.output

    def test_upgrade_failed(self, runner, monkeypatch):
        """Test that failed upgrade is reported correctly."""

        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            # Create test config
            test_config = {
                "agents": [
                    {
                        "name": "failing-agent",
                        "description": "Failing agent",
                        "install_command": "echo install",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 2.0.0",
                        "upgrade_command": "exit 1",  # This will fail
                        "latest_version": "2.0.0",
                    }
                ]
            }
            config_file.write_text(json.dumps(test_config))

            # Mock get_config_dir to return tmpdir
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            # Import upgrade module to enable monkeypatching
            import sys
            import importlib

            importlib.import_module("reincheck.commands.upgrade")

            # Mock get_current_version to return lower version
            async def mock_get_current_version(agent_config):
                return "1.0.0", "success"

            monkeypatch.setattr(
                sys.modules["reincheck.commands.upgrade"],
                "get_current_version",
                mock_get_current_version,
            )

            result = runner.invoke(cli, ["upgrade"])

            assert result.exit_code == 0
            assert "❌ failing-agent upgrade failed" in result.output

    def test_upgrade_debug_mode(self, runner, monkeypatch):
        """Test that debug mode shows upgrade command from adapter."""
        import logging

        # Reset logging
        _logging = logging.getLogger("reincheck")
        _logging.handlers.clear()
        _logging.setLevel(logging.DEBUG)

        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            # Create test config
            test_config = {
                "agents": [
                    {
                        "name": "test-agent",
                        "description": "Test agent",
                        "install_command": "echo install",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 2.0.0",
                        "upgrade_command": "echo special-upgrade-command",
                        "latest_version": "2.0.0",
                    }
                ]
            }
            config_file.write_text(json.dumps(test_config))

            # Mock get_config_dir to return tmpdir
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            # Import upgrade module to enable monkeypatching
            import sys
            import importlib

            importlib.import_module("reincheck.commands.upgrade")

            # Mock get_current_version to return lower version
            async def mock_get_current_version(agent_config):
                return "1.0.0", "success"

            monkeypatch.setattr(
                sys.modules["reincheck.commands.upgrade"],
                "get_current_version",
                mock_get_current_version,
            )

            async def mock_run_command_async(command, **kwargs):
                return "upgraded", 0

            monkeypatch.setattr(
                sys.modules["reincheck.commands.upgrade"],
                "run_command_async",
                mock_run_command_async,
            )

            result = runner.invoke(cli, ["--debug", "upgrade"])

            assert result.exit_code == 0
            assert "DEBUG:" in result.output
            assert "echo special-upgrade-command" in result.output

    def test_upgrade_agent_not_found(self, runner, monkeypatch):
        """Test error when specified agent not found."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            # Create test config
            test_config = {
                "agents": [
                    {
                        "name": "existing-agent",
                        "description": "Existing agent",
                        "install_command": "echo install",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 2.0.0",
                        "upgrade_command": "echo upgrade",
                        "latest_version": "2.0.0",
                    }
                ]
            }
            config_file.write_text(json.dumps(test_config))

            # Mock get_config_dir to return tmpdir
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            result = runner.invoke(cli, ["upgrade", "--agent", "nonexistent"])

            assert result.exit_code == 1
            assert "Agent 'nonexistent' not found in configuration" in result.output


class TestUpdateCommand:
    """Tests for update command behavior."""

    def test_update_uses_adapter_layer(self, runner, monkeypatch):
        """Test that update command uses adapter layer for version checking."""
        # Import update module to enable monkeypatching
        import sys
        import importlib

        importlib.import_module("reincheck.commands.update")

        # Track if adapter was called
        adapter_called = {"count": 0}
        original_adapter = sys.modules[
            "reincheck.commands.update"
        ].get_effective_method_from_config

        def mock_adapter(config):
            adapter_called["count"] += 1
            return original_adapter(config)

        monkeypatch.setattr(
            sys.modules["reincheck.commands.update"],
            "get_effective_method_from_config",
            mock_adapter,
        )

        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            # Create test config
            test_config = {
                "agents": [
                    {
                        "name": "test-agent",
                        "description": "Test agent",
                        "install_command": "echo install",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 2.0.0",
                        "upgrade_command": "echo upgrade",
                    }
                ]
            }
            config_file.write_text(json.dumps(test_config))

            # Mock get_config_dir to return tmpdir
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            result = runner.invoke(cli, ["update", "--quiet"])

            assert result.exit_code == 0
            assert adapter_called["count"] > 0, "Adapter should have been called"

            # Verify latest_version was saved
            updated_config = json.loads(config_file.read_text())
            assert updated_config["agents"][0]["latest_version"] == "2.0.0"

    def test_update_successful_save(self, runner, monkeypatch):
        """Test that successful update saves version to config."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            # Create test config
            test_config = {
                "agents": [
                    {
                        "name": "test-agent",
                        "description": "Test agent",
                        "install_command": "echo install",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 2.5.0",
                        "upgrade_command": "echo upgrade",
                    }
                ]
            }
            config_file.write_text(json.dumps(test_config))

            # Mock get_config_dir to return tmpdir
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            result = runner.invoke(cli, ["update"])

            assert result.exit_code == 0
            assert "✅ test-agent: 2.5.0" in result.output
            assert "All agents updated successfully" in result.output

            # Verify config was updated
            updated_config = json.loads(config_file.read_text())
            assert updated_config["agents"][0]["latest_version"] == "2.5.0"

    def test_update_failed_agent(self, runner, monkeypatch):
        """Test that failed update reports error correctly."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            # Create test config with failing check command
            test_config = {
                "agents": [
                    {
                        "name": "failing-agent",
                        "description": "Failing agent",
                        "install_command": "echo install",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "exit 1",  # This will fail
                        "upgrade_command": "echo upgrade",
                    }
                ]
            }
            config_file.write_text(json.dumps(test_config))

            # Mock get_config_dir to return tmpdir
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            result = runner.invoke(cli, ["update"])

            assert result.exit_code == 1
            assert "❌ failing-agent:" in result.output
            assert "1 agent(s) failed to update" in result.output

    def test_update_specific_agent(self, runner, monkeypatch):
        """Test --agent flag updates only specified agent."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            # Create test config with multiple agents
            test_config = {
                "agents": [
                    {
                        "name": "agent-a",
                        "description": "Agent A",
                        "install_command": "echo install",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 2.0.0",
                        "upgrade_command": "echo upgrade",
                    },
                    {
                        "name": "agent-b",
                        "description": "Agent B",
                        "install_command": "echo install",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 3.0.0",
                        "upgrade_command": "echo upgrade",
                    },
                ]
            }
            config_file.write_text(json.dumps(test_config))

            # Mock get_config_dir to return tmpdir
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            result = runner.invoke(cli, ["update", "--agent", "agent-a"])

            assert result.exit_code == 0
            assert "Updating 1 agents..." in result.output
            assert "✅ agent-a: 2.0.0" in result.output
            assert "agent-b" not in result.output  # agent-b should not be updated

            # Verify only agent-a was updated
            updated_config = json.loads(config_file.read_text())
            assert updated_config["agents"][0]["latest_version"] == "2.0.0"
            assert "latest_version" not in updated_config["agents"][1]

    def test_update_quiet_mode(self, runner, monkeypatch):
        """Test --quiet flag suppresses output."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            # Create test config
            test_config = {
                "agents": [
                    {
                        "name": "test-agent",
                        "description": "Test agent",
                        "install_command": "echo install",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 2.0.0",
                        "upgrade_command": "echo upgrade",
                    }
                ]
            }
            config_file.write_text(json.dumps(test_config))

            # Mock get_config_dir to return tmpdir
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            result = runner.invoke(cli, ["update", "--quiet"])

            assert result.exit_code == 0
            assert "Updating" not in result.output
            assert "✅" not in result.output
            assert "All agents updated" not in result.output
            assert result.output == ""

            # Verify config was still updated
            updated_config = json.loads(config_file.read_text())
            assert updated_config["agents"][0]["latest_version"] == "2.0.0"

    def test_update_debug_mode_shows_adapter_command(self, runner, monkeypatch):
        """Test that debug mode shows command from adapter layer."""
        import logging

        # Reset logging to ensure debug output is captured
        _logging = logging.getLogger("reincheck")
        _logging.handlers.clear()
        _logging.setLevel(logging.DEBUG)

        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            # Create test config
            test_config = {
                "agents": [
                    {
                        "name": "test-agent",
                        "description": "Test agent",
                        "install_command": "echo install",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 2.0.0",
                        "upgrade_command": "echo upgrade",
                    }
                ]
            }
            config_file.write_text(json.dumps(test_config))

            # Mock get_config_dir to return tmpdir
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            result = runner.invoke(cli, ["--debug", "update"])

            assert result.exit_code == 0
            assert "DEBUG:" in result.output
            assert "echo 2.0.0" in result.output  # The command from adapter

    def test_update_agent_not_found(self, runner, monkeypatch):
        """Test error when specified agent not found."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            # Create test config
            test_config = {
                "agents": [
                    {
                        "name": "existing-agent",
                        "description": "Existing agent",
                        "install_command": "echo install",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 2.0.0",
                        "upgrade_command": "echo upgrade",
                    }
                ]
            }
            config_file.write_text(json.dumps(test_config))

            # Mock get_config_dir to return tmpdir
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            result = runner.invoke(cli, ["update", "--agent", "nonexistent"])

            assert result.exit_code == 2
            assert "Agent 'nonexistent' not found in configuration" in result.output

    def test_update_efficient_command_passing(self, runner, monkeypatch):
        """Test that update works efficiently without round-trip conversions."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            # Create test config
            test_config = {
                "agents": [
                    {
                        "name": "efficient-agent",
                        "description": "Test efficient update",
                        "install_command": "echo install",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 2.0.0",
                        "upgrade_command": "echo upgrade",
                        "latest_version": "1.0.0",
                    }
                ]
            }
            config_file.write_text(json.dumps(test_config))

            # Mock get_config_dir to return tmpdir
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            result = runner.invoke(cli, ["update", "--quiet"])

            assert result.exit_code == 0
            # Verify config was updated
            updated_config = json.loads(config_file.read_text())
            assert updated_config["agents"][0]["latest_version"] == "2.0.0"

    def test_update_failing_check_command(self, runner, monkeypatch):
        """Test that failing check command reports error correctly."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            # Create test config
            test_config = {
                "agents": [
                    {
                        "name": "failing-agent",
                        "description": "Failing agent",
                        "install_command": "echo install",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "exit 1",
                        "upgrade_command": "echo upgrade",
                    }
                ]
            }
            config_file.write_text(json.dumps(test_config))

            # Mock get_config_dir to return tmpdir
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            result = runner.invoke(cli, ["update"])

            assert result.exit_code == 1
            assert "❌ failing-agent:" in result.output
            assert "1 agent(s) failed to update" in result.output


class TestListCommand:
    """Tests for list command behavior."""

    def test_list_default_format_single_agent_installed(self, runner, monkeypatch):
        """Test default output shows one line per agent with version."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            test_config = {
                "agents": [
                    {
                        "name": "test-agent",
                        "description": "A test agent",
                        "install_command": "echo install",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 1.0.0",
                        "upgrade_command": "echo upgrade",
                    }
                ]
            }
            config_file.write_text(json.dumps(test_config))
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            # Mock get_current_version to return installed version
            async def mock_get_current_version(agent_config):
                return "1.0.0", "success"

            monkeypatch.setattr(
                "reincheck.commands.get_current_version", mock_get_current_version
            )

            result = runner.invoke(cli, ["list"])

            assert result.exit_code == 0
            assert "test-agent: 1.0.0" in result.output

    def test_list_default_format_single_agent_not_installed(self, runner, monkeypatch):
        """Test default output shows 'not installed' for uninstalled agents."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            test_config = {
                "agents": [
                    {
                        "name": "test-agent",
                        "description": "A test agent",
                        "install_command": "echo install",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 1.0.0",
                        "upgrade_command": "echo upgrade",
                    }
                ]
            }
            config_file.write_text(json.dumps(test_config))
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            # Import list module to enable monkeypatching
            import sys
            import importlib

            importlib.import_module("reincheck.commands.list")

            # Mock get_current_version to return not installed
            async def mock_get_current_version(agent_config):
                return None, "not_installed"

            monkeypatch.setattr(
                sys.modules["reincheck.commands.list"],
                "get_current_version",
                mock_get_current_version,
            )

            result = runner.invoke(cli, ["list"])

            assert result.exit_code == 0
            assert "test-agent: not installed" in result.output

    def test_list_default_format_multiple_agents_mixed(self, runner, monkeypatch):
        """Test default output with mix of installed and uninstalled agents."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            test_config = {
                "agents": [
                    {
                        "name": "agent-a",
                        "description": "Agent A",
                        "install_command": "echo install",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 1.0.0",
                        "upgrade_command": "echo upgrade",
                    },
                    {
                        "name": "agent-b",
                        "description": "Agent B",
                        "install_command": "echo install",
                        "version_command": "echo 2.0.0",
                        "check_latest_command": "echo 2.0.0",
                        "upgrade_command": "echo upgrade",
                    },
                ]
            }
            config_file.write_text(json.dumps(test_config))
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            # Import list module to enable monkeypatching
            import sys
            import importlib

            importlib.import_module("reincheck.commands.list")

            # Mock get_current_version with mixed results
            async def mock_get_current_version(agent_config):
                if agent_config.name == "agent-a":
                    return "1.0.0", "success"
                return None, "not_installed"

            monkeypatch.setattr(
                sys.modules["reincheck.commands.list"],
                "get_current_version",
                mock_get_current_version,
            )

            result = runner.invoke(cli, ["list"])

            assert result.exit_code == 0
            assert "agent-a: 1.0.0" in result.output
            assert "agent-b: not installed" in result.output

    def test_list_empty_agents(self, runner, monkeypatch):
        """Test list with no configured agents."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            test_config = {"agents": []}
            config_file.write_text(json.dumps(test_config))
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            result = runner.invoke(cli, ["list"])

            assert result.exit_code == 0
            assert "No agents configured" in result.output

    def test_list_verbose_shows_description(self, runner, monkeypatch):
        """Test verbose output includes agent description."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            test_config = {
                "agents": [
                    {
                        "name": "test-agent",
                        "description": "My test agent description",
                        "install_command": "echo install",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 1.0.0",
                        "upgrade_command": "echo upgrade",
                    }
                ]
            }
            config_file.write_text(json.dumps(test_config))
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            async def mock_get_current_version(agent_config):
                return "1.0.0", "success"

            monkeypatch.setattr(
                "reincheck.commands.get_current_version", mock_get_current_version
            )

            result = runner.invoke(cli, ["list", "-v"])

            assert result.exit_code == 0
            assert "My test agent description" in result.output

    def test_list_verbose_shows_version(self, runner, monkeypatch):
        """Test verbose output shows current version."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            test_config = {
                "agents": [
                    {
                        "name": "test-agent",
                        "description": "Test agent",
                        "install_command": "echo install",
                        "version_command": "echo 2.5.0",
                        "check_latest_command": "echo 2.5.0",
                        "upgrade_command": "echo upgrade",
                    }
                ]
            }
            config_file.write_text(json.dumps(test_config))
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            async def mock_get_current_version(agent_config):
                return "2.5.0", "success"

            monkeypatch.setattr(
                "reincheck.commands.get_current_version", mock_get_current_version
            )

            result = runner.invoke(cli, ["list", "--verbose"])

            assert result.exit_code == 0
            assert "Current version: 2.5.0" in result.output

    def test_list_verbose_shows_not_installed(self, runner, monkeypatch):
        """Test verbose output shows 'not installed' for uninstalled agents."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            test_config = {
                "agents": [
                    {
                        "name": "test-agent",
                        "description": "Test agent",
                        "install_command": "echo install",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 1.0.0",
                        "upgrade_command": "echo upgrade",
                    }
                ]
            }
            config_file.write_text(json.dumps(test_config))
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            # Import list module to enable monkeypatching
            import sys
            import importlib

            importlib.import_module("reincheck.commands.list")

            async def mock_get_current_version(agent_config):
                return None, "not_installed"

            monkeypatch.setattr(
                sys.modules["reincheck.commands.list"],
                "get_current_version",
                mock_get_current_version,
            )

            result = runner.invoke(cli, ["list", "-v"])

            assert result.exit_code == 0
            assert "Current version: not installed" in result.output

    def test_list_verbose_shows_source(self, runner, monkeypatch):
        """Test verbose output shows source/method information."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            test_config = {
                "agents": [
                    {
                        "name": "test-agent",
                        "description": "Test agent",
                        "install_command": "echo install",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 1.0.0",
                        "upgrade_command": "echo upgrade",
                    }
                ]
            }
            config_file.write_text(json.dumps(test_config))
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            async def mock_get_current_version(agent_config):
                return "1.0.0", "success"

            monkeypatch.setattr(
                "reincheck.commands.get_current_version", mock_get_current_version
            )

            result = runner.invoke(cli, ["list", "-v"])

            assert result.exit_code == 0
            assert "Source:" in result.output

    def test_list_verbose_shows_available_methods(self, runner, monkeypatch):
        """Test verbose output shows available methods when they exist."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            test_config = {
                "agents": [
                    {
                        "name": "claude",
                        "description": "Claude agent",
                        "install_command": "echo install",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 1.0.0",
                        "upgrade_command": "echo upgrade",
                    }
                ]
            }
            config_file.write_text(json.dumps(test_config))
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            async def mock_get_current_version(agent_config):
                return "1.0.0", "success"

            monkeypatch.setattr(
                "reincheck.commands.get_current_version", mock_get_current_version
            )

            result = runner.invoke(cli, ["list", "-v"])

            assert result.exit_code == 0
            assert "Available methods:" in result.output

    def test_list_verbose_formatting(self, runner, monkeypatch):
        """Test verbose output has proper formatting with bullets and indentation."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            test_config = {
                "agents": [
                    {
                        "name": "test-agent",
                        "description": "Test agent",
                        "install_command": "echo install",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 1.0.0",
                        "upgrade_command": "echo upgrade",
                    }
                ]
            }
            config_file.write_text(json.dumps(test_config))
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            async def mock_get_current_version(agent_config):
                return "1.0.0", "success"

            monkeypatch.setattr(
                "reincheck.commands.get_current_version", mock_get_current_version
            )

            result = runner.invoke(cli, ["list", "-v"])

            assert result.exit_code == 0
            # Check for bullet point and indentation
            assert "• test-agent" in result.output
            assert "  Description:" in result.output
            assert "  Current version:" in result.output
            assert "  Source:" in result.output

    def test_list_verbose_vs_default_difference(self, runner, monkeypatch):
        """Test that verbose and default outputs are distinctly different."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            test_config = {
                "agents": [
                    {
                        "name": "test-agent",
                        "description": "Test agent description",
                        "install_command": "echo install",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 1.0.0",
                        "upgrade_command": "echo upgrade",
                    }
                ]
            }
            config_file.write_text(json.dumps(test_config))
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            async def mock_get_current_version(agent_config):
                return "1.0.0", "success"

            monkeypatch.setattr(
                "reincheck.commands.get_current_version", mock_get_current_version
            )

            # Get default output
            default_result = runner.invoke(cli, ["list"])
            # Get verbose output
            verbose_result = runner.invoke(cli, ["list", "-v"])

            assert default_result.exit_code == 0
            assert verbose_result.exit_code == 0

            # Default should be one line
            default_lines = [
                line for line in default_result.output.split("\n") if line.strip()
            ]
            assert len(default_lines) == 1
            assert "test-agent: 1.0.0" in default_result.output

            # Verbose should have multiple lines with description
            assert "Test agent description" in verbose_result.output
            assert "Description:" in verbose_result.output

    def test_list_both_flags_equivalent(self, runner, monkeypatch):
        """Test that -v and --verbose produce same output."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            test_config = {
                "agents": [
                    {
                        "name": "test-agent",
                        "description": "Test agent",
                        "install_command": "echo install",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 1.0.0",
                        "upgrade_command": "echo upgrade",
                    }
                ]
            }
            config_file.write_text(json.dumps(test_config))
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            async def mock_get_current_version(agent_config):
                return "1.0.0", "success"

            monkeypatch.setattr(
                "reincheck.commands.get_current_version", mock_get_current_version
            )

            short_flag_result = runner.invoke(cli, ["list", "-v"])
            long_flag_result = runner.invoke(cli, ["list", "--verbose"])

            assert short_flag_result.exit_code == 0
            assert long_flag_result.exit_code == 0
            assert short_flag_result.output == long_flag_result.output


class TestInstallCommand:
    """Tests for install command behavior."""

    def test_install_uses_preset_method_when_available(self, runner, monkeypatch):
        """Test that install uses method from preset when harness is in preset."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            # Create test config with preset and claude agent
            test_config = {
                "agents": [
                    {
                        "name": "claude",
                        "description": "Claude Code",
                        "install_command": "echo config-install",  # Should NOT use this
                        "version_command": "claude --version",
                        "check_latest_command": "echo 1.0.0",
                        "upgrade_command": "echo upgrade",
                    }
                ],
                "preset": "mise_binary",  # Active preset
            }
            config_file.write_text(json.dumps(test_config))
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            # Import install module to enable monkeypatching
            import sys
            import importlib

            importlib.import_module("reincheck.commands.install")

            # Mock get_current_version to return not installed
            async def mock_get_current_version(agent_config):
                return None, "not_installed"

            monkeypatch.setattr(
                sys.modules["reincheck.commands.install"],
                "get_current_version",
                mock_get_current_version,
            )

            # Track which install command was executed
            executed_commands = []

            async def mock_run_command_async(command, **kwargs):
                executed_commands.append(command)
                return "installed successfully", 0

            monkeypatch.setattr(
                sys.modules["reincheck.commands.install"],
                "run_command_async",
                mock_run_command_async,
            )

            result = runner.invoke(cli, ["install", "claude"])

            assert result.exit_code == 0
            assert "✅ claude installed successfully" in result.output
            # Should use mise_binary method, not config's install_command
            assert len(executed_commands) == 1
            assert "mise" in executed_commands[0].lower()
            assert "config-install" not in executed_commands[0]

    def test_install_falls_back_to_config_when_harness_not_in_preset(
        self, runner, monkeypatch
    ):
        """Test that install falls back to config when harness not in preset."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            # Create test config with preset but custom agent not in preset
            test_config = {
                "agents": [
                    {
                        "name": "custom-agent",
                        "description": "Custom Agent",
                        "install_command": "echo custom-config-install",  # Should use this
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 1.0.0",
                        "upgrade_command": "echo upgrade",
                    }
                ],
                "preset": "mise_binary",  # Active preset (but custom-agent not in it)
            }
            config_file.write_text(json.dumps(test_config))
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            # Import install module to enable monkeypatching
            import sys
            import importlib

            importlib.import_module("reincheck.commands.install")

            # Mock get_current_version to return not installed
            async def mock_get_current_version(agent_config):
                return None, "not_installed"

            monkeypatch.setattr(
                sys.modules["reincheck.commands.install"],
                "get_current_version",
                mock_get_current_version,
            )

            # Track which install command was executed
            executed_commands = []

            async def mock_run_command_async(command, **kwargs):
                executed_commands.append(command)
                return "installed successfully", 0

            monkeypatch.setattr(
                sys.modules["reincheck.commands.install"],
                "run_command_async",
                mock_run_command_async,
            )

            result = runner.invoke(cli, ["install", "custom-agent"])

            assert result.exit_code == 0
            assert "✅ custom-agent installed successfully" in result.output
            # Should fall back to config's install_command
            assert len(executed_commands) == 1
            assert executed_commands[0] == "echo custom-config-install"

    def test_install_falls_back_to_config_when_no_preset(self, runner, monkeypatch):
        """Test that install uses config when no preset is set."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            # Create test config without preset
            test_config = {
                "agents": [
                    {
                        "name": "test-agent",
                        "description": "Test Agent",
                        "install_command": "echo legacy-install",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 1.0.0",
                        "upgrade_command": "echo upgrade",
                    }
                ]
                # No preset field
            }
            config_file.write_text(json.dumps(test_config))
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            # Import install module to enable monkeypatching
            import sys
            import importlib

            importlib.import_module("reincheck.commands.install")

            # Mock get_current_version to return not installed
            async def mock_get_current_version(agent_config):
                return None, "not_installed"

            monkeypatch.setattr(
                sys.modules["reincheck.commands.install"],
                "get_current_version",
                mock_get_current_version,
            )

            # Track which install command was executed
            executed_commands = []

            async def mock_run_command_async(command, **kwargs):
                executed_commands.append(command)
                return "installed successfully", 0

            monkeypatch.setattr(
                sys.modules["reincheck.commands.install"],
                "run_command_async",
                mock_run_command_async,
            )

            result = runner.invoke(cli, ["install", "test-agent"])

            assert result.exit_code == 0
            assert "✅ test-agent installed successfully" in result.output
            # Should use config's install_command
            assert len(executed_commands) == 1
            assert executed_commands[0] == "echo legacy-install"

    def test_install_skips_when_already_installed(self, runner, monkeypatch):
        """Test that install skips when agent is already installed."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            test_config = {
                "agents": [
                    {
                        "name": "test-agent",
                        "description": "Test Agent",
                        "install_command": "echo install",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 1.0.0",
                        "upgrade_command": "echo upgrade",
                    }
                ]
            }
            config_file.write_text(json.dumps(test_config))
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            # Import install module to enable monkeypatching
            import sys
            import importlib

            importlib.import_module("reincheck.commands.install")

            # Mock get_current_version to return installed version
            async def mock_get_current_version(agent_config):
                return "1.0.0", "success"

            monkeypatch.setattr(
                sys.modules["reincheck.commands.install"],
                "get_current_version",
                mock_get_current_version,
            )

            result = runner.invoke(cli, ["install", "test-agent"])

            assert result.exit_code == 0
            assert "already installed" in result.output
            assert "Use --force to reinstall" in result.output

    def test_install_force_reinstalls(self, runner, monkeypatch):
        """Test that --force reinstalls even when already installed."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            test_config = {
                "agents": [
                    {
                        "name": "test-agent",
                        "description": "Test Agent",
                        "install_command": "echo reinstall",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 1.0.0",
                        "upgrade_command": "echo upgrade",
                    }
                ]
            }
            config_file.write_text(json.dumps(test_config))
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            # Import install module to enable monkeypatching
            import sys
            import importlib

            importlib.import_module("reincheck.commands.install")

            # Mock get_current_version to return installed version
            async def mock_get_current_version(agent_config):
                return "1.0.0", "success"

            monkeypatch.setattr(
                sys.modules["reincheck.commands.install"],
                "get_current_version",
                mock_get_current_version,
            )

            executed_commands = []

            async def mock_run_command_async(command, **kwargs):
                executed_commands.append(command)
                return "reinstalled successfully", 0

            monkeypatch.setattr(
                sys.modules["reincheck.commands.install"],
                "run_command_async",
                mock_run_command_async,
            )

            result = runner.invoke(cli, ["install", "test-agent", "--force"])

            assert result.exit_code == 0
            assert "✅ test-agent installed successfully" in result.output
            assert len(executed_commands) == 1
            assert executed_commands[0] == "echo reinstall"

    def test_install_reports_failure(self, runner, monkeypatch):
        """Test that install reports failure correctly."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            test_config = {
                "agents": [
                    {
                        "name": "failing-agent",
                        "description": "Failing Agent",
                        "install_command": "exit 1",
                        "version_command": "echo 1.0.0",
                        "check_latest_command": "echo 1.0.0",
                        "upgrade_command": "echo upgrade",
                    }
                ]
            }
            config_file.write_text(json.dumps(test_config))
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            # Import install module to enable monkeypatching
            import sys
            import importlib

            importlib.import_module("reincheck.commands.install")

            async def mock_get_current_version(agent_config):
                return None, "not_installed"

            monkeypatch.setattr(
                sys.modules["reincheck.commands.install"],
                "get_current_version",
                mock_get_current_version,
            )

            result = runner.invoke(cli, ["install", "failing-agent"])

            assert result.exit_code == 1
            assert "❌ failing-agent installation failed" in result.output

    def test_install_agent_not_found(self, runner, monkeypatch):
        """Test error when agent not found in configuration."""
        with runner.isolated_filesystem() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / ".config" / "reincheck"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "agents.json"

            test_config = {"agents": []}
            config_file.write_text(json.dumps(test_config))
            monkeypatch.setattr("reincheck.paths.get_config_dir", lambda: config_dir)

            result = runner.invoke(cli, ["install", "nonexistent"])

            assert result.exit_code == 1
            assert "Agent 'nonexistent' not found" in result.output

import pytest
from click.testing import CliRunner
from pathlib import Path
import os
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
        json_with_comments = '''{
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
        }'''
        
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
        
        json_with_comments = '''{
            // Comment to be removed
            "agents": [],
        }'''
        
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
        
        json_ordered = '''{
            "z_last": 1,
            "a_first": 2,
            "m_middle": 3
        }'''
        
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
            assert content.endswith('\n'), "File should end with trailing newline"

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
        result = runner.invoke(cli, ["setup", "--list-presets", "--preset", "mise_binary"])
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
        result = runner.invoke(cli, ["setup", "--preset", "mise_binary", "--harness", "nonexistent"])
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
        result = runner.invoke(cli, ["setup", "--preset", "mise_binary", "--harness", "claude", "--harness", "cline", "--dry-run"])
        assert result.exit_code == 0
        assert "[DRY-RUN]" in result.output
        assert "Would install harnesses:" in result.output
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

            result = runner.invoke(cli, ["setup", "--preset", "custom", "--override", "claude=language_native", "--yes"])
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
        result = runner.invoke(cli, ["setup", "--preset", "custom", "--override", "invalid"])
        assert result.exit_code != 0
        assert "Invalid override format" in result.output

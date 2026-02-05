import pytest
from click.testing import CliRunner
from pathlib import Path
from reincheck.commands import validate_pager, cli


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

    def test_fmt_stdout_with_comments_and_trailing_commas(self):
        """Test that fmt outputs strict JSON, stripping comments and trailing commas."""
        runner = CliRunner()
        
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

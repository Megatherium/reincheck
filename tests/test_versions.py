"""Tests for version utilities."""


class TestAddGithubAuthIfNeeded:
    """Tests for add_github_auth_if_needed function."""

    def test_basic_github_api_command_with_token(self, monkeypatch):
        """Test basic GitHub API command when token is set."""
        from reincheck.versions import add_github_auth_if_needed

        monkeypatch.setenv("GITHUB_TOKEN", "test_token_123")
        cmd = "curl -s https://api.github.com/repos/test/repo/releases/latest"
        result = add_github_auth_if_needed(cmd)

        assert "Authorization: Bearer test_token_123" in result
        assert "https://api.github.com" in result
        assert "curl" in result

    def test_github_api_command_with_existing_header(self, monkeypatch):
        """Test command with existing Authorization header is not modified."""
        from reincheck.versions import add_github_auth_if_needed

        monkeypatch.setenv("GITHUB_TOKEN", "test_token_123")
        cmd = 'curl -H "Authorization: Bearer existing" https://api.github.com/repos/test/repo/releases/latest'
        result = add_github_auth_if_needed(cmd)

        assert result == cmd

    def test_non_github_api_url(self, monkeypatch):
        """Test non-GitHub API URL is not modified."""
        from reincheck.versions import add_github_auth_if_needed

        monkeypatch.setenv("GITHUB_TOKEN", "test_token_123")
        cmd = "curl -s https://api.other.com/repos/test/releases/latest"
        result = add_github_auth_if_needed(cmd)

        assert result == cmd

    def test_no_token_set(self, monkeypatch):
        """Test command is not modified when GITHUB_TOKEN is not set."""
        from reincheck.versions import add_github_auth_if_needed

        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        cmd = "curl -s https://api.github.com/repos/test/repo/releases/latest"
        result = add_github_auth_if_needed(cmd)

        assert result == cmd

    def test_empty_token(self, monkeypatch):
        """Test command is not modified when GITHUB_TOKEN is empty."""
        from reincheck.versions import add_github_auth_if_needed

        monkeypatch.setenv("GITHUB_TOKEN", "")
        cmd = "curl -s https://api.github.com/repos/test/repo/releases/latest"
        result = add_github_auth_if_needed(cmd)

        assert result == cmd

    def test_non_curl_command(self, monkeypatch):
        """Test non-curl command is not modified."""
        from reincheck.versions import add_github_auth_if_needed

        monkeypatch.setenv("GITHUB_TOKEN", "test_token_123")
        cmd = "npm info @test/package version"
        result = add_github_auth_if_needed(cmd)

        assert result == cmd

    def test_pipe_command(self, monkeypatch):
        """Test pipe command with curl."""
        from reincheck.versions import add_github_auth_if_needed

        monkeypatch.setenv("GITHUB_TOKEN", "test_token_123")
        cmd = (
            "curl -s https://api.github.com/repos/test/releases/latest | grep tag_name"
        )
        result = add_github_auth_if_needed(cmd)

        assert "Authorization: Bearer test_token_123" in result
        assert " | grep tag_name" in result
        assert "https://api.github.com" in result

    def test_pipe_command_without_github(self, monkeypatch):
        """Test pipe command not targeting GitHub API."""
        from reincheck.versions import add_github_auth_if_needed

        monkeypatch.setenv("GITHUB_TOKEN", "test_token_123")
        cmd = "curl -s https://api.other.com/data | jq .version"
        result = add_github_auth_if_needed(cmd)

        assert result == cmd

    def test_command_with_multiple_curl(self, monkeypatch):
        """Test command with multiple curl references (only first should be modified)."""
        from reincheck.versions import add_github_auth_if_needed

        monkeypatch.setenv("GITHUB_TOKEN", "test_token_123")
        cmd = "curl -s https://api.github.com/repos/test/releases/latest | xargs curl"
        result = add_github_auth_if_needed(cmd)

        assert result.count("Authorization: Bearer") == 1

    def test_command_with_quoted_args(self, monkeypatch):
        """Test command with quoted arguments."""
        from reincheck.versions import add_github_auth_if_needed

        monkeypatch.setenv("GITHUB_TOKEN", "test_token_123")
        cmd = 'curl -s "https://api.github.com/repos/test repo/releases/latest"'
        result = add_github_auth_if_needed(cmd)

        assert "Authorization: Bearer test_token_123" in result
        assert "https://api.github.com" in result

    def test_command_with_special_characters_in_token(self, monkeypatch):
        """Test token with special characters is properly handled."""
        from reincheck.versions import add_github_auth_if_needed

        monkeypatch.setenv("GITHUB_TOKEN", "ghp_token.123_ABC-def")
        cmd = "curl -s https://api.github.com/repos/test/releases/latest"
        result = add_github_auth_if_needed(cmd)

        assert "Authorization: Bearer ghp_token.123_ABC-def" in result

    def test_github_com_non_api_url(self, monkeypatch):
        """Test github.com URL that is not API URL is not modified."""
        from reincheck.versions import add_github_auth_if_needed

        monkeypatch.setenv("GITHUB_TOKEN", "test_token_123")
        cmd = "curl -s https://github.com/test/repo/releases/latest"
        result = add_github_auth_if_needed(cmd)

        assert result == cmd

    def test_empty_command(self, monkeypatch):
        """Test empty command string."""
        from reincheck.versions import add_github_auth_if_needed

        monkeypatch.setenv("GITHUB_TOKEN", "test_token_123")
        cmd = ""
        result = add_github_auth_if_needed(cmd)

        assert result == ""

    def test_command_with_existing_h_flag(self, monkeypatch):
        """Test command with existing -H flag gets additional header."""
        from reincheck.versions import add_github_auth_if_needed

        monkeypatch.setenv("GITHUB_TOKEN", "test_token_123")
        cmd = 'curl -H "Accept: application/json" https://api.github.com/repos/test/releases/latest'
        result = add_github_auth_if_needed(cmd)

        assert "Authorization: Bearer test_token_123" in result
        assert "Accept: application/json" in result

    def test_complex_pipe_chain(self, monkeypatch):
        """Test command with complex pipe chain."""
        from reincheck.versions import add_github_auth_if_needed

        monkeypatch.setenv("GITHUB_TOKEN", "test_token_123")
        cmd = 'curl -s https://api.github.com/repos/test/releases/latest | grep tag_name | cut -d\\" -f4'
        result = add_github_auth_if_needed(cmd)

        assert "Authorization: Bearer test_token_123" in result
        assert ' | grep tag_name | cut -d\\" -f4' in result

    def test_whitespace_in_pipe(self, monkeypatch):
        """Test command with inconsistent whitespace in pipe."""
        from reincheck.versions import add_github_auth_if_needed

        monkeypatch.setenv("GITHUB_TOKEN", "test_token_123")
        cmd = 'curl -s https://api.github.com/repos/test/releases/latest|grep tag_name|cut -d\\" -f4'
        result = add_github_auth_if_needed(cmd)

        assert "Authorization: Bearer test_token_123" in result

    def test_real_world_crush_command(self, monkeypatch):
        """Test real-world command from crush agent."""
        from reincheck.versions import add_github_auth_if_needed

        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123")
        cmd = "curl -s https://api.github.com/repos/charmbracelet/crush/releases/latest | grep 'tag_name' | cut -d'\"' -f4"
        result = add_github_auth_if_needed(cmd)

        assert "Authorization: Bearer ghp_test123" in result
        assert "charmbracelet/crush" in result
        assert "grep" in result

    def test_real_world_goose_command(self, monkeypatch):
        """Test real-world command from goose agent."""
        from reincheck.versions import add_github_auth_if_needed

        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test456")
        cmd = 'curl -s https://api.github.com/repos/block/goose/releases/latest | grep "tag_name" | cut -d"\\"" -f4'
        result = add_github_auth_if_needed(cmd)

        assert "Authorization: Bearer ghp_test456" in result
        assert "block/goose" in result

    def test_malformed_command(self, monkeypatch):
        """Test malformed command that cannot be parsed."""
        from reincheck.versions import add_github_auth_if_needed

        monkeypatch.setenv("GITHUB_TOKEN", "test_token_123")
        cmd = 'curl -s "https://api.github.com/repos/test/releases/latest'
        result = add_github_auth_if_needed(cmd)

        assert result == cmd


class TestExtractVersionNumber:
    """Tests for extract_version_number function."""

    def test_extract_semantic_version(self):
        from reincheck.versions import extract_version_number

        assert extract_version_number("v1.2.3") == "1.2.3"
        assert extract_version_number("1.2.3") == "1.2.3"

    def test_extract_two_part_version(self):
        from reincheck.versions import extract_version_number

        assert extract_version_number("v1.2") == "1.2"
        assert extract_version_number("1.2") == "1.2"

    def test_extract_single_part_version(self):
        from reincheck.versions import extract_version_number

        assert extract_version_number("v1") == "1"
        assert extract_version_number("1") == "1"

    def test_extract_from_complex_string(self):
        from reincheck.versions import extract_version_number

        assert extract_version_number("Version 1.2.3 released") == "1.2.3"
        assert extract_version_number("v1.0.0-beta") == "1.0.0"

    def test_empty_string(self):
        from reincheck.versions import extract_version_number

        assert extract_version_number("") == ""

    def test_no_version_in_string(self):
        from reincheck.versions import extract_version_number

        assert extract_version_number("No version here") == ""

    def test_extract_four_part_version(self):
        from reincheck.versions import extract_version_number

        assert extract_version_number("1.2.3.4") == "1.2.3.4"


class TestCompareVersions:
    """Tests for compare_versions function."""

    def test_less_than(self):
        from reincheck.versions import compare_versions

        assert compare_versions("1.2.3", "1.2.4") == -1
        assert compare_versions("1.2", "1.3") == -1
        assert compare_versions("1", "2") == -1

    def test_greater_than(self):
        from reincheck.versions import compare_versions

        assert compare_versions("1.2.4", "1.2.3") == 1
        assert compare_versions("1.3", "1.2") == 1
        assert compare_versions("2", "1") == 1

    def test_equal(self):
        from reincheck.versions import compare_versions

        assert compare_versions("1.2.3", "1.2.3") == 0
        assert compare_versions("1.2", "1.2") == 0
        assert compare_versions("1", "1") == 0

    def test_version_strings(self):
        from reincheck.versions import compare_versions

        assert compare_versions("v1.2.3", "v1.2.3") == 0
        assert compare_versions("v1.2.3", "1.2.3") == 0
        assert compare_versions("v1.2.3", "v1.2.4") == -1

    def test_invalid_versions_fallback_to_string(self):
        from reincheck.versions import compare_versions

        assert compare_versions("abc", "def") == -1
        assert compare_versions("unknown", "1.0.0") == 1  # "u" > "1" in ASCII
        assert compare_versions("", "1.0.0") == -1

    def test_extracts_version_from_complex_strings(self):
        """Test that version numbers are extracted from strings with extra text."""
        from reincheck.versions import compare_versions

        assert compare_versions("1.2.x", "1.2.y") == 0
        assert compare_versions("1.2.3-beta", "1.2.3-alpha") == 0

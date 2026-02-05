import pytest
from reincheck.commands import validate_pager


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
                validate_pager(cmd)

    def test_rejected_absolute_paths(self):
        """Test that disallowed commands with absolute paths raise ValueError."""
        dangerous = ["/bin/rm", "/usr/bin/sh", "/bin/bash"]
        for cmd in dangerous:
            with pytest.raises(ValueError, match="Unsafe pager"):
                validate_pager(cmd)

    def test_rejected_with_args(self):
        """Test that commands with arguments are rejected."""
        with pytest.raises(ValueError, match="Unsafe pager"):
            validate_pager("less -R")
        with pytest.raises(ValueError, match="Unsafe pager"):
            validate_pager("cat file.txt")

    def test_error_message_includes_allowed_list(self):
        """Test that error message includes list of allowed pagers."""
        with pytest.raises(ValueError) as exc_info:
            validate_pager("rm -rf /")

        error_msg = str(exc_info.value)
        assert "Unsafe pager" in error_msg
        assert "cat" in error_msg
        assert "less" in error_msg
        assert "more" in error_msg

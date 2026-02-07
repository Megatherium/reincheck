"""Tests for TUI utilities."""

import sys
from io import StringIO
from unittest.mock import patch

import pytest

from reincheck.installer import DependencyStatus
from reincheck.tui import (
    format_dep_line,
    get_color_for_status,
    display_dependency_table,
    _scan_and_display_deps,
)


class TestFormatDepLine:
    """Tests for format_dep_line function."""

    def test_available_with_version(self):
        status = DependencyStatus(
            name="npm",
            available=True,
            version="10.8.0",
            path="/usr/bin/npm",
            version_satisfied=True,
        )
        result = format_dep_line(status, max_name_width=10)
        assert "✅" in result
        assert "npm" in result
        assert "10.8.0" in result
        assert "/usr/bin/npm" in result

    def test_available_with_v_prefix_version(self):
        status = DependencyStatus(
            name="node",
            available=True,
            version="v20.0.0",
            path="/usr/bin/node",
            version_satisfied=True,
        )
        result = format_dep_line(status, max_name_width=10)
        assert "✅" in result
        assert "v20.0.0" in result
        assert "v20.0.0v" not in result

    def test_missing_dependency(self):
        status = DependencyStatus(
            name="brew",
            available=False,
            version=None,
            path=None,
            version_satisfied=True,
        )
        result = format_dep_line(status, max_name_width=10)
        assert "❌" in result
        assert "brew" in result
        assert "missing" in result

    def test_version_not_satisfied(self):
        status = DependencyStatus(
            name="python",
            available=True,
            version="3.10.5",
            path="/usr/bin/python",
            version_satisfied=False,
        )
        result = format_dep_line(status, max_name_width=10)
        assert "⚠️" in result
        assert "python" in result
        assert "3.10.5" in result

    def test_available_no_version(self):
        status = DependencyStatus(
            name="curl",
            available=True,
            version=None,
            path="/usr/bin/curl",
            version_satisfied=True,
        )
        result = format_dep_line(status, max_name_width=10)
        assert "✅" in result
        assert "unknown" in result

    def test_name_alignment(self):
        short_status = DependencyStatus(
            name="uv",
            available=True,
            version="0.1.0",
            path="/usr/bin/uv",
            version_satisfied=True,
        )
        long_status = DependencyStatus(
            name="python",
            available=True,
            version="3.11.0",
            path="/usr/bin/python",
            version_satisfied=True,
        )

        short_line = format_dep_line(short_status, max_name_width=10)
        long_line = format_dep_line(long_status, max_name_width=10)

        assert "uv        " in short_line
        assert "python    " in long_line


class TestGetColorForStatus:
    """Tests for get_color_for_status function."""

    def test_available_green(self):
        status = DependencyStatus(
            name="npm",
            available=True,
            version="10.0.0",
            version_satisfied=True,
        )
        assert get_color_for_status(status) == "green"

    def test_missing_red(self):
        status = DependencyStatus(
            name="brew",
            available=False,
            version=None,
            version_satisfied=True,
        )
        assert get_color_for_status(status) == "red"

    def test_version_not_satisfied_yellow(self):
        status = DependencyStatus(
            name="python",
            available=True,
            version="3.10.0",
            version_satisfied=False,
        )
        assert get_color_for_status(status) == "yellow"


class TestDisplayDependencyTable:
    """Tests for display_dependency_table function."""

    def test_show_all_dependencies(self, capsys):
        statuses = {
            "npm": DependencyStatus(
                name="npm",
                available=True,
                version="10.0.0",
                path="/usr/bin/npm",
                version_satisfied=True,
            ),
            "brew": DependencyStatus(
                name="brew",
                available=False,
                version=None,
                path=None,
                version_satisfied=True,
            ),
        }
        display_dependency_table(statuses, show_all=True)
        captured = capsys.readouterr()
        assert "npm" in captured.out
        assert "brew" in captured.out

    def test_show_only_issues(self, capsys):
        statuses = {
            "npm": DependencyStatus(
                name="npm",
                available=True,
                version="10.0.0",
                path="/usr/bin/npm",
                version_satisfied=True,
            ),
            "brew": DependencyStatus(
                name="brew",
                available=False,
                version=None,
                path=None,
                version_satisfied=True,
            ),
        }
        display_dependency_table(statuses, show_all=False)
        captured = capsys.readouterr()
        assert "brew" in captured.out
        assert "npm" not in captured.out

    def test_required_deps_filter(self, capsys):
        statuses = {
            "npm": DependencyStatus(
                name="npm",
                available=True,
                version="10.0.0",
                path="/usr/bin/npm",
                version_satisfied=True,
            ),
            "brew": DependencyStatus(
                name="brew",
                available=False,
                version=None,
                path=None,
                version_satisfied=True,
            ),
        }
        display_dependency_table(statuses, required_deps=["npm"])
        captured = capsys.readouterr()
        assert "npm" in captured.out
        assert "brew" not in captured.out

    def test_all_satisfied_message(self, capsys):
        statuses = {
            "npm": DependencyStatus(
                name="npm",
                available=True,
                version="10.0.0",
                path="/usr/bin/npm",
                version_satisfied=True,
            ),
        }
        display_dependency_table(statuses, show_all=False)
        captured = capsys.readouterr()
        assert "All dependencies satisfied" in captured.out

    def test_empty_statuses(self, capsys):
        display_dependency_table({}, show_all=True)
        captured = capsys.readouterr()
        assert "All dependencies satisfied" in captured.out


class TestScanAndDisplayDeps:
    """Tests for _scan_and_display_deps function."""

    def test_non_interactive_skips_display(self):
        with patch("reincheck.tui.scan_dependencies") as mock_scan:
            mock_scan.return_value = {
                "npm": DependencyStatus(
                    name="npm",
                    available=True,
                    version="10.0.0",
                    path="/usr/bin/npm",
                    version_satisfied=True,
                ),
            }
            result = _scan_and_display_deps(non_interactive=True)
            assert result == mock_scan.return_value
            mock_scan.assert_called_once()

    def test_non_tty_skips_display(self):
        with patch("sys.stdout.isatty", return_value=False):
            with patch("reincheck.tui.scan_dependencies") as mock_scan:
                mock_scan.return_value = {
                    "npm": DependencyStatus(
                        name="npm",
                        available=True,
                        version="10.0.0",
                        path="/usr/bin/npm",
                        version_satisfied=True,
                    ),
                }
                result = _scan_and_display_deps()
                assert result == mock_scan.return_value
                mock_scan.assert_called_once()

    def test_returns_statuses_dict(self):
        with patch("sys.stdout.isatty", return_value=True):
            with patch("reincheck.tui.scan_dependencies") as mock_scan:
                with patch("reincheck.tui.display_dependency_table"):
                    mock_scan.return_value = {
                        "npm": DependencyStatus(
                            name="npm",
                            available=True,
                            version="10.0.0",
                            path="/usr/bin/npm",
                            version_satisfied=True,
                        ),
                    }
                    result = _scan_and_display_deps()
                    assert isinstance(result, dict)
                    assert "npm" in result

    def test_required_deps_passed_through(self):
        with patch("sys.stdout.isatty", return_value=True):
            with patch("reincheck.tui.scan_dependencies") as mock_scan:
                with patch("reincheck.tui.display_dependency_table") as mock_display:
                    mock_scan.return_value = {
                        "npm": DependencyStatus(
                            name="npm",
                            available=True,
                            version="10.0.0",
                            path="/usr/bin/npm",
                            version_satisfied=True,
                        ),
                        "brew": DependencyStatus(
                            name="brew",
                            available=False,
                            version=None,
                            path=None,
                            version_satisfied=True,
                        ),
                    }
                    _scan_and_display_deps(required_deps=["npm"], show_all=True)
                    mock_display.assert_called_once()
                    call_kwargs = mock_display.call_args[1]
                    assert call_kwargs["required_deps"] == ["npm"]
                    assert call_kwargs["show_all"] is True

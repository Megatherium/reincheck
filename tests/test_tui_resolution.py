import pytest
from unittest.mock import patch, MagicMock
from reincheck.tui import resolve_failed_harnesses_interactive
from reincheck.installer import Harness, InstallMethod, RiskLevel, DependencyReport


@pytest.fixture
def mock_methods_dict():
    return {
        "claude.mise_binary": InstallMethod(
            harness="claude",
            method_name="mise_binary",
            install="install",
            upgrade="",
            version="",
            check_latest="",
            dependencies=["mise"],
        ),
        "claude.homebrew": InstallMethod(
            harness="claude",
            method_name="homebrew",
            install="install",
            upgrade="",
            version="",
            check_latest="",
            dependencies=["brew"],
        ),
    }


@pytest.fixture
def mock_harnesses_data():
    return {
        "claude": Harness(name="claude", display_name="Claude", description="Claude")
    }


def test_resolve_failed_harnesses_returns_none_if_no_tty():
    with patch("sys.stdin.isatty", return_value=False):
        with pytest.raises(RuntimeError):
            resolve_failed_harnesses_interactive([], {}, {})


def test_resolve_failed_harnesses_skips_if_no_methods(mock_harnesses_data):
    with patch("sys.stdin.isatty", return_value=True):
        mock_q = MagicMock()
        with patch.dict("sys.modules", {"questionary": mock_q}):
            # harness 'foo' has no methods in empty dict
            result = resolve_failed_harnesses_interactive(
                ["foo"], {}, mock_harnesses_data
            )
            assert result == {}
            # We don't check mock_q calls because we don't know if it was even imported if we patched modules dict
            # But the result should be empty.


def test_resolve_failed_harnesses_selects_method(
    mock_methods_dict, mock_harnesses_data
):
    with patch("sys.stdin.isatty", return_value=True):
        mock_q = MagicMock()
        mock_q.select.return_value.ask.return_value = "mise_binary"

        with patch.dict("sys.modules", {"questionary": mock_q}):
            result = resolve_failed_harnesses_interactive(
                ["claude"], mock_methods_dict, mock_harnesses_data
            )

            assert result == {"claude": "mise_binary"}

            # Verify Choice calls
            choice_calls = mock_q.Choice.call_args_list
            values = [c.kwargs.get("value") for c in choice_calls]

            assert "mise_binary" in values
            assert "homebrew" in values
            assert None in values


def test_resolve_failed_harnesses_user_skips(mock_methods_dict, mock_harnesses_data):
    with patch("sys.stdin.isatty", return_value=True):
        mock_q = MagicMock()
        mock_q.select.return_value.ask.return_value = None

        with patch.dict("sys.modules", {"questionary": mock_q}):
            result = resolve_failed_harnesses_interactive(
                ["claude"], mock_methods_dict, mock_harnesses_data
            )

            assert result == {}


def test_resolve_failed_harnesses_with_missing_deps(
    mock_methods_dict, mock_harnesses_data
):
    report = MagicMock(spec=DependencyReport)
    report.missing_deps = ["brew"]

    with patch("sys.stdin.isatty", return_value=True):
        mock_q = MagicMock()
        mock_q.select.return_value.ask.return_value = "mise_binary"

        with patch.dict("sys.modules", {"questionary": mock_q}):
            resolve_failed_harnesses_interactive(
                ["claude"], mock_methods_dict, mock_harnesses_data, dep_report=report
            )

            # Check that homebrew choice was marked missing
            choice_calls = mock_q.Choice.call_args_list

            # Find the call for homebrew
            homebrew_call = next(
                c for c in choice_calls if c.kwargs.get("value") == "homebrew"
            )

            # The title should be a list of tokens with 'class:missing'
            title = homebrew_call.kwargs.get("title")
            assert isinstance(title, list)
            assert any(t[0] == "class:missing" for t in title)

            # Find the call for mise_binary
            mise_call = next(
                c for c in choice_calls if c.kwargs.get("value") == "mise_binary"
            )

            title = mise_call.kwargs.get("title")
            assert isinstance(title, list)
            assert any(t[0] == "class:available" for t in title)

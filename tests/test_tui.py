"""Tests for TUI utilities."""

from unittest.mock import patch

import pytest

from reincheck.installer import DependencyStatus, Preset, InstallMethod, RiskLevel
from reincheck.tui import (
    format_dep_line,
    get_color_for_status,
    display_dependency_table,
    _scan_and_display_deps,
    get_method_names_for_harness,
    select_harnesses_interactive,
    _format_harness_choice,
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


class TestFormatPresetChoice:
    """Tests for format_preset_choice function."""

    def test_green_status_formatting(self):
        from reincheck.installer import Preset, PresetStatus, DependencyReport
        from reincheck.tui import format_preset_choice

        preset = Preset(
            name="test_green",
            strategy="test",
            description="Test preset with all deps",
            methods={},
        )
        report = DependencyReport(
            all_deps={},
            preset_statuses={"test_green": PresetStatus.GREEN},
            missing_deps=[],
            unsatisfied_versions=[],
            available_count=5,
            total_count=5,
        )
        result = format_preset_choice(preset, PresetStatus.GREEN, report)
        assert "✅" in result
        assert "test_green" in result
        assert "all deps ready" not in result  # Green doesn't show status text in compact mode

    def test_partial_status_formatting(self):
        from reincheck.installer import Preset, PresetStatus, DependencyReport
        from reincheck.tui import format_preset_choice

        preset = Preset(
            name="test_partial",
            strategy="test",
            description="Test preset with partial deps",
            methods={"harness1": "method1"},
        )
        report = DependencyReport(
            all_deps={},
            preset_statuses={"test_partial": PresetStatus.PARTIAL},
            missing_deps=["dep1"],
            unsatisfied_versions=[],
            available_count=3,
            total_count=5,
        )
        result = format_preset_choice(preset, PresetStatus.PARTIAL, report)
        assert "⚠️" in result
        assert "test_partial" in result

    def test_red_status_formatting(self):
        from reincheck.installer import Preset, PresetStatus, DependencyReport
        from reincheck.tui import format_preset_choice

        preset = Preset(
            name="test_red",
            strategy="test",
            description="Test preset with missing deps",
            methods={},
        )
        report = DependencyReport(
            all_deps={},
            preset_statuses={"test_red": PresetStatus.RED},
            missing_deps=["dep1", "dep2"],
            unsatisfied_versions=[],
            available_count=0,
            total_count=5,
        )
        result = format_preset_choice(preset, PresetStatus.RED, report)
        assert "❌" in result
        assert "test_red" in result


class TestSelectPresetInteractive:
    """Tests for select_preset_interactive function."""

    def test_raises_error_without_tty(self):
        from reincheck.installer import Preset, PresetStatus, DependencyReport
        from reincheck.tui import select_preset_interactive

        preset = Preset(
            name="test",
            strategy="test",
            description="Test",
            methods={},
        )
        report = DependencyReport(
            all_deps={},
            preset_statuses={"test": PresetStatus.GREEN},
            missing_deps=[],
            unsatisfied_versions=[],
            available_count=1,
            total_count=1,
        )

        with pytest.raises(RuntimeError, match="requires a TTY"):
            select_preset_interactive({"test": preset}, report)

    def test_returns_none_for_empty_presets(self):
        from reincheck.installer import DependencyReport
        from reincheck.tui import select_preset_interactive

        report = DependencyReport(
            all_deps={},
            preset_statuses={},
            missing_deps=[],
            unsatisfied_versions=[],
            available_count=0,
            total_count=0,
        )

        with patch("sys.stdin.isatty", return_value=True):
            result = select_preset_interactive({}, report)
            assert result is None

    def test_returns_none_on_cancel(self):
        from reincheck.installer import Preset, PresetStatus, DependencyReport
        from reincheck.tui import select_preset_interactive

        preset = Preset(
            name="test",
            strategy="test",
            description="Test",
            methods={},
        )
        report = DependencyReport(
            all_deps={},
            preset_statuses={"test": PresetStatus.GREEN},
            missing_deps=[],
            unsatisfied_versions=[],
            available_count=1,
            total_count=1,
        )

        with patch("sys.stdin.isatty", return_value=True):
            with patch("questionary.select") as mock_select:
                mock_select.return_value.ask.return_value = None
                result = select_preset_interactive({"test": preset}, report)
                assert result is None

    def test_returns_selected_preset(self):
        from reincheck.installer import Preset, PresetStatus, DependencyReport
        from reincheck.tui import select_preset_interactive

        preset = Preset(
            name="mise_binary",
            strategy="mise",
            description="Use mise binaries",
            methods={},
        )
        report = DependencyReport(
            all_deps={},
            preset_statuses={"mise_binary": PresetStatus.GREEN},
            missing_deps=[],
            unsatisfied_versions=[],
            available_count=1,
            total_count=1,
        )

        with patch("sys.stdin.isatty", return_value=True):
            with patch("questionary.select") as mock_select:
                mock_select.return_value.ask.return_value = "mise_binary"
                result = select_preset_interactive({"mise_binary": preset}, report)
                assert result == "mise_binary"


def _make_method(harness: str, method_name: str) -> InstallMethod:
    return InstallMethod(
        harness=harness,
        method_name=method_name,
        install=f"install-{harness}-{method_name}",
        upgrade=f"upgrade-{harness}-{method_name}",
        version=f"version-{harness}",
        check_latest=f"check-{harness}",
        dependencies=[],
        risk_level=RiskLevel.SAFE,
    )


def _make_methods_dict() -> dict[str, InstallMethod]:
    return {
        "claude.mise_binary": _make_method("claude", "mise_binary"),
        "claude.homebrew": _make_method("claude", "homebrew"),
        "claude.language_native": _make_method("claude", "language_native"),
        "aider.homebrew": _make_method("aider", "homebrew"),
        "aider.language_native": _make_method("aider", "language_native"),
        "roo.vendor_recommended": _make_method("roo", "vendor_recommended"),
    }


def _make_harnesses() -> dict:
    from reincheck.installer import Harness

    return {
        "claude": Harness(name="claude", display_name="Claude", description="Claude Code"),
        "aider": Harness(name="aider", display_name="Aider", description="Aider"),
        "roo": Harness(name="roo", display_name="Roo", description="Roo"),
    }


class TestGetMethodNamesForHarness:

    def test_returns_sorted_methods(self):
        methods = _make_methods_dict()
        result = get_method_names_for_harness("claude", methods)
        assert result == ["homebrew", "language_native", "mise_binary"]

    def test_preset_default_first(self):
        methods = _make_methods_dict()
        result = get_method_names_for_harness("claude", methods, preset_default="mise_binary")
        assert result[0] == "mise_binary"
        assert set(result) == {"mise_binary", "homebrew", "language_native"}

    def test_unknown_harness_returns_empty(self):
        methods = _make_methods_dict()
        result = get_method_names_for_harness("nonexistent", methods)
        assert result == []

    def test_single_method_harness(self):
        methods = _make_methods_dict()
        result = get_method_names_for_harness("roo", methods)
        assert result == ["vendor_recommended"]

    def test_preset_default_not_in_methods_ignored(self):
        methods = _make_methods_dict()
        result = get_method_names_for_harness("claude", methods, preset_default="nonexistent")
        assert result == ["homebrew", "language_native", "mise_binary"]


class TestFormatHarnessChoice:

    def test_with_display_name_and_method(self):
        harnesses = _make_harnesses()
        result = _format_harness_choice("claude", harnesses, "mise_binary")
        assert "Claude" in result
        assert "mise_binary" in result

    def test_without_method(self):
        harnesses = _make_harnesses()
        result = _format_harness_choice("claude", harnesses)
        assert "Claude" in result
        assert "method" not in result

    def test_unknown_harness_uses_key(self):
        result = _format_harness_choice("unknown_thing", {}, "some_method")
        assert "unknown_thing" in result


class TestSelectHarnessesInteractive:

    def test_raises_without_tty(self):
        preset = Preset(
            name="test", strategy="test", description="Test",
            methods={"claude": "mise_binary"},
        )
        with pytest.raises(RuntimeError, match="requires a TTY"):
            select_harnesses_interactive(preset, {}, {})

    def test_empty_preset_returns_empty(self):
        preset = Preset(
            name="test", strategy="test", description="Test",
            methods={},
        )
        with patch("sys.stdin.isatty", return_value=True):
            result = select_harnesses_interactive(preset, _make_methods_dict(), _make_harnesses())
            assert result == ([], {})

    def test_returns_all_selected_no_overrides(self):
        preset = Preset(
            name="test", strategy="test", description="Test",
            methods={"claude": "mise_binary", "aider": "homebrew"},
        )
        methods = _make_methods_dict()
        harnesses = _make_harnesses()

        with patch("sys.stdin.isatty", return_value=True):
            with patch("questionary.checkbox") as mock_cb:
                mock_cb.return_value.ask.return_value = ["claude", "aider"]
                with patch("questionary.confirm") as mock_confirm:
                    mock_confirm.return_value.ask.return_value = False
                    result = select_harnesses_interactive(preset, methods, harnesses)

        assert result is not None
        selected, overrides = result
        assert set(selected) == {"claude", "aider"}
        assert overrides == {}

    def test_returns_none_on_cancel(self):
        preset = Preset(
            name="test", strategy="test", description="Test",
            methods={"claude": "mise_binary"},
        )
        with patch("sys.stdin.isatty", return_value=True):
            with patch("questionary.checkbox") as mock_cb:
                mock_cb.return_value.ask.return_value = None
                result = select_harnesses_interactive(preset, _make_methods_dict(), _make_harnesses())
                assert result is None

    def test_keyboard_interrupt_returns_none(self):
        preset = Preset(
            name="test", strategy="test", description="Test",
            methods={"claude": "mise_binary"},
        )
        with patch("sys.stdin.isatty", return_value=True):
            with patch("questionary.checkbox") as mock_cb:
                mock_cb.return_value.ask.side_effect = KeyboardInterrupt
                result = select_harnesses_interactive(preset, _make_methods_dict(), _make_harnesses())
                assert result is None

    def test_method_override_flow(self):
        preset = Preset(
            name="test", strategy="test", description="Test",
            methods={"claude": "mise_binary", "roo": "vendor_recommended"},
        )
        methods = _make_methods_dict()
        harnesses = _make_harnesses()

        with patch("sys.stdin.isatty", return_value=True):
            with patch("questionary.checkbox") as mock_cb:
                # First call: harness selection
                # Second call: which harnesses to customize
                mock_cb.return_value.ask.side_effect = [
                    ["claude", "roo"],
                    ["claude"],
                ]
                with patch("questionary.confirm") as mock_confirm:
                    mock_confirm.return_value.ask.return_value = True
                    with patch("questionary.select") as mock_select:
                        mock_select.return_value.ask.return_value = "homebrew"
                        result = select_harnesses_interactive(preset, methods, harnesses)

        assert result is not None
        selected, overrides = result
        assert set(selected) == {"claude", "roo"}
        assert overrides == {"claude": "homebrew"}

    def test_single_method_harness_not_offered_for_customization(self):
        preset = Preset(
            name="test", strategy="test", description="Test",
            methods={"roo": "vendor_recommended"},
        )
        methods = _make_methods_dict()
        harnesses = _make_harnesses()

        with patch("sys.stdin.isatty", return_value=True):
            with patch("questionary.checkbox") as mock_cb:
                mock_cb.return_value.ask.return_value = ["roo"]
                result = select_harnesses_interactive(preset, methods, harnesses)

        assert result is not None
        selected, overrides = result
        assert selected == ["roo"]
        assert overrides == {}

    def test_choosing_preset_default_not_added_to_overrides(self):
        preset = Preset(
            name="test", strategy="test", description="Test",
            methods={"claude": "mise_binary"},
        )
        methods = _make_methods_dict()
        harnesses = _make_harnesses()

        with patch("sys.stdin.isatty", return_value=True):
            with patch("questionary.checkbox") as mock_cb:
                mock_cb.return_value.ask.side_effect = [
                    ["claude"],
                    ["claude"],
                ]
                with patch("questionary.confirm") as mock_confirm:
                    mock_confirm.return_value.ask.return_value = True
                    with patch("questionary.select") as mock_select:
                        mock_select.return_value.ask.return_value = "mise_binary"
                        result = select_harnesses_interactive(preset, methods, harnesses)

        assert result is not None
        _, overrides = result
        assert overrides == {}

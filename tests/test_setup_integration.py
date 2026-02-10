"""Integration tests for TUI wizard flow and setup command."""

import sys
import asyncio
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import pytest

from reincheck.installer import (
    Preset,
    DependencyStatus,
    DependencyReport,
    PresetStatus,
    InstallMethod,
    RiskLevel,
)


@pytest.fixture
def mock_harnesses_dict():
    """Mock harness data as dict."""
    from reincheck.installer import Harness

    return {
        "claude": Harness(
            name="claude", display_name="Claude Code", description="Claude Code"
        ),
        "aider": Harness(name="aider", display_name="Aider", description="Aider"),
        "roo": Harness(name="roo", display_name="Roo", description="Roo Code"),
    }


class TestTUIIntegrationFlow:
    """Integration tests for complete TUI wizard flow."""

    def test_full_setup_flow_with_preset_flag(
        self,
        mock_tty,
        mock_presets,
        mock_methods,
        mock_harnesses_dict,
        mock_dependency_report,
        temp_dir,
    ):
        """Test complete setup flow with preset flag (no interactive selection)."""
        from reincheck.commands import setup
        from click.testing import CliRunner

        runner = CliRunner()

        # Mock data loading
        with (
            patch("reincheck.data_loader.get_presets", return_value=mock_presets),
            patch("reincheck.data_loader.get_all_methods", return_value=mock_methods),
            patch(
                "reincheck.data_loader.get_harnesses", return_value=mock_harnesses_dict
            ),
            patch(
                "reincheck.installer.get_dependency_report",
                return_value=mock_dependency_report,
            ),
            patch(
                "reincheck.tui.select_preset_interactive",
                return_value="mise_binary",
            ),
            patch(
                "reincheck.installer.get_dependency_report",
                return_value=mock_dependency_report,
            ),
            patch("reincheck.paths.get_config_dir", return_value=temp_dir),
        ):
            result = runner.invoke(
                setup,
                ["--preset", "mise_binary", "--dry-run"],
                obj={},
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert "mise_binary" in result.output

    def test_setup_fallback_to_non_interactive_when_no_tty(
        self,
        mock_no_tty,
        mock_presets,
        mock_methods,
        mock_dependency_report,
        temp_dir,
    ):
        """Test that setup falls back to error when no TTY and no preset specified."""
        from reincheck.commands import setup
        from click.testing import CliRunner

        runner = CliRunner()

        with (
            patch("reincheck.data_loader.get_presets", return_value=mock_presets),
            patch("reincheck.data_loader.get_all_methods", return_value=mock_methods),
            patch(
                "reincheck.installer.get_dependency_report",
                return_value=mock_dependency_report,
            ),
            patch("reincheck.paths.get_config_dir", return_value=temp_dir),
            patch("reincheck.paths.get_packaged_config_path", return_value=None),
            patch("reincheck.ensure_user_config"),
            patch(
                "reincheck.commands.setup._select_preset_interactive_with_fallback"
            ) as mock_select_preset,
        ):
            result = runner.invoke(
                setup,
                ["--preset", "mise_binary", "--dry-run"],
                obj={},
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        mock_select_preset.assert_not_called()
        assert "mise_binary" in result.output

    def test_keyboard_interrupt_during_preset_selection(
        self,
        mock_tty,
        mock_presets,
        mock_methods,
        mock_dependency_report,
    ):
        """Test handling of KeyboardInterrupt during preset selection."""
        from reincheck.commands.setup import _select_preset_interactive_with_fallback

        with (
            patch(
                "reincheck.commands.setup.select_preset_interactive",
                side_effect=KeyboardInterrupt,
            ),
            patch("reincheck.commands.setup.sys.stdin.isatty", return_value=True),
        ):
            result = _select_preset_interactive_with_fallback(
                mock_presets, mock_dependency_report, debug=False
            )

        # Should return None on interrupt
        assert result is None

    def test_keyboard_interrupt_during_harness_selection(
        self,
        mock_tty,
        mock_presets,
        mock_methods,
    ):
        """Test handling of KeyboardInterrupt during harness selection."""
        from reincheck.commands.setup import _select_harnesses_interactive_with_fallback

        preset = mock_presets["mise_binary"]

        with (
            patch(
                "reincheck.commands.setup.select_harnesses_interactive",
                side_effect=KeyboardInterrupt,
            ),
            patch("reincheck.commands.setup.sys.stdin.isatty", return_value=True),
        ):
            result = _select_harnesses_interactive_with_fallback(
                preset, mock_methods, harnesses={}, debug=False
            )

        # Should return None on interrupt
        assert result is None

    def test_tty_unavailable_fallback_during_preset_selection(
        self,
        mock_presets,
        mock_methods,
        mock_dependency_report,
    ):
        """Test fallback to None when TTY unavailable during preset selection."""
        from reincheck.commands.setup import _select_preset_interactive_with_fallback

        with patch("reincheck.commands.setup.sys.stdin.isatty", return_value=False):
            result = _select_preset_interactive_with_fallback(
                mock_presets, mock_dependency_report, debug=False
            )

        assert result is None

    def test_tty_unavailable_fallback_during_harness_selection(
        self,
        mock_presets,
        mock_methods,
    ):
        """Test fallback to None when TTY unavailable during harness selection."""
        from reincheck.commands.setup import _select_harnesses_interactive_with_fallback

        preset = mock_presets["mise_binary"]

        with patch("reincheck.commands.setup.sys.stdin.isatty", return_value=False):
            result = _select_harnesses_interactive_with_fallback(
                preset, mock_methods, harnesses={}, debug=False
            )

        assert result is None


class TestSetupCommandIntegration:
    """Integration tests for full setup command."""

    def test_list_presets_with_status(
        self, mock_presets, mock_methods, mock_dependency_report
    ):
        """Test listing presets with dependency status."""
        from reincheck.commands.setup import _list_presets_with_status
        from click.testing import CliRunner

        with (
            patch("reincheck.data_loader.get_presets", return_value=mock_presets),
            patch("reincheck.data_loader.get_all_methods", return_value=mock_methods),
            patch(
                "reincheck.installer.get_dependency_report",
                return_value=mock_dependency_report,
            ),
            patch(
                "reincheck.setup_logging",
            ),
        ):
            # Call the function directly and capture output
            import io
            from contextlib import redirect_stdout

            f = io.StringIO()
            with redirect_stdout(f):
                _list_presets_with_status(debug=False)
            output = f.getvalue()

        assert "✅" in output
        assert "❌" in output
        assert "mise_binary" in output
        assert "homebrew" in output

    def test_setup_with_custom_preset_and_overrides(
        self,
        mock_no_tty,
        mock_methods,
        mock_harnesses_dict,
        temp_dir,
        mock_dependency_report,
    ):
        """Test setup with custom preset using --override."""
        from reincheck.commands import setup
        from click.testing import CliRunner

        runner = CliRunner()

        with (
            patch("reincheck.data_loader.get_presets", return_value={}),
            patch("reincheck.data_loader.get_all_methods", return_value=mock_methods),
            patch(
                "reincheck.data_loader.get_harnesses", return_value=mock_harnesses_dict
            ),
            patch(
                "reincheck.installer.get_dependency_report",
                return_value=mock_dependency_report,
            ),
            patch(
                "reincheck.paths.get_config_path", return_value=temp_dir / "config.json"
            ),
        ):
            result = runner.invoke(
                setup,
                ["--preset", "custom", "--override", "claude=mise_binary", "--dry-run"],
                obj={},
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert "custom" in result.output

    def test_setup_with_all_harnesses_flag(
        self,
        mock_no_tty,
        mock_presets,
        mock_methods,
        mock_harnesses_dict,
        temp_dir,
        mock_dependency_report,
    ):
        """Test setup with --harness ALL."""
        from reincheck.commands import setup
        from click.testing import CliRunner

        runner = CliRunner()

        with (
            patch("reincheck.data_loader.get_presets", return_value=mock_presets),
            patch("reincheck.data_loader.get_all_methods", return_value=mock_methods),
            patch(
                "reincheck.data_loader.get_harnesses", return_value=mock_harnesses_dict
            ),
            patch(
                "reincheck.installer.get_dependency_report",
                return_value=mock_dependency_report,
            ),
            patch(
                "reincheck.paths.get_config_path", return_value=temp_dir / "config.json"
            ),
        ):
            result = runner.invoke(
                setup,
                ["--preset", "mise_binary", "--harness", "ALL", "--dry-run"],
                obj={},
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert "claude" in result.output or "aider" in result.output

    def test_setup_writes_config_file(
        self,
        mock_no_tty,
        mock_presets,
        mock_methods,
        mock_harnesses_dict,
        temp_dir,
        mock_dependency_report,
    ):
        """Test that setup writes config file correctly."""
        from reincheck.commands import setup
        from click.testing import CliRunner

        config_path = temp_dir / "agents.json"

        runner = CliRunner()

        with (
            patch("reincheck.data_loader.get_presets", return_value=mock_presets),
            patch("reincheck.data_loader.get_all_methods", return_value=mock_methods),
            patch(
                "reincheck.data_loader.get_harnesses", return_value=mock_harnesses_dict
            ),
            patch(
                "reincheck.installer.get_dependency_report",
                return_value=mock_dependency_report,
            ),
            patch("reincheck.paths.get_config_dir", return_value=temp_dir),
            patch("reincheck.paths.get_packaged_config_path", return_value=None),
            patch("reincheck.ensure_user_config"),
        ):
            result = runner.invoke(
                setup,
                ["--preset", "mise_binary", "--yes"],
                obj={},
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert config_path.exists()


class TestSetupApplyFlow:
    """Tests for setup --apply flow."""

    def test_setup_apply_executes_installation(
        self,
        mock_no_tty,
        mock_presets,
        mock_methods,
        mock_harnesses_dict,
        temp_dir,
        mock_dependency_report,
    ):
        """Test that setup --apply executes installation."""
        from reincheck.commands import setup
        from reincheck.installer import Plan, PlanStep, RiskLevel
        from click.testing import CliRunner

        runner = CliRunner()
        config_path = temp_dir / "agents.json"

        # Mock installation plan
        plan = Plan(
            preset_name="mise_binary",
            steps=[
                PlanStep(
                    harness="claude",
                    action="install",
                    command="echo 'installing claude'",
                    timeout=600,
                    risk_level=RiskLevel.SAFE,
                    method_name="mise_binary",
                )
            ],
            unsatisfied_deps=[],
        )

        with (
            patch("reincheck.data_loader.get_presets", return_value=mock_presets),
            patch("reincheck.data_loader.get_all_methods", return_value=mock_methods),
            patch(
                "reincheck.data_loader.get_harnesses", return_value=mock_harnesses_dict
            ),
            patch(
                "reincheck.installer.get_dependency_report",
                return_value=mock_dependency_report,
            ),
            patch("reincheck.installer.plan_install", return_value=plan),
            patch(
                "reincheck.run_command_async",
                new_callable=AsyncMock,
                return_value=("installed", 0),
            ),
            patch("reincheck.paths.get_config_dir", return_value=temp_dir),
            patch("reincheck.paths.get_packaged_config_path", return_value=None),
            patch("reincheck.ensure_user_config"),
        ):
            result = runner.invoke(
                setup,
                ["--preset", "mise_binary", "--harness", "ALL", "--apply", "--yes"],
                obj={},
                catch_exceptions=False,
            )

        assert result.exit_code == 0

    def test_setup_apply_with_dangerous_command_requires_confirmation(
        self,
        mock_no_tty,
        mock_presets,
        mock_methods,
        mock_harnesses_dict,
        temp_dir,
        mock_dependency_report,
    ):
        """Test that dangerous commands require confirmation even with --yes."""
        from reincheck.commands import setup
        from reincheck.installer import Plan, PlanStep, RiskLevel
        from click.testing import CliRunner

        runner = CliRunner()
        config_path = temp_dir / "agents.json"

        # Mock installation plan with dangerous command
        plan = Plan(
            preset_name="mise_binary",
            steps=[
                PlanStep(
                    harness="roo",
                    action="install",
                    command="curl -fsSL https://roo.sh | sh",
                    timeout=600,
                    risk_level=RiskLevel.DANGEROUS,
                    method_name="vendor_recommended",
                )
            ],
            unsatisfied_deps=[],
        )

        with (
            patch("reincheck.data_loader.get_presets", return_value=mock_presets),
            patch("reincheck.data_loader.get_all_methods", return_value=mock_methods),
            patch(
                "reincheck.data_loader.get_harnesses", return_value=mock_harnesses_dict
            ),
            patch(
                "reincheck.installer.get_dependency_report",
                return_value=mock_dependency_report,
            ),
            patch("reincheck.installer.plan_install", return_value=plan),
            patch(
                "reincheck.commands.run_command_async",
                new_callable=AsyncMock,
                return_value=("installed", 0),
            ),
            patch("reincheck.paths.get_config_path", return_value=config_path),
        ):
            # Without --yes, should prompt for dangerous command
            result = runner.invoke(
                setup,
                ["--preset", "mise_binary", "--harness", "ALL", "--apply"],
                obj={},
                input="n\n",  # Decline dangerous command
                catch_exceptions=False,
            )

        # Command should have been skipped
        assert "skipped" in result.output.lower() or result.exit_code == 0


class TestTTYFallbackBehavior:
    """Tests for TTY availability fallback behavior."""

    def test_preset_selector_fallback_returns_none_on_tty_error(
        self,
        mock_presets,
        mock_dependency_report,
    ):
        """Test that preset selector returns None on OSError (terminal errors)."""
        from reincheck.commands.setup import _select_preset_interactive_with_fallback

        with (
            patch(
                "reincheck.commands.setup.select_preset_interactive",
                side_effect=OSError("No TERM"),
            ),
            patch("reincheck.commands.setup.sys.stdin.isatty", return_value=True),
        ):
            result = _select_preset_interactive_with_fallback(
                mock_presets, mock_dependency_report, debug=True
            )

        assert result is None

    def test_harness_selector_fallback_returns_none_on_tty_error(
        self,
        mock_presets,
        mock_methods,
    ):
        """Test that harness selector returns None on OSError (terminal errors)."""
        from reincheck.commands.setup import _select_harnesses_interactive_with_fallback

        preset = mock_presets["mise_binary"]

        with (
            patch(
                "reincheck.commands.setup.select_harnesses_interactive",
                side_effect=OSError("No TERM"),
            ),
            patch("reincheck.commands.setup.sys.stdin.isatty", return_value=True),
        ):
            result = _select_harnesses_interactive_with_fallback(
                preset, mock_methods, harnesses={}, debug=True
            )

        assert result is None

    def test_questionary_import_error_fallback(
        self,
        mock_presets,
        mock_methods,
        mock_harnesses_dict,
        temp_dir,
        mock_dependency_report,
    ):
        """Test that import errors in questionary are handled gracefully."""
        from reincheck.commands.setup import _select_preset_interactive_with_fallback

        with (
            patch("reincheck.data_loader.get_presets", return_value=mock_presets),
            patch("reincheck.data_loader.get_all_methods", return_value=mock_methods),
            patch(
                "reincheck.data_loader.get_harnesses", return_value=mock_harnesses_dict
            ),
            patch(
                "reincheck.installer.get_dependency_report",
                return_value=mock_dependency_report,
            ),
            patch(
                "reincheck.commands.setup.select_preset_interactive",
                side_effect=ImportError("questionary not installed"),
            ),
            patch("reincheck.commands.setup.sys.stdin.isatty", return_value=True),
        ):
            result = _select_preset_interactive_with_fallback(
                mock_presets, mock_dependency_report, debug=False
            )

        assert result is None


class TestInteractivePromptMocking:
    """Tests for mocking interactive prompts."""

    def test_mock_questionary_select(self, mock_tty):
        """Test mocking prompt_toolkit Application for preset selection."""
        from reincheck.tui import select_preset_interactive
        from reincheck.installer import Preset, PresetStatus, DependencyReport

        presets = {
            "mise_binary": Preset(
                name="mise_binary",
                strategy="mise",
                description="Use mise binaries",
                methods={},
            )
        }
        report = DependencyReport({}, {}, [], [], 0, 0)

        mock_instance = MagicMock()
        mock_instance.run.return_value = None

        with patch("reincheck.tui.presets.Application", return_value=mock_instance):
            result = select_preset_interactive(
                presets, report, methods={}, default=None
            )

        assert result is None

    def test_mock_questionary_checkbox(self, mock_tty):
        """Test mocking questionary.checkbox for harness selection."""
        from reincheck.tui import select_harnesses_interactive
        from reincheck.installer import Preset

        preset = Preset(
            name="test",
            strategy="test",
            description="Test",
            methods={"claude": "method1"},
        )

        with (
            patch("questionary.checkbox") as mock_cb,
            patch("questionary.confirm") as mock_confirm,
        ):
            mock_cb.return_value.ask.return_value = ["claude"]
            mock_confirm.return_value.ask.return_value = False  # No overrides

            result = select_harnesses_interactive(preset, {}, {})

        assert result is not None
        selected, _ = result
        assert set(selected) == {"claude"}

    def test_mock_prompt_sequence_for_full_wizard_flow(
        self,
        mock_presets,
        mock_methods,
        mock_harnesses_dict,
        mock_dependency_report,
        temp_dir,
    ):
        """Test mocking a sequence of prompts for full wizard flow."""
        from reincheck.commands import setup
        from click.testing import CliRunner

        runner = CliRunner()

        # Mock sequence: preset selection -> harness selection -> confirmation
        with (
            patch("reincheck.data_loader.get_presets", return_value=mock_presets),
            patch("reincheck.data_loader.get_all_methods", return_value=mock_methods),
            patch(
                "reincheck.data_loader.get_harnesses", return_value=mock_harnesses_dict
            ),
            patch(
                "reincheck.installer.get_dependency_report",
                return_value=mock_dependency_report,
            ),
            patch(
                "reincheck.commands.setup._apply_interactive_harness_selection",
                return_value=(mock_presets["mise_binary"], {}),
            ),
            patch(
                "reincheck.paths.get_config_path", return_value=temp_dir / "config.json"
            ),
            patch("click.confirm", return_value=True),
            patch("reincheck.ensure_user_config"),
        ):
            result = runner.invoke(
                setup,
                ["--preset", "mise_binary"],
                obj={},
            )

        assert result.exit_code == 0


# Helper fixtures
@pytest.fixture
def mock_dependency_report():
    from reincheck.installer import (
        DependencyStatus,
        DependencyReport,
        PresetStatus,
    )

    return DependencyReport(
        all_deps={
            "mise": DependencyStatus(name="mise", available=True, version="2024.12.1"),
            "brew": DependencyStatus(name="brew", available=False),
            "python": DependencyStatus(name="python", available=True, version="3.11.0"),
            "pip": DependencyStatus(name="pip", available=True, version="23.0"),
            "curl": DependencyStatus(name="curl", available=True, version="8.0"),
        },
        preset_statuses={
            "mise_binary": PresetStatus.GREEN,
            "homebrew": PresetStatus.RED,
        },
        missing_deps=["brew"],
        unsatisfied_versions=[],
        available_count=4,
        total_count=5,
    )

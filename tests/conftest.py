"""Pytest fixtures and utilities for reincheck tests."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from typing import Generator

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config_dir(temp_dir: Path) -> Generator[Path, None, None]:
    """Create a mock config directory."""
    config_dir = temp_dir / ".config" / "reincheck"
    config_dir.mkdir(parents=True, exist_ok=True)
    yield config_dir


@pytest.fixture
def mock_harnesses() -> dict:
    """Mock harness data."""
    return {
        "claude": {
            "name": "claude",
            "display_name": "Claude Code",
            "description": "Claude Code",
        },
        "aider": {"name": "aider", "display_name": "Aider", "description": "Aider"},
        "roo": {"name": "roo", "display_name": "Roo", "description": "Roo Code"},
    }


@pytest.fixture
def mock_methods() -> dict:
    """Mock install methods."""
    from reincheck.installer import InstallMethod, RiskLevel

    return {
        "claude.mise_binary": InstallMethod(
            harness="claude",
            method_name="mise_binary",
            install="mise use -g claude-code@latest",
            upgrade="mise use -g claude-code@latest",
            version="claude --version",
            check_latest="npm info @anthropic-ai/claude-code version",
            dependencies=["mise"],
            risk_level=RiskLevel.SAFE,
        ),
        "claude.homebrew": InstallMethod(
            harness="claude",
            method_name="homebrew",
            install="brew install claude-code",
            upgrade="brew upgrade claude-code",
            version="claude --version",
            check_latest="brew info claude-code --json",
            dependencies=["brew"],
            risk_level=RiskLevel.SAFE,
        ),
        "aider.language_native": InstallMethod(
            harness="aider",
            method_name="language_native",
            install="pip install aider-chat",
            upgrade="pip install --upgrade aider-chat",
            version="aider --version",
            check_latest="pip index versions aider-chat",
            dependencies=["python", "pip"],
            risk_level=RiskLevel.SAFE,
        ),
        "roo.vendor_recommended": InstallMethod(
            harness="roo",
            method_name="vendor_recommended",
            install="curl -fsSL https://roo.sh | sh",
            upgrade="curl -fsSL https://roo.sh | sh",
            version="roo --version",
            check_latest="curl -fsSL https://roo.sh | grep VER=",
            dependencies=["curl"],
            risk_level=RiskLevel.DANGEROUS,
        ),
    }


@pytest.fixture
def mock_presets() -> dict:
    """Mock preset data."""
    from reincheck.installer import Preset

    return {
        "mise_binary": Preset(
            name="mise_binary",
            strategy="mise",
            description="Use mise for binary installations",
            methods={"claude": "mise_binary", "aider": "language_native"},
            fallback_strategy="recommended",
            priority=1,
        ),
        "homebrew": Preset(
            name="homebrew",
            strategy="homebrew",
            description="Use Homebrew for macOS installations",
            methods={"claude": "homebrew", "aider": "language_native"},
            fallback_strategy="recommended",
            priority=2,
        ),
    }


@pytest.fixture
def mock_dependency_report() -> object:
    """Mock dependency report."""
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


@pytest.fixture
def mock_tty() -> Generator[None, None, None]:
    """Mock sys.stdin.isatty to return True."""
    with patch("sys.stdin.isatty", return_value=True):
        yield


@pytest.fixture
def mock_no_tty() -> Generator[None, None, None]:
    """Mock sys.stdin.isatty to return False."""
    with patch("sys.stdin.isatty", return_value=False):
        yield


@pytest.fixture
def mock_stdout_tty() -> Generator[None, None, None]:
    """Mock sys.stdout.isatty to return True."""
    with patch("sys.stdout.isatty", return_value=True):
        yield


@pytest.fixture
def mock_no_stdout_tty() -> Generator[None, None, None]:
    """Mock sys.stdout.isatty to return False."""
    with patch("sys.stdout.isatty", return_value=False):
        yield


class MockApplication:
    """Mock prompt_toolkit Application for testing."""

    def __init__(self, result=None):
        self.result = result
        self.layout = MagicMock()

    def run(self):
        return self.result


@pytest.fixture
def mock_tui_app():
    """Factory for creating mock TUI applications."""

    def _create(result=None):
        return MockApplication(result=result)

    return _create

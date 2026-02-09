"""Data models for installation system."""

from dataclasses import dataclass, field
from typing import Any

from .dependencies import RiskLevel


@dataclass
class Harness:
    name: str
    display_name: str
    description: str
    github_repo: str | None = None
    release_notes_url: str | None = None


@dataclass
class InstallMethod:
    harness: str
    method_name: str
    install: str
    upgrade: str
    version: str
    check_latest: str
    dependencies: list[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.SAFE


@dataclass
class Preset:
    name: str
    strategy: str
    description: str
    methods: dict[str, str]
    fallback_strategy: str | None = None
    priority: int = 999


@dataclass
class PlanStep:
    harness: str
    action: str
    command: str
    timeout: int
    risk_level: RiskLevel
    method_name: str
    dependencies: list[str] = field(default_factory=list)


@dataclass
class Plan:
    preset_name: str
    steps: list[PlanStep]
    unsatisfied_deps: list[str] = field(default_factory=list)
    risky_steps: list[str] = field(default_factory=list)

    def is_ready(self) -> bool:
        return len(self.unsatisfied_deps) == 0


@dataclass
class StepResult:
    harness: str
    status: str
    output: str


@dataclass
class DependencyReport:
    all_deps: dict[str, Any]
    preset_statuses: dict[str, Any]
    missing_deps: list[str]
    unsatisfied_versions: list[str]
    available_count: int
    total_count: int

    @property
    def overall_ready(self) -> bool:
        return self.available_count == self.total_count


__all__ = [
    "Harness",
    "InstallMethod",
    "Preset",
    "PlanStep",
    "Plan",
    "StepResult",
    "DependencyReport",
]

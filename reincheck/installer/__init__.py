"""Installer engine for harness setup and management."""

from .dependencies import (
    Dependency,
    DependencyStatus,
    PresetStatus,
    RiskLevel,
    get_all_dependencies,
    get_dependency,
    scan_dependencies,
)
from .installation import apply_plan, confirm_installation
from .models import (
    DependencyReport,
    Harness,
    InstallMethod,
    Plan,
    PlanStep,
    Preset,
    StepResult,
)
from .planning import plan_install, render_plan
from .resolution import (
    compute_preset_status,
    get_dependency_report,
    resolve_method,
)

__all__ = [
    "RiskLevel",
    "PresetStatus",
    "Dependency",
    "DependencyStatus",
    "DependencyReport",
    "Harness",
    "InstallMethod",
    "Preset",
    "PlanStep",
    "Plan",
    "StepResult",
    "get_all_dependencies",
    "get_dependency",
    "scan_dependencies",
    "compute_preset_status",
    "get_dependency_report",
    "resolve_method",
    "plan_install",
    "render_plan",
    "confirm_installation",
    "apply_plan",
]

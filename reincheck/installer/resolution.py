"""Method resolution and preset status computation."""

from typing import Any

from .dependencies import (
    DependencyStatus,
    PresetStatus,
    _infer_risk_level,
    scan_dependencies,
)
from .models import DependencyReport, InstallMethod, Preset


def resolve_method(
    preset: Preset,
    harness_name: str,
    methods: dict[str, InstallMethod],
    overrides: dict[str, Any] | None = None,
) -> InstallMethod:
    overrides = overrides or {}
    harness_override = overrides.get(harness_name)

    if isinstance(harness_override, dict):
        custom_override = harness_override

        base_method_name = custom_override.get("method") or preset.methods.get(
            harness_name
        )
        base_method = (
            methods.get(f"{harness_name}.{base_method_name}")
            if base_method_name
            else None
        )

        if "commands" in custom_override:
            cmds = custom_override["commands"]
            return InstallMethod(
                harness=harness_name,
                method_name="custom",
                install=cmds.get("install")
                or (base_method.install if base_method else ""),
                upgrade=cmds.get("upgrade")
                or (base_method.upgrade if base_method else ""),
                version=cmds.get("version")
                or (base_method.version if base_method else ""),
                check_latest=cmds.get("check_latest")
                or (base_method.check_latest if base_method else ""),
                dependencies=base_method.dependencies if base_method else [],
                risk_level=_infer_risk_level(cmds.get("install", "")),
            )
        elif base_method:
            return base_method

    if harness_override and isinstance(harness_override, str):
        method_key = f"{harness_name}.{harness_override}"
        method = methods.get(method_key)
        if method:
            return method

    preset_method_name = preset.methods.get(harness_name)
    if preset_method_name:
        method_key = f"{harness_name}.{preset_method_name}"
        method = methods.get(method_key)
        if method:
            return method

    if preset.fallback_strategy:
        fallback_key = f"{harness_name}.{preset.fallback_strategy}"
        method = methods.get(fallback_key)
        if method:
            return method

    raise ValueError(
        f"No valid install method found for {harness_name} in preset {preset.name}"
    )


def compute_preset_status(
    preset: Preset,
    methods: dict[str, InstallMethod],
    dep_map: dict[str, DependencyStatus],
) -> PresetStatus:
    all_deps = set()

    for harness_name, method_name in preset.methods.items():
        method_key = f"{harness_name}.{method_name}"
        method = methods.get(method_key)
        if method:
            all_deps.update(method.dependencies)

    if not all_deps:
        return PresetStatus.GREEN

    satisfied_count = 0
    for dep_name in all_deps:
        status = dep_map.get(dep_name)
        if status and status.available and status.version_satisfied:
            satisfied_count += 1

    if satisfied_count == len(all_deps):
        return PresetStatus.GREEN
    elif satisfied_count > 0:
        return PresetStatus.PARTIAL
    else:
        return PresetStatus.RED


def get_dependency_report(
    presets: dict[str, Preset],
    methods: dict[str, InstallMethod],
    dep_map: dict[str, DependencyStatus] | None = None,
) -> DependencyReport:
    if dep_map is None:
        dep_map = scan_dependencies()

    preset_statuses = {}
    for preset_name, preset in presets.items():
        status = compute_preset_status(preset, methods, dep_map)
        preset_statuses[preset_name] = status

    missing_deps = []
    unsatisfied_versions = []

    for name, status in dep_map.items():
        if not status.available:
            missing_deps.append(name)
        elif not status.version_satisfied:
            unsatisfied_versions.append(name)

    available_count = sum(
        1 for s in dep_map.values() if s.available and s.version_satisfied
    )

    return DependencyReport(
        all_deps=dep_map,
        preset_statuses=preset_statuses,
        missing_deps=missing_deps,
        unsatisfied_versions=unsatisfied_versions,
        available_count=available_count,
        total_count=len(dep_map),
    )


__all__ = [
    "resolve_method",
    "compute_preset_status",
    "get_dependency_report",
]

"""Data loader for harness configuration files."""

from pathlib import Path

from reincheck.config import ConfigError, load_config
from reincheck.installer import (
    Dependency,
    Harness,
    InstallMethod,
    Preset,
    RiskLevel,
)


# Module-level caches
_harnesses_cache: dict[str, Harness] | None = None
_dependencies_cache: dict[str, Dependency] | None = None
_presets_cache: dict[str, Preset] | None = None
_methods_cache: dict[str, InstallMethod] | None = None


def _get_data_dir() -> Path:
    """Get path to bundled data directory."""
    return Path(__file__).parent / "data"


def _load_json_file(path: Path) -> dict:
    """Load and parse a JSON file with error handling.

    Args:
        path: Path to JSON file

    Returns:
        Parsed dict

    Raises:
        ConfigError: If file cannot be read or contains invalid JSON
    """
    if not path.exists():
        raise ConfigError(f"Data file not found: {path}")

    if not path.is_file():
        raise ConfigError(f"Data path is not a file: {path}")

    try:
        return load_config(path)
    except ConfigError as e:
        # Re-raise with more context
        raise ConfigError(f"Failed to load data file {path}: {e}") from e


def _validate_harness_data(data: dict, harness_name: str) -> None:
    """Validate harness data before creating Harness instance.

    Args:
        data: Raw dict for a single harness
        harness_name: Name of the harness for error messages

    Raises:
        ConfigError: If validation fails
    """
    required_fields = ["name", "display_name", "description"]

    for field in required_fields:
        if field not in data:
            raise ConfigError(
                f"Harness '{harness_name}' missing required field: {field}"
            )
        if not isinstance(data[field], str) or not data[field].strip():
            raise ConfigError(
                f"Harness '{harness_name}' field '{field}' must be a non-empty string"
            )

    # Optional fields should be strings if present
    for field in ["github_repo", "release_notes_url", "binary"]:
        if field in data and data[field] is not None:
            if not isinstance(data[field], str):
                raise ConfigError(
                    f"Harness '{harness_name}' field '{field}' must be a string or null"
                )


def _validate_dependency_data(data: dict, dep_name: str) -> None:
    """Validate dependency data before creating Dependency instance.

    Args:
        data: Raw dict for a single dependency
        dep_name: Name of the dependency for error messages

    Raises:
        ConfigError: If validation fails
    """
    required_fields = ["name", "check_command", "install_hint"]

    for field in required_fields:
        if field not in data:
            raise ConfigError(
                f"Dependency '{dep_name}' missing required field: {field}"
            )
        if not isinstance(data[field], str) or not data[field].strip():
            raise ConfigError(
                f"Dependency '{dep_name}' field '{field}' must be a non-empty string"
            )

    # Optional fields
    optional_fields = ["version_command", "min_version", "max_version"]
    for field in optional_fields:
        if field in data and data[field] is not None:
            if not isinstance(data[field], str):
                raise ConfigError(
                    f"Dependency '{dep_name}' field '{field}' must be a string or null"
                )


def _validate_preset_data(data: dict, preset_name: str) -> None:
    """Validate preset data before creating Preset instance.

    Args:
        data: Raw dict for a single preset
        preset_name: Name of the preset for error messages

    Raises:
        ConfigError: If validation fails
    """
    # Note: 'name' is derived from the dict key, not a field in the data
    required_fields = ["strategy", "description", "methods"]

    for field in required_fields:
        if field not in data:
            raise ConfigError(f"Preset '{preset_name}' missing required field: {field}")

    if not isinstance(data["strategy"], str) or not data["strategy"].strip():
        raise ConfigError(
            f"Preset '{preset_name}' field 'strategy' must be a non-empty string"
        )

    if not isinstance(data["description"], str) or not data["description"].strip():
        raise ConfigError(
            f"Preset '{preset_name}' field 'description' must be a non-empty string"
        )

    if not isinstance(data["methods"], dict):
        raise ConfigError(f"Preset '{preset_name}' field 'methods' must be an object")

    if "priority" in data and data["priority"] is not None:
        if not isinstance(data["priority"], int):
            raise ConfigError(
                f"Preset '{preset_name}' field 'priority' must be an integer or null"
            )

    # Validate fallback_strategy if present
    if "fallback_strategy" in data and data["fallback_strategy"] is not None:
        if not isinstance(data["fallback_strategy"], str):
            raise ConfigError(
                f"Preset '{preset_name}' field 'fallback_strategy' must be a string or null"
            )

    if not isinstance(data["strategy"], str) or not data["strategy"].strip():
        raise ConfigError(
            f"Preset '{preset_name}' field 'strategy' must be a non-empty string"
        )

    if not isinstance(data["description"], str) or not data["description"].strip():
        raise ConfigError(
            f"Preset '{preset_name}' field 'description' must be a non-empty string"
        )

    if not isinstance(data["methods"], dict):
        raise ConfigError(f"Preset '{preset_name}' field 'methods' must be an object")

    # Validate fallback_strategy if present
    if "fallback_strategy" in data and data["fallback_strategy"] is not None:
        if not isinstance(data["fallback_strategy"], str):
            raise ConfigError(
                f"Preset '{preset_name}' field 'fallback_strategy' must be a string or null"
            )


def _validate_method_data(data: dict, method_key: str) -> None:
    """Validate install method data before creating InstallMethod instance.

    Args:
        data: Raw dict for a single method
        method_key: Key for this method (e.g., "claude.mise_binary")

    Raises:
        ConfigError: If validation fails
    """
    required_fields = ["install", "upgrade", "version", "check_latest", "risk_level"]

    for field in required_fields:
        if field not in data:
            raise ConfigError(f"Method '{method_key}' missing required field: {field}")
        if not isinstance(data[field], str) or not data[field].strip():
            raise ConfigError(
                f"Method '{method_key}' field '{field}' must be a non-empty string"
            )

    # Validate risk_level is valid enum value
    valid_risk_levels = {"safe", "interactive", "dangerous"}
    if data["risk_level"].lower() not in valid_risk_levels:
        raise ConfigError(
            f"Method '{method_key}' has invalid risk_level: {data['risk_level']}. "
            f"Must be one of: {', '.join(sorted(valid_risk_levels))}"
        )

    # Validate dependencies if present
    if "dependencies" in data:
        if not isinstance(data["dependencies"], list):
            raise ConfigError(
                f"Method '{method_key}' field 'dependencies' must be an array"
            )
        for i, dep in enumerate(data["dependencies"]):
            if not isinstance(dep, str) or not dep.strip():
                raise ConfigError(
                    f"Method '{method_key}' dependencies[{i}] must be a non-empty string"
                )


def _parse_risk_level(value: str) -> RiskLevel:
    """Convert string risk level to RiskLevel enum.

    Args:
        value: String value (e.g., "safe", "interactive", "dangerous")

    Returns:
        RiskLevel enum value

    Raises:
        ValueError: If value is not a valid risk level
    """
    try:
        return RiskLevel(value.lower())
    except ValueError as e:
        valid = [rl.value for rl in RiskLevel]
        raise ValueError(
            f"Invalid risk level '{value}'. Must be one of: {', '.join(valid)}"
        ) from e


def get_harnesses() -> dict[str, Harness]:
    """Load all harnesses from bundled data file.

    Returns:
        Dictionary mapping harness name to Harness instance

    Raises:
        ConfigError: If file cannot be loaded or data is invalid
    """
    global _harnesses_cache

    if _harnesses_cache is not None:
        return _harnesses_cache

    data_dir = _get_data_dir()
    file_path = data_dir / "harnesses.json"
    raw_data = _load_json_file(file_path)

    if "harnesses" not in raw_data:
        raise ConfigError(
            f"Invalid harnesses data file: missing top-level 'harnesses' key"
        )

    if not isinstance(raw_data["harnesses"], dict):
        raise ConfigError(f"Invalid harnesses data file: 'harnesses' must be an object")

    harnesses = {}
    for harness_name, harness_data in raw_data["harnesses"].items():
        if not isinstance(harness_data, dict):
            raise ConfigError(
                f"Invalid harnesses data file: '{harness_name}' must be an object"
            )

        _validate_harness_data(harness_data, harness_name)

        harnesses[harness_name] = Harness(
            name=harness_data["name"],
            display_name=harness_data["display_name"],
            description=harness_data["description"],
            github_repo=harness_data.get("github_repo"),
            release_notes_url=harness_data.get("release_notes_url"),
        )

    _harnesses_cache = harnesses
    return harnesses


def get_dependencies() -> dict[str, Dependency]:
    """Load all dependencies from bundled data file.

    Returns:
        Dictionary mapping dependency name to Dependency instance

    Raises:
        ConfigError: If file cannot be loaded or data is invalid
    """
    global _dependencies_cache

    if _dependencies_cache is not None:
        return _dependencies_cache

    data_dir = _get_data_dir()
    file_path = data_dir / "dependencies.json"
    raw_data = _load_json_file(file_path)

    if "dependencies" not in raw_data:
        raise ConfigError(
            f"Invalid dependencies data file: missing top-level 'dependencies' key"
        )

    if not isinstance(raw_data["dependencies"], dict):
        raise ConfigError(
            f"Invalid dependencies data file: 'dependencies' must be an object"
        )

    dependencies = {}
    for dep_name, dep_data in raw_data["dependencies"].items():
        if not isinstance(dep_data, dict):
            raise ConfigError(
                f"Invalid dependencies data file: '{dep_name}' must be an object"
            )

        _validate_dependency_data(dep_data, dep_name)

        dependencies[dep_name] = Dependency(
            name=dep_data["name"],
            check_command=dep_data["check_command"],
            install_hint=dep_data["install_hint"],
            version_command=dep_data.get("version_command"),
            min_version=dep_data.get("min_version"),
            max_version=dep_data.get("max_version"),
        )

    _dependencies_cache = dependencies
    return dependencies


def get_presets() -> dict[str, Preset]:
    """Load all presets from bundled data file.

    Returns:
        Dictionary mapping preset name to Preset instance

    Raises:
        ConfigError: If file cannot be loaded or data is invalid
    """
    global _presets_cache

    if _presets_cache is not None:
        return _presets_cache

    data_dir = _get_data_dir()
    file_path = data_dir / "presets.json"
    raw_data = _load_json_file(file_path)

    if "presets" not in raw_data:
        raise ConfigError(f"Invalid presets data file: missing top-level 'presets' key")

    if not isinstance(raw_data["presets"], dict):
        raise ConfigError(f"Invalid presets data file: 'presets' must be an object")

    presets = {}
    for preset_name, preset_data in raw_data["presets"].items():
        if not isinstance(preset_data, dict):
            raise ConfigError(
                f"Invalid presets data file: '{preset_name}' must be an object"
            )

        _validate_preset_data(preset_data, preset_name)

        presets[preset_name] = Preset(
            name=preset_name,
            strategy=preset_data["strategy"],
            description=preset_data["description"],
            methods=dict(preset_data["methods"]),
            fallback_strategy=preset_data.get("fallback_strategy"),
            priority=preset_data.get("priority", 999),
        )

    _presets_cache = presets
    return presets


def get_all_methods() -> dict[str, InstallMethod]:
    """Load all install methods from bundled data file.

    Returns:
        Dictionary mapping method key (e.g., "claude.mise_binary") to InstallMethod instance

    Raises:
        ConfigError: If file cannot be loaded or data is invalid
    """
    global _methods_cache

    if _methods_cache is not None:
        return _methods_cache

    data_dir = _get_data_dir()
    file_path = data_dir / "methods.json"
    raw_data = _load_json_file(file_path)

    if "methods" not in raw_data:
        raise ConfigError(f"Invalid methods data file: missing top-level 'methods' key")

    if not isinstance(raw_data["methods"], dict):
        raise ConfigError(f"Invalid methods data file: 'methods' must be an object")

    methods = {}
    for method_key, method_data in raw_data["methods"].items():
        if not isinstance(method_data, dict):
            raise ConfigError(
                f"Invalid methods data file: '{method_key}' must be an object"
            )

        _validate_method_data(method_data, method_key)

        risk_level = _parse_risk_level(method_data["risk_level"])

        methods[method_key] = InstallMethod(
            harness=method_key.split(".", 1)[0],
            method_name=method_key.split(".", 1)[1]
            if "." in method_key
            else method_key,
            install=method_data["install"],
            upgrade=method_data["upgrade"],
            version=method_data["version"],
            check_latest=method_data["check_latest"],
            dependencies=method_data.get("dependencies", []),
            risk_level=risk_level,
        )

    _methods_cache = methods
    return methods


def get_method(harness: str, method_name: str) -> InstallMethod | None:
    """Get a specific install method by harness and method name.

    Args:
        harness: Harness name (e.g., "claude")
        method_name: Method name (e.g., "mise_binary")

    Returns:
        InstallMethod instance if found, None otherwise
    """
    methods = get_all_methods()
    key = f"{harness}.{method_name}"
    return methods.get(key)


def clear_cache() -> None:
    """Clear all cached data.

    Forces reload on next access. Useful for testing and configuration reload.
    """
    global _harnesses_cache, _dependencies_cache, _presets_cache, _methods_cache
    _harnesses_cache = None
    _dependencies_cache = None
    _presets_cache = None
    _methods_cache = None


__all__ = [
    "get_harnesses",
    "get_dependencies",
    "get_presets",
    "get_all_methods",
    "get_method",
    "clear_cache",
]

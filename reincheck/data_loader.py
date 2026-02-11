"""Data loader for harness configuration files.

This module provides cached access to harness, dependency, preset, and install
method data loaded from JSON files in the bundled data directory.

Caching Strategy:
- Data is loaded once on first access and cached in module-level variables
- Caches persist for the lifetime of the program to avoid repeated disk I/O
- Use clear_cache() to force a reload of all or specific caches

Cache Invalidation:
- Clear caches when testing to ensure fresh data between test cases
- Clear caches if bundled data files are modified at runtime (rare)
- No automatic invalidation - data is read-only after program start

Testing:
- Tests use clear_cache() to prevent state pollution between tests
- clear_cache() can selectively clear individual caches or all caches
"""

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


def _require_str_field(data: dict, field: str, entity_name: str) -> None:
    """Validate required string field.

    Args:
        data: Raw dict
        field: Field name to validate
        entity_name: Entity name for error messages

    Raises:
        ConfigError: If field missing, not str, or empty
    """
    if field not in data:
        raise ConfigError(f"{entity_name} missing required field: {field}")
    if not isinstance(data[field], str) or not data[field].strip():
        raise ConfigError(f"{entity_name} field '{field}' must be a non-empty string")


def _optional_field(data: dict, field: str, entity_name: str, field_type: type) -> None:
    """Validate optional field with type check.

    Args:
        data: Raw dict
        field: Field name to validate
        entity_name: Entity name for error messages
        field_type: Expected type (str, int, etc.)

    Raises:
        ConfigError: If field present, not None, and wrong type
    """
    if field in data and data[field] is not None:
        if not isinstance(data[field], field_type):
            type_name = field_type.__name__
            raise ConfigError(
                f"{entity_name} field '{field}' must be a {type_name} or null"
            )


def _require_dict_field(data: dict, field: str, entity_name: str) -> None:
    """Validate required dict field.

    Args:
        data: Raw dict
        field: Field name to validate
        entity_name: Entity name for error messages

    Raises:
        ConfigError: If field missing or not a dict
    """
    if field not in data:
        raise ConfigError(f"{entity_name} missing required field: {field}")
    if not isinstance(data[field], dict):
        raise ConfigError(f"{entity_name} field '{field}' must be an object")


def _require_list_field(data: dict, field: str, entity_name: str) -> None:
    """Validate required list field.

    Args:
        data: Raw dict
        field: Field name to validate
        entity_name: Entity name for error messages

    Raises:
        ConfigError: If field missing or not a list
    """
    if field not in data:
        raise ConfigError(f"{entity_name} missing required field: {field}")
    if not isinstance(data[field], list):
        raise ConfigError(f"{entity_name} field '{field}' must be an array")


def _require_enum_field(
    data: dict, field: str, entity_name: str, allowed_values: set[str]
) -> None:
    """Validate field against allowed enum values.

    Args:
        data: Raw dict
        field: Field name to validate
        entity_name: Entity name for error messages
        allowed_values: Set of allowed values

    Raises:
        ConfigError: If field value not in allowed values
    """
    if data[field].lower() not in allowed_values:
        sorted_allowed = ", ".join(sorted(allowed_values))
        raise ConfigError(
            f"{entity_name} has invalid {field}: {data[field]}. "
            f"Must be one of: {sorted_allowed}"
        )


def _validate_string_list(data: dict, field: str, entity_name: str) -> None:
    """Validate list contains only non-empty strings.

    Args:
        data: Raw dict
        field: Field name to validate
        entity_name: Entity name for error messages

    Raises:
        ConfigError: If field not a list or contains invalid strings
    """
    if field in data:
        if not isinstance(data[field], list):
            raise ConfigError(f"{entity_name} field '{field}' must be an array")
        for i, item in enumerate(data[field]):
            if not isinstance(item, str) or not item.strip():
                raise ConfigError(
                    f"{entity_name} {field}[{i}] must be a non-empty string"
                )


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
        _require_str_field(data, field, f"Harness '{harness_name}'")

    optional_fields = ["github_repo", "release_notes_url", "binary"]
    for field in optional_fields:
        _optional_field(data, field, f"Harness '{harness_name}'", str)


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
        _require_str_field(data, field, f"Dependency '{dep_name}'")

    optional_fields = ["version_command", "min_version", "max_version"]
    for field in optional_fields:
        _optional_field(data, field, f"Dependency '{dep_name}'", str)


def _validate_preset_data(data: dict, preset_name: str) -> None:
    """Validate preset data before creating Preset instance.

    Args:
        data: Raw dict for a single preset
        preset_name: Name of the preset for error messages

    Raises:
        ConfigError: If validation fails
    """
    _require_str_field(data, "strategy", f"Preset '{preset_name}'")
    _require_str_field(data, "description", f"Preset '{preset_name}'")
    _require_dict_field(data, "methods", f"Preset '{preset_name}'")
    _optional_field(data, "priority", f"Preset '{preset_name}'", int)
    _optional_field(data, "fallback_strategy", f"Preset '{preset_name}'", str)


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
        _require_str_field(data, field, f"Method '{method_key}'")

    valid_risk_levels = {"safe", "interactive", "dangerous"}
    _require_enum_field(data, "risk_level", f"Method '{method_key}'", valid_risk_levels)

    _validate_string_list(data, "dependencies", f"Method '{method_key}'")


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
            "Invalid harnesses data file: missing top-level 'harnesses' key"
        )

    if not isinstance(raw_data["harnesses"], dict):
        raise ConfigError("Invalid harnesses data file: 'harnesses' must be an object")

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
            "Invalid dependencies data file: missing top-level 'dependencies' key"
        )

    if not isinstance(raw_data["dependencies"], dict):
        raise ConfigError(
            "Invalid dependencies data file: 'dependencies' must be an object"
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
        raise ConfigError("Invalid presets data file: missing top-level 'presets' key")

    if not isinstance(raw_data["presets"], dict):
        raise ConfigError("Invalid presets data file: 'presets' must be an object")

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
        raise ConfigError("Invalid methods data file: missing top-level 'methods' key")

    if not isinstance(raw_data["methods"], dict):
        raise ConfigError("Invalid methods data file: 'methods' must be an object")

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


def clear_cache(cache_type: str | None = None) -> None:
    """Clear cached data to force reload on next access.

    Args:
        cache_type: Optional cache type to clear. If None, clears all caches.
            Valid values: 'harnesses', 'dependencies', 'presets', 'methods'
            Defaults to None (clear all caches).

    Raises:
        ValueError: If cache_type is not one of the valid values

    Examples:
        >>> clear_cache()  # Clear all caches
        >>> clear_cache('harnesses')  # Clear only harnesses cache
    """
    global _harnesses_cache, _dependencies_cache, _presets_cache, _methods_cache

    valid_cache_types = {"harnesses", "dependencies", "presets", "methods"}

    if cache_type is None:
        _harnesses_cache = None
        _dependencies_cache = None
        _presets_cache = None
        _methods_cache = None
    else:
        if cache_type not in valid_cache_types:
            raise ValueError(
                f"Invalid cache_type '{cache_type}'. "
                f"Must be one of: {', '.join(sorted(valid_cache_types))}"
            )
        if cache_type == "harnesses":
            _harnesses_cache = None
        elif cache_type == "dependencies":
            _dependencies_cache = None
        elif cache_type == "presets":
            _presets_cache = None
        elif cache_type == "methods":
            _methods_cache = None


__all__ = [
    "get_harnesses",
    "get_dependencies",
    "get_presets",
    "get_all_methods",
    "get_method",
    "clear_cache",
]

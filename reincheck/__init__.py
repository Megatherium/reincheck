import asyncio
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import TypedDict, cast
import click

from .config import (
    ConfigError,
    AgentConfig,
    Config,
    validate_config,
    load_config as load_json_config,
)

DEFAULT_TIMEOUT = 30
UPGRADE_TIMEOUT = 300
INSTALL_TIMEOUT = 600

_logging = logging.getLogger(__name__)


def get_config_dir() -> Path:
    """Return XDG-compliant config directory: ~/.config/reincheck"""
    return Path.home() / ".config" / "reincheck"


def get_packaged_config_path() -> Path:
    """Return path to packaged default config (read-only fallback)"""
    return Path(__file__).parent / "agents.json"


def get_config_path(create: bool = False) -> Path:
    """Return path to user config file.

    Priority:
    1. REINCHECK_CONFIG environment variable (if set)
    2. ~/.config/reincheck/agents.json (default XDG location)

    Args:
        create: If True, create config dir and seed from defaults if missing

    Returns:
        Path to config file
    """
    if "REINCHECK_CONFIG" in os.environ:
        custom_path = Path(os.environ["REINCHECK_CONFIG"])
        if create:
            custom_path.parent.mkdir(parents=True, exist_ok=True)
        return custom_path

    config_path = get_config_dir() / "agents.json"
    if create:
        ensure_user_config(config_path)
    return config_path


def migrate_yaml_to_json(yaml_path: Path, json_path: Path) -> None:
    """Migrate YAML config to JSON format.

    Args:
        yaml_path: Path to source YAML file
        json_path: Path to destination JSON file

    Raises:
        ConfigError: If migration fails
    """
    try:
        import yaml
    except ImportError:
        _logging.warning("pyyaml not installed. Install with: pip install pyyaml")
        raise ConfigError(
            f"Cannot migrate YAML config: pyyaml not installed.\n"
            f"Install with: pip install pyyaml"
        )

    try:
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict) or "agents" not in data:
            raise ValueError("Invalid YAML config structure")

        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

        yaml_backup = yaml_path.with_suffix(".yaml.bak")
        yaml_path.rename(yaml_backup)

        click.echo(f"✅ Migrated config from {yaml_path} to {json_path}")
        click.echo(f"   Old YAML backed up to {yaml_backup}")
        click.echo(f"   You can manually remove the backup when you're ready.")

    except Exception as e:
        _logging.error(f"Migration failed: {e}")
        raise ConfigError(f"Failed to migrate YAML config: {e}")


def ensure_user_config(user_config_path: Path) -> None:
    """Ensure user config exists with proper seeding/migration logic.

    Priority order:
    1. If user_config exists → do nothing
    2. If ~/.config/reincheck/agents.yaml exists → migrate YAML→JSON
    3. If old project agents.yaml exists (dev mode) → migrate YAML→JSON
    4. Seed from packaged default (reincheck/agents.json)

    Args:
        user_config_path: Path where user config should exist
    """
    if user_config_path.exists():
        return

    _logging.debug(f"User config not found, checking migration sources...")

    yaml_sources = [
        get_config_dir() / "agents.yaml",
        Path(__file__).parent / "agents.yaml",
    ]

    for yaml_path in yaml_sources:
        if yaml_path.exists():
            click.echo(f"⚠️  Found legacy YAML config at {yaml_path}")
            click.echo(f"   Migrating to {user_config_path}...")
            try:
                migrate_yaml_to_json(yaml_path, user_config_path)
                return
            except ConfigError:
                _logging.warning(f"Migration from {yaml_path} failed, trying next source")
                continue

    packaged_default = get_packaged_config_path()
    if packaged_default.exists():
        click.echo(f"📋 Creating user config from packaged defaults...")
        user_config_path.parent.mkdir(parents=True, exist_ok=True)
        user_config_path.write_text(packaged_default.read_text())
        _logging.debug(f"Seeded config from {packaged_default}")
    else:
        user_config_path.parent.mkdir(parents=True, exist_ok=True)
        user_config_path.write_text('{"agents": []}\n')
        _logging.debug("Created empty config")


def setup_logging(debug: bool = False):
    """Configure logging for the application."""
    if not _logging.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        _logging.addHandler(handler)
        _logging.setLevel(logging.DEBUG if debug else logging.INFO)


class UpdateResult(TypedDict):
    name: str
    current_version: str | None
    current_status: str
    latest_version: str | None
    latest_status: str
    update_available: bool
    description: str


def _dict_to_config(data: dict) -> Config:
    """Convert a raw dict to a Config object.

    Temporary bridge function - delegates to validate_config from config.py.
    Kept for backward compatibility during migration.
    """
    return validate_config(data)


def load_config(config_path: Path | None = None) -> Config:
    """Load agents configuration from a JSON file.

    Args:
        config_path: Optional path to config file. If None, uses get_config_path(create=True)

    Returns:
        Config object with agents list

    Raises:
        ConfigError: If the config cannot be loaded or parsed
    """
    if config_path is None:
        config_path = get_config_path(create=True)

    if not config_path.exists():
        raise ConfigError(
            f"Config file not found: {config_path}\n"
            f"Run 'reincheck config init' to create a default config."
        )

    try:
        data = load_json_config(config_path)
    except ConfigError as e:
        raise ConfigError(
            f"Config file is corrupted: {config_path}\n{e}\n\n"
            f"Run 'reincheck config init' to restore defaults."
        ) from e

    return _dict_to_config(data)


# Also export the new JSON loader for future use
__all__ = [
    "ConfigError",
    "AgentConfig",
    "Config",
    "UpdateResult",
    "load_config",
    "save_config",
    "setup_logging",
    "DEFAULT_TIMEOUT",
    "UPGRADE_TIMEOUT",
    "INSTALL_TIMEOUT",
    "get_config_dir",
    "get_config_path",
    "get_packaged_config_path",
]


def save_config(config: Config, config_path: Path | None = None) -> None:
    """Save agents configuration to JSON file atomically.

    Args:
        config: Config object to save
        config_path: Optional path to config file. If None, uses get_config_path(create=True)
    """
    if config_path is None:
        config_path = get_config_path(create=True)

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise ConfigError(f"Failed to create config directory: {config_path.parent}\n{e}")

    try:
        # Convert dataclass to dict for JSON serialization
        agents_data = []
        for agent in config.agents:
            agent_dict = {
                "name": agent.name,
                "description": agent.description,
                "install_command": agent.install_command,
                "version_command": agent.version_command,
                "check_latest_command": agent.check_latest_command,
                "upgrade_command": agent.upgrade_command,
            }
            if agent.latest_version is not None:
                agent_dict["latest_version"] = agent.latest_version
            if agent.github_repo is not None:
                agent_dict["github_repo"] = agent.github_repo
            if agent.release_notes_url is not None:
                agent_dict["release_notes_url"] = agent.release_notes_url
            agents_data.append(agent_dict)

        data = {"agents": agents_data}

        # Write to temp file first
        temp_path = config_path.with_suffix(".tmp")
        with open(temp_path, "w") as f:
            json.dump(data, f, indent=2)
        # Atomic rename (POSIX guarantees atomicity)
        temp_path.replace(config_path)
    except (IOError, OSError) as e:
        _logging.error(f"Error saving configuration: {e}")
        click.echo(f"Error saving configuration: {e}", err=True)
        raise


async def run_command_async(
    command: str, timeout: int = DEFAULT_TIMEOUT, debug: bool = False
) -> tuple[str, int]:
    """Run a command asynchronously and return output and return code."""
    process = None
    try:
        if debug:
            _logging.debug(f"Running command: {command}")
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            output = stdout.decode().strip()
            if stderr and debug:
                _logging.debug(f"stderr: {stderr.decode().strip()}")
            return output, process.returncode if process.returncode is not None else 1
        except asyncio.TimeoutError:
            process.kill()
            _ = await process.wait()
            return f"Command timed out after {timeout} seconds", 1
    except Exception as e:
        if debug:
            _logging.debug(f"Exception: {type(e).__name__}: {e}")
        return f"Error: {str(e)}", 1
    finally:
        if process:
            transport = getattr(process, "_transport", None)
            if transport:
                transport.close()


async def get_current_version(agent: AgentConfig) -> tuple[str | None, str]:
    """Get the current version of an agent."""
    version_command = agent.version_command
    if not version_command:
        return None, "No version command configured"

    output, returncode = await run_command_async(version_command)
    if returncode == 0:
        return output, "success"
    else:
        return None, output or "Command failed"


def add_github_auth_if_needed(command: str) -> str:
    """Add Bearer token header to curl commands targeting GitHub API
    if GITHUB_TOKEN is set."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token or "api.github.com" not in command:
        return command

    if "Authorization:" in command:
        return command

    if "curl " in command or "curl" == command[:4]:
        header = ' -H "Authorization: Bearer $GITHUB_TOKEN"'
        if "-H " in command:
            command = command.replace("curl ", f"curl{header} ", 1)
        else:
            command = command.replace("curl", f"curl{header}", 1)

    return command


async def get_latest_version(agent: AgentConfig) -> tuple[str | None, str]:
    """Get the latest version of an agent."""
    check_latest_command = agent.check_latest_command
    if not check_latest_command:
        return None, "No version check command configured"

    check_latest_command = add_github_auth_if_needed(check_latest_command)
    output, returncode = await run_command_async(check_latest_command)
    if returncode == 0:
        return output, "success"
    else:
        return None, output or "Command failed"


def extract_version_number(version_str: str) -> str:
    """Extract version number from version string."""
    if not version_str:
        return ""

    # Look for version patterns like v1.2.3, 1.2.3, or version numbers in parentheses
    patterns = [
        r"v?(\d+\.\d+\.\d+(?:\.\d+)?)",  # v1.2.3 or 1.2.3
        r"v?(\d+\.\d+(?:\.\d+)?)",  # v1.2 or 1.2
        r"v?(\d+)",  # v1 or 1
    ]

    for pattern in patterns:
        match = re.search(pattern, version_str)
        if match:
            return match.group(1)

    # If no version found, return empty string to avoid comparing "Unknown" vs "1.2.3"
    return ""


def compare_versions(version1: str, version2: str) -> int:
    """Compare two version strings. Returns -1, 0, or 1."""

    def version_tuple(v: str) -> tuple[int, ...]:
        return tuple(map(int, v.split(".")))

    try:
        v1 = version_tuple(extract_version_number(version1))
        v2 = version_tuple(extract_version_number(version2))

        if v1 < v2:
            return -1
        elif v1 > v2:
            return 1
        else:
            return 0
    except (ValueError, TypeError):
        # If parsing fails, do string comparison
        if version1 < version2:
            return -1
        elif version1 > version2:
            return 1
        else:
            return 0


async def check_agent_updates(agent: AgentConfig) -> UpdateResult:
    """Check if an agent has an update available."""
    # Run checks in parallel
    current_future = get_current_version(agent)
    latest_future = get_latest_version(agent)

    (current, current_status), (latest, latest_status) = await asyncio.gather(
        current_future, latest_future
    )

    result: UpdateResult = {
        "name": agent.name,
        "current_version": current,
        "current_status": current_status,
        "latest_version": latest,
        "latest_status": latest_status,
        "update_available": False,
        "description": agent.description,
    }

    if (
        current
        and latest
        and current_status == "success"
        and latest_status == "success"
    ):
        # Compare versions
        if compare_versions(current, latest) < 0:
            result["update_available"] = True

    return result


async def fetch_url_content(url: str) -> tuple[str | None, str]:
    """Fetch content from a URL using curl."""
    cmd = f"curl -s -L {url}"
    output, returncode = await run_command_async(cmd)
    if returncode != 0:
        return None, f"Failed to fetch URL: {output}"
    return output, "success"


async def get_npm_release_info(package_name: str) -> str | None:
    """Get release info from NPM."""
    # Get dist-tags to find the true 'latest'
    cmd_tags = f"npm view {package_name} dist-tags --json"
    output_tags, returncode_tags = await run_command_async(cmd_tags)

    latest_ver = None
    if returncode_tags == 0:
        try:
            tags = json.loads(output_tags)
            latest_ver = tags.get("latest")
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    # Get time info
    cmd_time = f"npm view {package_name} time --json"
    output_time, returncode_time = await run_command_async(cmd_time)

    latest_time = "Unknown"
    if returncode_time == 0:
        try:
            data = json.loads(output_time)
            # If we didn't find latest from tags, try the last key
            if not latest_ver:
                versions = [k for k in data.keys() if k not in ["modified", "created"]]
                if versions:
                    latest_ver = versions[-1]

            if latest_ver:
                latest_time = data.get(latest_ver, "Unknown")
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    if latest_ver:
        return (
            f"### Latest NPM Release: {latest_ver}\n"
            f"**Published:** {latest_time}\n\n"
            f"View on NPM: https://www.npmjs.com/package/{package_name}\n"
        )

    return None


async def get_pypi_release_info(package_name: str) -> str | None:
    """Get release info from PyPI."""
    url = f"https://pypi.org/pypi/{package_name}/json"
    output, returncode = await run_command_async(f"curl -s {url}")

    if returncode != 0:
        return None

    try:
        data = json.loads(output)
        info = data.get("info", {})
        latest_ver = info.get("version")

        if not latest_ver:
            return None

        # Try to find release time
        releases = data.get("releases", {})
        latest_release_data = releases.get(latest_ver, [])
        upload_time = "Unknown"
        if latest_release_data:
            upload_time = latest_release_data[0].get("upload_time", "Unknown")

        project_urls = info.get("project_urls") or {}
        changelog_url = (
            project_urls.get("Changelog")
            or project_urls.get("Changes")
            or project_urls.get("History")
        )

        notes = (
            f"### Latest PyPI Release: {latest_ver}\n"
            f"**Uploaded:** {upload_time}\n"
            f"**Summary:** {info.get('summary', '')}\n\n"
            f"View on PyPI: https://pypi.org/project/{package_name}/\n"
        )

        if changelog_url:
            notes += f"Changelog: {changelog_url}\n"

        return notes
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


async def fetch_github_release_notes(
    agent: AgentConfig, current_version: str | None
) -> list[str]:
    """Fetch release notes from GitHub API."""
    notes_parts = []
    repo = agent.github_repo
    if not repo:
        return notes_parts

    url = f"https://api.github.com/repos/{repo}/releases/latest"
    cmd = add_github_auth_if_needed(
        f"curl -s -H 'Accept: application/vnd.github.v3+json' {url}"
    )
    output, returncode = await run_command_async(cmd)

    if returncode == 0:
        try:
            data = cast(dict[str, object], json.loads(output))
            tag_name = str(data.get("tag_name", ""))
            body = str(data.get("body", ""))

            # Check version freshness
            github_ver = extract_version_number(tag_name)
            current_ver_num = extract_version_number(current_version or "")

            is_outdated = False
            if current_ver_num and github_ver:
                if compare_versions(github_ver, current_ver_num) < 0:
                    is_outdated = True

            if is_outdated:
                notes_parts.append(
                    f"⚠️ **Warning**: The latest GitHub release ({tag_name}) appears older than your installed version ({current_version}).\n"
                )

            if body:
                header = f"# Release Notes: {agent.name} ({tag_name})\n\n"
                notes_parts.append(header + body)
            else:
                notes_parts.append(
                    f"No release body found on GitHub. Check {data.get('html_url', url)}"
                )

        except json.JSONDecodeError:
            notes_parts.append("Failed to parse GitHub release notes JSON.")
    else:
        notes_parts.append(f"Failed to fetch GitHub release notes: {output}")

    return notes_parts


async def fetch_external_release_notes(agent: AgentConfig) -> list[str]:
    """Fetch release notes from an external URL."""
    notes_parts = []
    rn_url = agent.release_notes_url
    if not rn_url:
        return notes_parts

    notes_parts.append(f"\n\n## External Release Notes\nSource: {rn_url}\n")
    # Try to fetch text content if it looks like a text file
    if rn_url.endswith(".md") or rn_url.endswith(".txt"):
        content, status = await fetch_url_content(rn_url)
        if status == "success" and content:
            notes_parts.append(content)
        else:
            notes_parts.append("Could not fetch content directly.")
    else:
        notes_parts.append(f"Please visit: {rn_url}")

    return notes_parts


async def fetch_npm_fallback(agent: AgentConfig) -> list[str]:
    """Fetch release info from NPM as a fallback."""
    notes_parts = []
    install_cmd = agent.install_command
    if "npm" in install_cmd or "npm:" in install_cmd:
        # Extract package name
        match = re.search(r"npm:(@?[\w\-/]+)", install_cmd)
        if not match:
            match = re.search(r"npm install -g (@?[\w\-/]+)", install_cmd)

        if match:
            pkg_name = match.group(1)
            npm_info = await get_npm_release_info(pkg_name)
            if npm_info:
                notes_parts.append(f"\n\n## NPM Info\n{npm_info}")
    return notes_parts


async def fetch_pypi_fallback(agent: AgentConfig) -> list[str]:
    """Fetch release info from PyPI as a fallback."""
    notes_parts = []
    install_cmd = agent.install_command
    if "pip" in install_cmd or "uv tool" in install_cmd:
        # Extract package name
        match = re.search(r"uv tool install (@?[\w\-/]+)", install_cmd)
        if not match:
            match = re.search(r"pip install (@?[\w\-/]+)", install_cmd)

        if match:
            pkg_name = match.group(1)
            pypi_info = await get_pypi_release_info(pkg_name)
            if pypi_info:
                notes_parts.append(f"\n\n## PyPI Info\n{pypi_info}")
    return notes_parts


async def fetch_release_notes(
    agent: AgentConfig, current_version: str | None
) -> tuple[str, str]:
    """Fetch release notes for an agent."""
    notes_parts = []

    # 1. Try GitHub
    notes_parts.extend(await fetch_github_release_notes(agent, current_version))

    # 2. Try Release Notes URL (Fallback or Supplement)
    if not notes_parts or "⚠️" in notes_parts[0]:
        notes_parts.extend(await fetch_external_release_notes(agent))

    # 3. Try NPM Fallback
    should_fallback = not notes_parts or any(
        x in notes_parts[0] for x in ["⚠️", "No release body", "Failed to fetch"]
    )
    if should_fallback:
        notes_parts.extend(await fetch_npm_fallback(agent))

    # 4. Try PyPI Fallback
    if should_fallback:
        notes_parts.extend(await fetch_pypi_fallback(agent))

    if not notes_parts:
        return agent.name, "No release notes found from configured sources."

    return agent.name, "\n".join(notes_parts)

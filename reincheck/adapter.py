"""Adapter layer bridging AgentConfig with Harness/InstallMethod models.

This module provides functions to bridge the legacy AgentConfig model (used by
check/update/upgrade commands) with the new Harness/InstallMethod system (used
by setup command).

The primary use case is allowing commands like `check`, `update`, and `upgrade`
to resolve the correct InstallMethod for a given harness based on the user's
active preset and any overrides.
"""

from __future__ import annotations

from dataclasses import dataclass

from reincheck.config import AgentConfig
from reincheck.installer import Harness, InstallMethod, RiskLevel


@dataclass
class EffectiveMethod:
    """Result of resolving an agent to its effective install method.
    
    Combines metadata from both the Harness and the resolved InstallMethod,
    providing a unified interface for commands that need both.
    """
    harness: Harness
    method: InstallMethod
    source: str  # "config", "preset", or "preset+override"
    
    @property
    def name(self) -> str:
        """Harness name."""
        return self.harness.name
    
    @property
    def description(self) -> str:
        """Harness description."""
        return self.harness.description
    
    @property
    def install_command(self) -> str:
        """Install command from the method."""
        return self.method.install
    
    @property
    def upgrade_command(self) -> str:
        """Upgrade command from the method."""
        return self.method.upgrade
    
    @property
    def version_command(self) -> str:
        """Version command from the method."""
        return self.method.version
    
    @property
    def check_latest_command(self) -> str:
        """Check latest command from the method."""
        return self.method.check_latest
    
    @property
    def github_repo(self) -> str | None:
        """GitHub repo from harness metadata."""
        return self.harness.github_repo
    
    @property
    def release_notes_url(self) -> str | None:
        """Release notes URL from harness metadata."""
        return self.harness.release_notes_url
    
    def to_agent_config(self) -> AgentConfig:
        """Convert to legacy AgentConfig for compatibility."""
        return AgentConfig(
            name=self.name,
            description=self.description,
            install_command=self.install_command,
            version_command=self.version_command,
            check_latest_command=self.check_latest_command,
            upgrade_command=self.upgrade_command,
            github_repo=self.github_repo,
            release_notes_url=self.release_notes_url,
        )


def agent_config_to_method(config: AgentConfig) -> InstallMethod:
    """Convert an AgentConfig to an InstallMethod.
    
    This extracts the command fields from an AgentConfig and creates
    an InstallMethod instance. Useful when working with existing
    agents.json configurations.
    
    Args:
        config: AgentConfig instance to convert
        
    Returns:
        InstallMethod with commands from the config
    """
    return InstallMethod(
        harness=config.name,
        method_name="config",  # Indicates this came from agents.json
        install=config.install_command,
        upgrade=config.upgrade_command,
        version=config.version_command,
        check_latest=config.check_latest_command,
        dependencies=[],
        risk_level=_infer_risk_level(config.install_command),
    )


def _infer_risk_level(command: str) -> RiskLevel:
    """Infer risk level from an install command.
    
    Args:
        command: Install command string
        
    Returns:
        Inferred RiskLevel
    """
    import re
    
    if not command:
        return RiskLevel.SAFE
    
    pipe_pattern = re.compile(r"\|.*\b(sh|bash)\b", re.IGNORECASE)
    if pipe_pattern.search(command):
        return RiskLevel.DANGEROUS
    if any(pkg in command for pkg in ("npm install", "pip install", "uv tool install")):
        return RiskLevel.INTERACTIVE
    return RiskLevel.SAFE


def get_effective_method(
    harness_name: str,
    preset_name: str | None = None,
    overrides: dict[str, str] | None = None,
) -> EffectiveMethod | None:
    """Resolve the effective install method for a harness.
    
    Resolution priority:
    1. Override for this specific harness (if provided)
    2. Preset's method mapping (if preset specified)
    3. Fallback strategy from preset (if defined)
    
    Args:
        harness_name: Name of the harness (e.g., "claude", "aider")
        preset_name: Name of the preset to use for resolution (e.g., "mise_binary")
        overrides: Optional mapping of harness names to method names for overrides.
                   Takes precedence over preset methods. Example: {"claude": "npm"}
        
    Returns:
        EffectiveMethod if resolution succeeds, None if harness not found
        
    Raises:
        ValueError: If preset specified but not found, or no valid method exists
    """
    from reincheck.data_loader import get_harnesses, get_presets, get_all_methods
    
    harnesses = get_harnesses()
    harness = harnesses.get(harness_name)
    
    if not harness:
        return None
    
    methods = get_all_methods()
    overrides = overrides or {}
    
    # Check for override first
    if harness_name in overrides:
        method_name = overrides[harness_name]
        method_key = f"{harness_name}.{method_name}"
        method = methods.get(method_key)
        if method:
            return EffectiveMethod(
                harness=harness,
                method=method,
                source="preset+override",
            )
        raise ValueError(
            f"Override method '{method_name}' not found for harness '{harness_name}'"
        )
    
    # No preset means we can't resolve
    if not preset_name:
        raise ValueError(
            f"No preset specified and no override for harness '{harness_name}'"
        )
    
    presets = get_presets()
    preset = presets.get(preset_name)
    
    if not preset:
        available = ", ".join(sorted(presets.keys()))
        raise ValueError(f"Preset '{preset_name}' not found. Available: {available}")
    
    # Try preset's method mapping
    if harness_name in preset.methods:
        method_name = preset.methods[harness_name]
        method_key = f"{harness_name}.{method_name}"
        method = methods.get(method_key)
        if method:
            return EffectiveMethod(
                harness=harness,
                method=method,
                source="preset",
            )
    
    # Try fallback strategy
    if preset.fallback_strategy:
        method_key = f"{harness_name}.{preset.fallback_strategy}"
        method = methods.get(method_key)
        if method:
            return EffectiveMethod(
                harness=harness,
                method=method,
                source="preset",
            )
    
    raise ValueError(
        f"No valid method found for harness '{harness_name}' in preset '{preset_name}'"
    )


def get_effective_method_from_config(
    config: AgentConfig,
) -> EffectiveMethod:
    """Create an EffectiveMethod from an existing AgentConfig.
    
    This is for backwards compatibility when using agents.json directly
    without the preset system. It wraps the config's commands in an
    InstallMethod and pairs it with the harness metadata.
    
    Args:
        config: AgentConfig from agents.json
        
    Returns:
        EffectiveMethod wrapping the config
        
    Raises:
        ValueError: If harness metadata not found (unlikely for valid configs)
    """
    from reincheck.data_loader import get_harnesses
    
    harnesses = get_harnesses()
    harness = harnesses.get(config.name)
    
    # If harness metadata exists, use it; otherwise create minimal harness
    if harness:
        effective_harness = harness
    else:
        effective_harness = Harness(
            name=config.name,
            display_name=config.name.title(),
            description=config.description,
            github_repo=config.github_repo,
            release_notes_url=config.release_notes_url,
        )
    
    method = agent_config_to_method(config)
    
    return EffectiveMethod(
        harness=effective_harness,
        method=method,
        source="config",
    )


def list_available_methods(harness_name: str) -> list[str]:
    """List all available install methods for a harness.
    
    Args:
        harness_name: Name of the harness
        
    Returns:
        List of method names available for this harness
    """
    from reincheck.data_loader import get_all_methods
    
    methods = get_all_methods()
    prefix = f"{harness_name}."
    
    return [
        key.removeprefix(prefix)
        for key in methods.keys()
        if key.startswith(prefix)
    ]


__all__ = [
    "EffectiveMethod",
    "agent_config_to_method",
    "get_effective_method",
    "get_effective_method_from_config",
    "list_available_methods",
]

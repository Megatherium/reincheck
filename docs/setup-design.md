# Setup Command Architecture & Data Model

> Design document for reincheck-xjq  
> Status: Draft  
> Last updated: 2026-02-05

## Overview

The setup command allows users to install and manage multiple AI coding agents ("harnesses") using different installation strategies. This document defines the core data model, dependency scanning, plan execution, and backward compatibility approach.

## Core Entities

### 1. Harness

A harness represents an AI coding agent. It contains metadata but NOT installation commands—those live in `InstallMethod` records.

```python
@dataclass
class Harness:
    name: str              # Unique identifier: "claude", "amp", "aider"
    display_name: str      # Human-friendly: "Claude Code", "Amp", "Aider"
    description: str       # What it does
    github_repo: str | None    # e.g., "anthropics/claude-code" for release notes
    release_notes_url: str | None  # Fallback URL for release notes
```

### 2. Dependency

A tool or binary required for an install method to work.

```python
@dataclass
class Dependency:
    name: str           # Binary name: "mise", "npm", "curl"
    check_command: str  # Command to verify presence, default: "which {name}"
    install_hint: str   # Human-readable install suggestion
    
    def is_available(self) -> bool:
        """Check if this dependency is available in PATH."""
        # Runs check_command, returns True if exit code 0
```

Standard dependencies (built-in):
- `mise`: check="which mise", hint="Install from https://mise.jdx.dev"
- `npm`: check="which npm", hint="Install Node.js from https://nodejs.org"
- `curl`: check="which curl", hint="Install via system package manager"
- `jq`: check="which jq", hint="Install via system package manager"
- `uv`: check="which uv", hint="Install from https://docs.astral.sh/uv/"
- `brew`: check="which brew", hint="Install from https://brew.sh"

### 3. InstallMethod

A named set of commands for installing/managing a specific harness using a specific tool/approach.

```python
@dataclass
class InstallMethod:
    harness: str           # Which harness this method is for
    method_name: str       # e.g., "mise_binary", "mise_language", "npm", "brew", "recommended"
    install: str           # Install command
    upgrade: str           # Upgrade command  
    version: str           # Get installed version
    check_latest: str      # Get latest available version
    dependencies: list[str]  # List of Dependency names required
    risk_level: RiskLevel  # See below
```

```python
class RiskLevel(Enum):
    SAFE = "safe"              # mise, npm, brew - trusted package managers
    INTERACTIVE = "interactive"  # May prompt for input
    DANGEROUS = "dangerous"     # curl|sh - arbitrary code execution
```

### 4. Strategy vs Preset

**Strategy**: A category/philosophy for installation approaches.

```python
@dataclass  
class Strategy:
    name: str           # "mise_binary", "mise_language", "homebrew", "language", "recommended"
    description: str    # Human-friendly explanation
    priority: int       # Sort order in UI (lower = higher priority)
```

**Preset**: A concrete, complete mapping of harnesses to install methods. A preset belongs to a strategy.

```python
@dataclass
class Preset:
    name: str                          # Usually same as strategy name
    strategy: str                      # Which strategy this implements
    description: str                   # Human-friendly description
    methods: dict[str, str]            # harness_name → method_name mapping
    fallback_strategy: str | None      # If method unavailable, try this
```

**Key insight**: Strategy and Preset are NOT the same. A strategy is a category; a preset is a concrete configuration. However, in most cases they map 1:1 (the "mise_binary" strategy has one "mise_binary" preset). The distinction exists to allow:
1. Multiple presets per strategy (e.g., "mise_binary_minimal" vs "mise_binary_full")
2. Future extensibility for user-defined presets

For MVP, we can treat them as synonymous in the UI.

### 5. Plan

The execution plan generated from a preset selection.

```python
@dataclass
class PlanStep:
    harness: str
    action: str              # "install" or "upgrade"  
    command: str
    timeout: int             # Seconds
    risk_level: RiskLevel
    method_name: str         # For display/debugging
    dependencies: list[str]  # Required deps for this step

@dataclass
class Plan:
    preset_name: str
    steps: list[PlanStep]
    unsatisfied_deps: list[str]  # Dependencies not found
    risky_steps: list[str]       # Harnesses requiring curl|sh
    
    def is_ready(self) -> bool:
        """All dependencies satisfied."""
        return len(self.unsatisfied_deps) == 0
```

## The "Green" Computation

At startup, scan for available tools to determine which presets/methods are "green" (fully satisfied).

```python
def scan_dependencies() -> dict[str, bool]:
    """Scan PATH for all known dependencies, return availability map."""
    deps = get_all_dependencies()  # Built-in list
    return {dep.name: dep.is_available() for dep in deps}

def compute_preset_status(preset: Preset, dep_map: dict[str, bool]) -> PresetStatus:
    """Determine if a preset is fully green, partially green, or red."""
    all_deps = set()
    for harness, method_name in preset.methods.items():
        method = get_method(harness, method_name)
        all_deps.update(method.dependencies)
    
    missing = [d for d in all_deps if not dep_map.get(d, False)]
    
    if not missing:
        return PresetStatus.GREEN
    elif len(missing) < len(all_deps):
        return PresetStatus.PARTIAL
    else:
        return PresetStatus.RED
```

Display rules:
- GREEN presets: shown first, green font, checkmark
- PARTIAL presets: shown with warning, orange font
- RED presets: shown last, red font, require confirmation to select

## Override Mechanics

Three levels of customization, in order of precedence:

### Level 1: Preset Selection
User picks a preset (e.g., "mise_binary"). This sets the default method for all harnesses.

### Level 2: Per-Harness Method Override
User can override which method is used for a specific harness:

```json
{
  "preset": "mise_binary",
  "overrides": {
    "droid": "recommended",    // droid doesn't have mise support
    "claude": "npm"            // prefer npm for claude
  }
}
```

### Level 3: Per-Command Override
For fine-grained control, override individual commands:

```json
{
  "preset": "mise_binary",
  "overrides": {
    "claude": {
      "method": "npm",
      "commands": {
        "install": "pnpm add -g @anthropic-ai/claude-code"  // use pnpm instead
      }
    }
  }
}
```

Resolution order:
1. Check per-command override
2. Check per-harness method override  
3. Fall back to preset default
4. If preset method unavailable, try fallback_strategy

## Plan Execution

### plan_install()

Generate an installation plan from preset + harness selection:

```python
def plan_install(
    preset: Preset,
    harnesses: list[str],
    overrides: dict[str, Any] | None = None
) -> Plan:
    """Generate ordered installation steps."""
    steps = []
    unsatisfied = set()
    risky = []
    
    for harness in harnesses:
        method = resolve_method(preset, harness, overrides)
        
        # Check dependencies
        for dep in method.dependencies:
            if not is_dep_available(dep):
                unsatisfied.add(dep)
        
        # Flag risky
        if method.risk_level == RiskLevel.DANGEROUS:
            risky.append(harness)
        
        steps.append(PlanStep(
            harness=harness,
            action="install",
            command=method.install,
            timeout=INSTALL_TIMEOUT,
            risk_level=method.risk_level,
            method_name=method.method_name,
            dependencies=method.dependencies
        ))
    
    return Plan(
        preset_name=preset.name,
        steps=steps,
        unsatisfied_deps=list(unsatisfied),
        risky_steps=risky
    )
```

### render_plan()

Human-readable preview of what will happen:

```python
def render_plan(plan: Plan) -> str:
    """Generate human-readable plan summary."""
    lines = [f"Installation Plan: {plan.preset_name}", ""]
    
    if plan.unsatisfied_deps:
        lines.append("⚠️  Missing dependencies:")
        for dep in plan.unsatisfied_deps:
            hint = get_dependency(dep).install_hint
            lines.append(f"   • {dep}: {hint}")
        lines.append("")
    
    if plan.risky_steps:
        lines.append("⚠️  The following require curl|sh (review carefully):")
        for harness in plan.risky_steps:
            lines.append(f"   • {harness}")
        lines.append("")
    
    lines.append("Steps:")
    for i, step in enumerate(plan.steps, 1):
        risk_icon = {"safe": "🟢", "interactive": "🟡", "dangerous": "🔴"}[step.risk_level.value]
        lines.append(f"  {i}. {risk_icon} {step.harness}")
        lines.append(f"     $ {step.command}")
    
    return "\n".join(lines)
```

### apply_plan()

Execute the plan with safety controls:

```python
async def apply_plan(
    plan: Plan,
    dry_run: bool = False,
    skip_confirmation: bool = False
) -> list[StepResult]:
    """Execute installation plan."""
    
    if not plan.is_ready() and not skip_confirmation:
        if not confirm("Dependencies missing. Continue anyway?"):
            return []
    
    results = []
    
    for step in plan.steps:
        # Dangerous commands require per-step confirmation
        if step.risk_level == RiskLevel.DANGEROUS and not skip_confirmation:
            print(f"\n⚠️  DANGEROUS: About to run curl|sh for {step.harness}")
            print(f"   Command: {step.command}")
            if not confirm("Execute this command? (review carefully)"):
                results.append(StepResult(step.harness, "skipped", "User declined"))
                continue
        
        if dry_run:
            print(f"[DRY-RUN] Would execute: {step.command}")
            results.append(StepResult(step.harness, "dry-run", step.command))
            continue
        
        # Execute
        output, returncode = await run_command_async(
            step.command, 
            timeout=step.timeout
        )
        
        if returncode == 0:
            results.append(StepResult(step.harness, "success", output))
        else:
            results.append(StepResult(step.harness, "failed", output))
            # Continue with other harnesses, don't abort entire plan
    
    return results
```

## Configuration File Format

Per reincheck-gaq decision: **JSON with tolerant preprocessing** (trailing commas, // comments accepted on input; strict JSON on output).

### User Config (~/.config/reincheck/config.json)

```json
{
  // User's selected preset
  "preset": "mise_binary",
  
  // Per-harness overrides
  "overrides": {
    "droid": "recommended",
    "claude": {
      "method": "npm",
      "commands": {
        "install": "pnpm add -g @anthropic-ai/claude-code"
      }
    }
  },
  
  // Which harnesses to manage (null = all)
  "managed_harnesses": ["claude", "amp", "aider", "gemini"],
  
  // Cached latest versions (populated by `reincheck update`)
  "latest_versions": {
    "claude": "2.1.31",
    "amp": "0.0.1770300461"
  }
}
```

### Bundled Definitions (reincheck/data/harnesses.json)

```json
{
  "harnesses": {
    "claude": {
      "display_name": "Claude Code",
      "description": "Anthropic's AI coding assistant",
      "github_repo": "anthropics/claude-code"
    },
    "amp": {
      "display_name": "Amp",
      "description": "Sourcegraph Amp - Agentic CLI tool",
      "github_repo": "sourcegraph/amp"
    }
  }
}
```

### Bundled Install Methods (reincheck/data/methods.json)

```json
{
  "methods": {
    "claude.mise_binary": {
      "install": "mise use -g claude-code@latest",
      "upgrade": "mise use -g claude-code@latest",
      "version": "claude --version",
      "check_latest": "mise ls-remote claude-code | tail -n1",
      "dependencies": ["mise"],
      "risk_level": "safe"
    },
    "claude.mise_language": {
      "install": "mise use -g npm:@anthropic-ai/claude-code",
      "upgrade": "mise use -g npm:@anthropic-ai/claude-code@latest",
      "version": "claude --version", 
      "check_latest": "npm info @anthropic-ai/claude-code version",
      "dependencies": ["mise"],
      "risk_level": "safe"
    },
    "claude.npm": {
      "install": "npm install -g @anthropic-ai/claude-code",
      "upgrade": "npm update -g @anthropic-ai/claude-code",
      "version": "claude --version",
      "check_latest": "npm info @anthropic-ai/claude-code version",
      "dependencies": ["npm"],
      "risk_level": "safe"
    },
    "droid.recommended": {
      "install": "curl -fsSL https://app.factory.ai/cli | sh",
      "upgrade": "curl -fsSL https://app.factory.ai/cli | sh",
      "version": "droid --version",
      "check_latest": "curl -fsSL https://app.factory.ai/cli | grep 'VER=' | head -n 1 | cut -d'\"' -f2",
      "dependencies": ["curl"],
      "risk_level": "dangerous"
    }
  }
}
```

### Bundled Presets (reincheck/data/presets.json)

```json
{
  "presets": {
    "mise_binary": {
      "strategy": "mise",
      "description": "Uses mise package manager, prefers precompiled binaries",
      "methods": {
        "claude": "mise_binary",
        "amp": "mise_language",
        "aider": "mise_language",
        "droid": "recommended",
        "goose": "recommended"
      },
      "fallback_strategy": "language"
    },
    "language": {
      "strategy": "language",
      "description": "Uses native language package managers (npm, pip, uv)",
      "methods": {
        "claude": "npm",
        "amp": "npm",
        "aider": "uv",
        "interpreter": "uv"
      },
      "fallback_strategy": "recommended"
    },
    "recommended": {
      "strategy": "vendor",
      "description": "Uses developer-recommended install methods (may include curl|sh)",
      "methods": {
        "claude": "mise_binary",
        "droid": "recommended",
        "goose": "recommended",
        "roo": "recommended"
      }
    }
  }
}
```

## Backward Compatibility

### Current Format (agents.yaml)

The current format is a flat list where each agent has exactly one installation method baked in:

```yaml
agents:
  - name: claude
    description: Claude Code - Anthropic's AI coding assistant
    install_command: mise use -g npm:@anthropic-ai/claude-code
    version_command: claude --version
    check_latest_command: npm info @anthropic-ai/claude-code version
    upgrade_command: mise use -g npm:@anthropic-ai/claude-code@latest
    latest_version: 2.1.31
```

### Migration Strategy

1. **Detection**: If `~/.config/reincheck/config.json` doesn't exist but `agents.yaml` does, offer migration
2. **Auto-convert**: The old format maps to a "custom" preset:
   - Each agent's commands become a custom install method
   - `latest_version` moves to `latest_versions` in config
3. **Preserve**: Keep old `agents.yaml` as backup during transition
4. **Dual-read**: For one major version, support both formats (JSON takes precedence)

### Migration Code Sketch

```python
def migrate_from_yaml(yaml_path: Path, json_path: Path) -> bool:
    """Migrate old agents.yaml to new config.json format."""
    
    with open(yaml_path) as f:
        old_data = yaml.safe_load(f)
    
    new_config = {
        "preset": "custom_migrated",
        "overrides": {},
        "latest_versions": {}
    }
    
    custom_methods = {}
    
    for agent in old_data["agents"]:
        name = agent["name"]
        
        # Extract version
        if agent.get("latest_version"):
            new_config["latest_versions"][name] = agent["latest_version"]
        
        # Create custom method
        custom_methods[f"{name}.custom"] = {
            "install": agent["install_command"],
            "upgrade": agent["upgrade_command"],
            "version": agent["version_command"],
            "check_latest": agent["check_latest_command"],
            "dependencies": infer_dependencies(agent["install_command"]),
            "risk_level": infer_risk_level(agent["install_command"])
        }
        
        new_config["overrides"][name] = "custom"
    
    # Write new config
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(new_config, f, indent=2)
    
    # Write custom methods to user methods file
    methods_path = json_path.parent / "custom_methods.json"
    with open(methods_path, "w") as f:
        json.dump({"methods": custom_methods}, f, indent=2)
    
    return True
```

## Error Handling

### Dependency Errors
- Missing dependency: warn but don't block (user might install it)
- Command failure during scan: treat as unavailable, log warning

### Execution Errors
- Single step failure: log, continue with remaining steps, summarize at end
- Timeout: kill process, report as failure, continue
- curl|sh failure: extra prominent warning, suggest manual intervention

### Config Errors
- Parse error: show line/column from preprocessor, suggest `reincheck config fmt`
- Schema error: identify which field failed validation
- Missing required field: provide sensible default or clear error

## Security Considerations

1. **curl|sh commands**: Always require explicit confirmation (even with --yes flag)
2. **Command validation**: Reject commands with dangerous metacharacters ($(), backticks)
3. **Config validation**: Schema validation before any execution
4. **No shell injection**: Commands are validated before storage, never interpolated unsafely

## Implementation Order

1. **reincheck-gaq**: JSON parser with tolerant preprocessing (blocks everything)
2. **reincheck-ib5**: Dataclass definitions based on this design
3. **reincheck-gg2**: Installer engine (plan_install, render_plan, apply_plan)
4. **reincheck-pgf**: Dependency scanning framework
5. **reincheck-lyp/e19/adq**: Research tasks to populate methods.json
6. **reincheck-2oz**: Define actual preset contents
7. **reincheck-wx1**: Config path migration
8. **reincheck-rd3**: Non-interactive setup command
9. **reincheck-xi8**: Interactive TUI (optional, P2)

## Open Questions

1. **Method naming convention**: Should methods be `{harness}.{strategy}` or `{strategy}.{harness}`?
   - **Decision**: `{harness}.{method_name}` - groups all methods for a harness together

2. **Where to store custom methods?**: Bundled data vs user config
   - **Decision**: Bundled in package, user overrides in ~/.config/reincheck/

3. **Fallback chains**: How deep can fallbacks go?
   - **Decision**: Single fallback only. If that fails, error out.

4. **Version checking frequency**: Cache expiry for latest_versions?
   - **Decision**: No expiry; explicit `reincheck update` required

---

## Appendix: Example Session

```
$ reincheck setup

Scanning system dependencies...
  ✅ mise (v2024.12.1)
  ✅ npm (v10.8.0)
  ✅ curl (v8.5.0)
  ❌ brew (not found)

Available presets:
  🟢 mise_binary - Uses mise package manager, prefers binaries
  🟢 mise_language - Uses mise with language backends (npm:, pipx:)
  🟡 homebrew - Uses Homebrew (requires: brew)
  🟢 language - Uses npm, uv, pip directly
  🟡 recommended - Developer-recommended (includes curl|sh scripts)

Select preset [mise_binary]: mise_binary

Select harnesses to install (space to toggle, enter to confirm):
  [x] claude
  [x] amp
  [ ] gemini
  [x] aider
  [ ] droid

Generating plan...

Installation Plan: mise_binary

Steps:
  1. 🟢 claude
     $ mise use -g npm:@anthropic-ai/claude-code
  2. 🟢 amp
     $ mise use --global npm:@sourcegraph/amp
  3. 🟢 aider
     $ mise use --global pipx:aider-chat

Proceed with installation? [Y/n]: y

Installing claude... ✅ (v2.1.31)
Installing amp... ✅ (v0.0.1770300461)
Installing aider... ✅ (v0.9.0)

Setup complete! Run 'reincheck check' to verify installations.
```

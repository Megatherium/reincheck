# Reincheck Setup Guide

The `setup` command is designed to help you configure `reincheck` to manage your AI coding agents effectively. This guide provides a detailed look at how it works, the security model, and how to customize it.

## The Dependency Scan

When you run `reincheck setup`, the first thing it does is scan your system for available tools. This informs the **Preset Status**:

| Status | Meaning |
| :--- | :--- |
| **🟢 Green** | All required dependencies for the preset are found in your `PATH` and satisfy any version requirements. |
| **🟡 Partial** | Some dependencies are missing. `reincheck` will attempt to use fallback strategies for missing methods. |
| **🔴 Red** | Critical dependencies are missing. You can still select the preset, but many installations will fail. |

### Built-in Dependencies

`reincheck` scans for:
- **Package Managers**: `mise`, `brew`, `npm`, `uv`, `pipx`, `cargo`
- **Utilities**: `curl`, `jq`, `rg`, `sd`, `git`
- **Runtimes**: `python` (3.11+), `node`, `go`

## Installation Strategies

Presets are collections of installation methods. Here are the standard strategies:

1.  **mise_binary**: Prefers precompiled binaries managed by `mise`. This is usually the fastest and cleanest method.
2.  **mise_language**: Uses `mise` with language backends (e.g., `npm:`, `pipx:`).
3.  **homebrew**: Uses Homebrew formulae and casks.
4.  **language_native**: Uses `npm`, `uv`, or `pipx` directly without a wrapper.
5.  **vendor_recommended**: Uses the installation path suggested by the agent developer. This often involves `curl | sh` scripts.

## Advanced Configuration

You can customize how individual agents are installed by editing your configuration file (usually `~/.config/reincheck/agents.json`).

### Overrides

You can override the method for a specific agent:

```json
{
  "preset": "mise_binary",
  "overrides": {
    "claude": "npm",
    "droid": "recommended"
  }
}
```

### Custom Commands

For full control, you can override specific commands:

```json
{
  "overrides": {
    "claude": {
      "commands": {
        "install": "pnpm add -g @anthropic-ai/claude-code",
        "upgrade": "pnpm update -g @anthropic-ai/claude-code"
      }
    }
  }
}
```

## Security & Auditing

`reincheck` is designed to be transparent about what it runs.

### Risk Levels

Every installation method is assigned a risk level:
- **SAFE**: Standard package managers (`mise`, `brew`, `npm`).
- **INTERACTIVE**: May prompt for input or sudo.
- **DANGEROUS**: Arbitrary code execution (e.g., `curl | sh`).

### Auditing the Plan

Before any command is executed, `reincheck` generates an **Installation Plan**. You can view this without executing anything by using:

```bash
reincheck setup --dry-run
```

The plan displays:
1.  **Risk Icons**: 🟢 (Safe), 🟡 (Interactive), 🔴 (Dangerous).
2.  **Missing Dependencies**: Warnings if the command is likely to fail.
3.  **Exact Commands**: The full shell command that will be run.

### The "Dangerous" Guardrail

If a plan contains **🔴 Dangerous** steps:
- `reincheck` will highlight them in red.
- It will require an **explicit, additional confirmation** even if you used the `--yes` or `-y` flag.
- You will be prompted to review the specific `curl | sh` command before it executes.

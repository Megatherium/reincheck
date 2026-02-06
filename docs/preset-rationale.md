# Preset Design Rationale

> Generated from reincheck-2oz  
> Last updated: 2026-02-06

## Overview

This document explains the design decisions behind the preset and method configuration system.

## Preset Philosophy

### Structural Uniformity

Each preset maps **all 18 harnesses** to the same `method_name`. For example, `mise_binary` maps every harness to `<harness>.mise_binary`. If that method doesn't exist in `methods.json`, the resolver treats it as "method unavailable" and applies `fallback_strategy`.

This design choice:
1. Makes the "green/partial/red" computation straightforward
2. Keeps the UI simple - users pick a philosophy, not a matrix
3. Puts the intelligence in `methods.json` where it belongs

### Five Presets

| Preset | Description | Primary Dependency | Target User |
|--------|-------------|-------------------|-------------|
| `mise_binary` | Prebuilt binaries via mise plugins/github | mise | Power users with mise |
| `mise_language` | mise with language backends (npm:, pipx:) | mise + npm | mise users without all plugins |
| `homebrew` | Homebrew formulae/casks | brew | macOS users |
| `language_native` | Direct npm/uv/pipx | npm or uv | Users without mise |
| `vendor_recommended` | Vendor's recommended path | varies | Last resort, catch-all |

### Fallback Chain

```
mise_binary → mise_language → language_native → vendor_recommended → (error)
homebrew → language_native → vendor_recommended → (error)
```

Single-hop fallback only (per design doc). If both preset method AND fallback fail, error out.

## Method Availability Matrix

### mise_binary (3 harnesses)
Only harnesses with verified mise plugins or github: backend support:
- claude (claude-code plugin)
- goose (github:block/goose)
- roo (github:RooCodeInc/Roo-Code)

### mise_language (14 harnesses)
All NPM-based harnesses + droid + kimi:
- crush, kilocode, opencode, claude, grok, gemini, cline, continue, codex, amp
- droid (@factory/cli)
- kimi (@jacksontian/kimi-cli)

**Gap**: interpreter, openhands, aider, mistral, goose, roo (no verified mise pip/pipx pattern)

### homebrew (9 harnesses)
Harnesses with verified Homebrew formulae/casks:
- opencode (formula)
- claude (cask: claude-code)
- gemini (formula: gemini-cli)
- codex (cask)
- droid (cask)
- goose (formula: block-goose-cli)
- aider (formula)
- mistral (formula: mistral-vibe)
- kimi (formula: kimi-cli)

**Gap**: crush, kilocode, grok, cline, continue, amp, interpreter, openhands, roo

**Warning**: Do NOT add `amp.homebrew` or `grok.homebrew` - the Homebrew packages with those names are DIFFERENT TOOLS.

### language_native (17 harnesses)
All harnesses except roo have a verified npm/uv/pipx path.

**Gap**: roo (no npm/pypi distribution)

### vendor_recommended (18 harnesses)
Complete coverage - every harness has a method.

## Security Classifications

### Risk Levels

| Level | Description | Examples |
|-------|-------------|----------|
| `safe` | Package manager with registry verification | npm, brew, uv, pipx |
| `interactive` | May prompt for input | (none currently) |
| `dangerous` | curl\|sh - arbitrary code execution | droid.curl, roo.vendor_recommended |

### Dangerous Methods (require explicit confirmation)

- `claude.vendor_recommended` (curl install.sh)
- `claude.curl`
- `roo.vendor_recommended` (curl install.sh)
- `roo.curl`
- `droid.curl`
- `goose.curl`
- `amp.curl`
- `opencode.curl`

## Binary Name Mappings

Some harnesses have binary names that differ from the harness name:

| Harness | Binary |
|---------|--------|
| continue | cn |
| mistral | vibe |
| interpreter | interpreter |

## Package Name Mappings

### NPM Packages
| Harness | NPM Package |
|---------|-------------|
| crush | @charmland/crush |
| kilocode | @kilocode/cli |
| opencode | opencode-ai |
| claude | @anthropic-ai/claude-code |
| grok | @vibe-kit/grok-cli |
| gemini | @google/gemini-cli |
| cline | cline |
| continue | @continuedev/cli |
| codex | @openai/codex |
| amp | @sourcegraph/amp |
| droid | @factory/cli |
| kimi | @jacksontian/kimi-cli |

### PyPI Packages
| Harness | PyPI Package |
|---------|--------------|
| interpreter | open-interpreter |
| openhands | openhands |
| aider | aider-chat |
| mistral | mistral-vibe |
| kimi | kimi-cli |
| goose | goose-ai |

## Per-OS Considerations

### macOS
- Homebrew is the most common and reliable option
- All casks have macOS support
- Most formulae have bottle support for both ARM64 and Intel

### Linux
- Homebrew exists but is less common
- `language_native` and `mise_*` presets are more reliable
- Cask support on Linux is inconsistent
- Fallback to `language_native` is important

### Linuxbrew Cask Support

Some casks claim Linux support but may not work reliably:
- claude-code: Linux 64-bit
- droid: Linux
- codex: Linux 64-bit

Recommendation: If on Linux and using `homebrew` preset, be prepared to fall back.

## Python Version Requirements

Some Python harnesses have strict version requirements:

| Harness | Python Version |
|---------|----------------|
| interpreter | 3.10+ (3.11 recommended) |
| openhands | 3.12+ (strict) |
| aider | 3.8-3.13 |
| mistral | 3.12+ |
| kimi | 3.12-3.14 |

The `openhands.language_native` method includes `--python 3.12` to ensure compatibility.

## Future Considerations

### OS-Conditional Methods
Could extend `InstallMethod` with `os: ["macos", "linux"]` selector.

### Multi-hop Fallbacks
Currently limited to single fallback. Could extend to chains but adds complexity.

### Python Version Constraints
Could add `constraints: { python: ">=3.12" }` to methods.

## References

- Research tickets: reincheck-lyp, reincheck-e19, reincheck-adq, reincheck-sxv
- Design doc: docs/setup-design.md
- Distilled data: research/{lyp,e19,adq,sxv}/DISTILLED.yaml

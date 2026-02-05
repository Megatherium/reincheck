# Homebrew Availability Sweep (All Harnesses)

**Research Ticket**: reincheck-sxv
**Status**: DISTILLED - Ready for Implementation
**Last Updated**: 2026-02-06
**Verification Method**: Direct checks against formulae.brew.sh

## Summary

This document provides verified Homebrew availability for all 16 harnesses in reincheck. All entries have been verified directly against formulae.brew.sh (the official Homebrew registry).

**Hallucination Rate**: ~40% in source research (models claimed formulae that don't exist, confused casks vs formulas, or identified wrong tools entirely)

**Legend:**
- ✅ **Verified**: Confirmed via formulae.brew.sh
- ❌ **Not Available**: Confirmed not in Homebrew (core or cask)
- 📦 **Formula**: Core formula (brew install)
- 🍺 **Cask**: Cask (brew install --cask)

---

## Quick Reference Table

| Harness | Formula/Cask | Type | Install Command | Platform |
|---------|--------------|------|----------------|----------|
| **crush** | ❌ None | - | Use `mise use -g npm:@charmland/crush` | All |
| **kilocode** | ❌ None | - | Use `mise use -g npm:@kilocode/cli` | All |
| **opencode** | ✅ opencode | Formula | `brew install opencode` | macOS + Linux |
| **claude** | ✅ claude-code | Cask | `brew install --cask claude-code` | macOS + Linux |
| **grok** | ❌ None | - | Use `mise use -g npm:grok-cli` | All |
| **gemini** | ✅ gemini-cli | Formula | `brew install gemini-cli` | macOS + Linux |
| **cline** | ❌ None | - | Use `mise use -g npm:cline` | All |
| **continue** | ❌ None | - | Use `mise use -g npm:@continuedev/cli` | All |
| **interpreter** | ❌ None | - | Use `uv tool install open-interpreter` | All |
| **droid** | ✅ droid | Cask | `brew install --cask droid` | macOS + Linux |
| **openhands** | ❌ None | - | Use `uv tool install openhands` | All |
| **mistral** | ✅ mistral-vibe | Formula | `brew install mistral-vibe` | macOS + Linux |
| **codex** | ✅ codex | Cask | `brew install --cask codex` | macOS + Linux |
| **goose** | ✅ block-goose-cli | Formula | `brew install block-goose-cli` | macOS + Linux |
| **goose** | ✅ block-goose | Cask | `brew install --cask block-goose` | macOS only |
| **aider** | ✅ aider | Formula | `brew install aider` | macOS + Linux |
| **kimi** | ✅ kimi-cli | Formula | `brew install kimi-cli` | macOS + Linux |
| **amp** | ❌ None | - | Use `mise use -g npm:@sourcegraph/amp` | All |

**Note:** The `amp` formula in Homebrew is the amp terminal editor (amp.rs), NOT Sourcegraph Amp (the AI CLI). They are different tools.

---

## Detailed Verified Availability

### ✅ Core Formulae (brew install)

| Formula | Version | Binary | Platform Support | Analytics (30d) |
|---------|---------|--------|-----------------|-----------------|
| **opencode** | 1.1.50 | opencode | macOS (ARM64/Intel), Linux (ARM64/x86_64) | 34,720 |
| **block-goose-cli** | 1.23.0 | goose | macOS (ARM64/Intel), Linux (ARM64/x86_64) | 4,984 |
| **aider** | 0.86.1 | aider | macOS (ARM64/Intel), Linux (ARM64/x86_64) | 563 |
| **gemini-cli** | 0.27.1 | gemini | macOS (ARM64/Intel), Linux (ARM64/x86_64) | 99,859 |
| **mistral-vibe** | 2.0.2 | vibe | macOS (ARM64/Intel), Linux (ARM64/x86_64) | 832 |
| **kimi-cli** | 1.8.0 | kimi | macOS (ARM64/Intel), Linux (ARM64/x86_64) | 1,311 |

### ✅ Casks (brew install --cask)

| Cask | Version | Binary | Platform Support | Analytics (30d) | Notes |
|------|---------|--------|-----------------|-----------------|-------|
| **claude-code** | 2.1.32 | claude | macOS (ARM64/Intel), Linux (64-bit) | 124,174 | |
| **droid** | 0.57.5 | droid | macOS 10.15+, Linux | 586 | |
| **codex** | 0.98.0 | codex | macOS 10.15+, Linux (64-bit) | 48,044 | |
| **block-goose** | 1.23.0 | goose | macOS 12+ | 1,200 | Desktop app only |

### ❌ Not Available in Homebrew

| Harness | Reason | Recommended Alternative |
|---------|--------|----------------------|
| **crush** | No formula or cask | `mise use -g npm:@charmland/crush` |
| **kilocode** | No formula or cask | `mise use -g npm:@kilocode/cli` |
| **grok** | No formula or cask | `mise use -g npm:grok-cli` |
| **cline** | No formula or cask | `mise use -g npm:cline` |
| **continue** | No formula or cask | `mise use -g npm:@continuedev/cli` |
| **interpreter** | No formula or cask | `uv tool install open-interpreter` |
| **openhands** | No formula or cask | `uv tool install openhands` |
| **roo** | No formula or cask | Use VS Code extension or curl script |
| **amp** | Wrong formula exists (amp terminal editor) | `mise use -g npm:@sourcegraph/amp` |

---

## Model Accuracy Summary

| Model | Accuracy | Notable Issues |
|-------|----------|----------------|
| **ChatGPT** | 60% | Claimed crush exists (wrong), missed opencode, missed gemini-cli, claimed open-interpreter exists (wrong), missed droid cask |
| **Gemini** | 55% | Claimed open-interpreter exists (wrong), claimed openhands exists (wrong), claimed cline cask (wrong), claimed continue cask (wrong), claimed roo-code cask (wrong) |
| **Zhipu** | 65% | Got droid and aider right, but missed many formulae, claimed crush doesn't exist when it might (tap), confused codex (claimed cask exists but formula exists - actually it's cask) |

### Common Hallucinations Detected

1. **crush formula** - ChatGPT claimed `charmbracelet/tap/crush` exists - verified not in Homebrew core or official tap
2. **open-interpreter formula** - Gemini claimed `brew install open-interpreter` works - verified false
3. **openhands formula** - Gemini claimed `brew install openhands` works - verified false
4. **cline cask** - Gemini claimed `brew install --cask cline` exists - verified false
5. **continue cask** - Gemini claimed `brew install --cask continue` exists - verified false
6. **roo-code cask** - Gemini claimed `brew install --cask roo-code` exists - verified false
7. **amp formula confusion** - All models confused amp formula (terminal editor) with Sourcegraph Amp (AI CLI) - different tools!

---

## Platform Support Summary

### macOS + Linux (Formulae with Bottles)

The following formulae have precompiled binaries for both macOS and Linux:

- ✅ opencode
- ✅ block-goose-cli
- ✅ aider
- ✅ gemini-cli
- ✅ mistral-vibe
- ✅ kimi-cli

**Note:** All core formulae listed above support:
- macOS Apple Silicon (tahoe, sequoia, sonoma)
- macOS Intel (sonoma)
- Linux ARM64
- Linux x86_64

### macOS + Linux (Casks)

The following casks work on both macOS and Linux:

- ✅ claude-code
- ✅ droid
- ✅ codex

### macOS Only (Casks)

- ✅ block-goose (desktop app)

### No Homebrew Support

The following harnesses have NO Homebrew support at all:

- crush
- kilocode
- grok
- cline
- continue
- interpreter
- openhands
- roo
- amp (Sourcegraph - not the terminal editor amp)

---

## Special Notes

### amp: Identity Confusion

**CRITICAL:** The Homebrew formula `amp` is NOT Sourcegraph Amp (the AI CLI). It's the amp terminal editor (amp.rs). They are completely different tools.

**Sourcegraph Amp** (the harness):
- Package: `@sourcegraph/amp` on NPM
- Install: `mise use -g npm:@sourcegraph/amp`
- Homebrew: NOT AVAILABLE

**amp** (terminal editor):
- Formula: `amp` in Homebrew core
- Install: `brew install amp`
- Purpose: Terminal-based text editor
- URL: https://amp.rs

### grok: Deprecated Formula

A `grok` formula exists in Homebrew but is:
- Deprecated (disable date: 2027-01-11)
- NOT the grok CLI from superagent-ai
- It's a regex processing tool (jordansissel/grok)

**grok CLI** (the harness):
- Package: `grok-cli` on NPM
- Install: `mise use -g npm:grok-cli`
- Homebrew: NOT AVAILABLE

### block-goose: Dual Availability

Goose has both:
1. **Formula**: `block-goose-cli` - CLI tool
2. **Cask**: `block-goose` - Desktop app

For CLI usage, use the formula: `brew install block-goose-cli`

---

## References

All verification performed via:
- https://formulae.brew.sh/ - Official Homebrew formulae website
- Direct formula/cask page checks for each harness

---

## Implementation Notes

### Package Type Classification

```yaml
formulae:
  opencode: formula
  block-goose-cli: formula
  aider: formula
  gemini-cli: formula
  mistral-vibe: formula
  kimi-cli: formula

casks:
  claude-code: cask
  droid: cask
  codex: cask
  block-goose: cask  # Desktop app only

none:
  crush: null
  kilocode: null
  grok: null
  cline: null
  continue: null
  interpreter: null
  openhands: null
  roo: null
  amp: null  # Wrong formula exists (different tool)
```

### Installation Commands by Harness

```yaml
crush: mise use -g npm:@charmland/crush
kilocode: mise use -g npm:@kilocode/cli
opencode: brew install opencode
claude: brew install --cask claude-code
grok: mise use -g npm:grok-cli
gemini: brew install gemini-cli
cline: mise use -g npm:cline
continue: mise use -g npm:@continuedev/cli
interpreter: uv tool install open-interpreter
droid: brew install --cask droid
openhands: uv tool install openhands
mistral: brew install mistral-vibe
codex: brew install --cask codex
goose: brew install block-goose-cli
aider: brew install aider
kimi: brew install kimi-cli
roo: curl -fsSL https://raw.githubusercontent.com/RooCodeInc/Roo-Code/main/apps/cli/install.sh | sh
amp: mise use -g npm:@sourcegraph/amp  # NOT brew install amp
```

---

## Action Items for Implementation

- [ ] Update agents.yaml to reflect verified Homebrew availability
- [ ] Add warning for amp (don't use brew install amp - it's the wrong tool)
- [ ] Prioritize Homebrew methods when available in UI
- [ ] For formulae with Linux support, note cross-platform availability
- [ ] Remove any non-existent Homebrew commands from config

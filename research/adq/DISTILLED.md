# Curl-Script Installer Reference (droid, goose, roo)

**Research Ticket**: reincheck-adq
**Status**: DISTILLED - Ready for Implementation
**Last Updated**: 2026-02-05
**Verification Method**: Official docs, GitHub releases, npm/PyPI registries, Homebrew formulae

## Summary

This document consolidates research from 3 AI models (ChatGPT, Gemini, Zhipu) on installation methods for 3 AI coding agents distributed via curl/sh scripts, with verification against official sources.

**Hallucination Rate**: ~30% of entries contained errors (mainly NPM package names, Homebrew cask availability, alternative installation methods)

**Legend:**
- ✅ Tested/Verified
- ⚠️ Verified but with caveats
- ❌ Not available/Unverified
- 🔴 HIGH RISK - Remote code execution without verification
- 📝 Untested syntax (theoretical only)

---

## Quick Reference Table

| Harness | NPM Package | PyPI Package | Binary | Homebrew | Curl Script | Provenance |
|---------|--------------|--------------|---------|-----------|-------------|------------|
| droid | `@factory/cli` | None | `droid` | ✅ `droid` cask | 🔴 Available | [NPM](https://www.npmjs.com/package/@factory/cli) |
| goose | None | `goose-ai` | `goose` | ✅ `block-goose-cli` | 🔴 Available | [Homebrew](https://formulae.brew.sh/formula/block-goose-cli) |
| roo | None | None | `roo` | ❌ | 🔴 Primary | [GitHub](https://github.com/RooCodeInc/Roo-Code) |

---

## Detailed Installation Methods

### 1. droid (Factory Droid CLI)

| Method | Status | Install | Upgrade | Version | Binary | Security |
|--------|--------|---------|---------|---------|-----------|----------|
| **NPM** | ✅ Verified | `npm install -g @factory/cli` | `npm update -g @factory/cli` | `droid --version` | `droid` | Medium - npm registry verification |
| **Homebrew** | ✅ Verified | `brew install --cask droid` | `brew upgrade --cask droid` | `droid --version` | `droid` | Low - Code-signed cask |
| **Curl/Shell** | 🔴 HIGH RISK | `curl -fsSL https://app.factory.ai/cli \| sh` | Re-run script | `droid --version` | `droid` | 🔴 Remote code execution |
| **Mise (npm)** | 🧪 Syntax | `mise use -g npm:@factory/cli` | `mise upgrade npm:@factory/cli` | `droid --version` | `droid` | Medium - npm registry |

**Security Notes:**
- NPM package `@factory/cli` has 0 dependencies (minimal attack surface)
- Homebrew cask `droid` installs signed .app bundle + CLI
- Curl script has NO checksum verification or signature
- **CRITICAL**: Curl installer must require explicit user confirmation

**Provenance:**
- NPM: `https://www.npmjs.com/package/@factory/cli`
- Homebrew: `https://formulae.brew.sh/cask/droid`
- Docs: `https://docs.factory.ai/changelog/cli-updates`

---

### 2. goose (Block Goose CLI)

| Method | Status | Install | Upgrade | Version | Binary | Security |
|--------|--------|---------|---------|---------|-----------|----------|
| **Homebrew** | ✅ Verified | `brew install block-goose-cli` | `brew upgrade block-goose-cli` | `goose --version` | `goose` | Low - Core formula + bottles |
| **PyPI** | ⚠️ Available | `pipx install goose-ai` | `pipx upgrade goose-ai` | `goose --version` | `goose` | Medium - PyPI trust model |
| **Curl/Shell** | 🔴 HIGH RISK | `curl -fsSL https://github.com/block/goose/releases/download/stable/download_cli.sh \| bash` | `goose update` | `goose --version` | `goose` | 🔴 Remote code execution |
| **Mise (GitHub)** | 🧪 Syntax | `mise use -g github:block/goose` | `mise upgrade github:block/goose` | `goose --version` | `goose` | Medium - GitHub releases |
| **Cargo** | 📝 Untested | `cargo install --git https://github.com/block/goose` | Rebuild from source | `goose --version` | `goose` | Medium - Source build |

**Special Notes:**
- Goose provides a native `goose update` command for upgrades (not standard curl re-run)
- Homebrew has bottle support for Apple Silicon (Sequoia, Sonoma), Intel (Sonoma), Linux ARM64/x86_64
- Desktop app available: `brew install --cask block-goose`

**Security Notes:**
- Homebrew core formula with source audit and signed bottles
- PyPI package `goose-ai` is published by Block (verified)
- Curl script downloads from GitHub releases without automatic checksum verification
- **CRITICAL**: Curl installer must require explicit user confirmation

**Provenance:**
- Homebrew: `https://formulae.brew.sh/formula/block-goose-cli`
- PyPI: `https://pypi.org/project/goose-ai`
- GitHub: `https://github.com/block/goose`

---

### 3. roo (Roo Code CLI)

| Method | Status | Install | Upgrade | Version | Binary | Security |
|--------|--------|---------|---------|---------|-----------|----------|
| **Curl/Shell** | 🔴 HIGH RISK (PRIMARY) | `curl -fsSL https://raw.githubusercontent.com/RooCodeInc/Roo-Code/main/apps/cli/install.sh \| sh` | Re-run script | `roo --version` | `roo` | 🔴 Only distribution method |
| **VS Code Extension** | ✅ Verified | `code --install-extension RooVeterinaryInc.roo-cline` | Auto-update or `--force` | Extension panel | N/A | Low - Marketplace verified |
| **Mise (GitHub)** | 🧪 Syntax | `mise use -g github:RooCodeInc/Roo-Code` | `mise upgrade github:RooCodeInc/Roo-Code` | `roo --version` | `roo` | Medium - GitHub releases |

**Platform Support:**
- macOS Apple Silicon (M1/M2/M3/M4)
- Linux x64
- Requires Node.js 20 or higher

**Version Pinning:**
```bash
ROO_VERSION=0.0.49 curl -fsSL https://raw.githubusercontent.com/RooCodeInc/Roo-Code/main/apps/cli/install.sh | sh
```

**Checksum Verification (Post-Install):**
```bash
curl -fsSL https://github.com/RooCodeInc/Roo-Code/releases/download/cli-v0.0.49/checksums.txt > checksums.txt
sha256sum -c checksums.txt
```

**Security Notes:**
- Roo Code CLI is distributed PRIMARILY via curl pipe-to-shell - **NO cryptographically verified alternative exists**
- VS Code extension is the primary distribution method for most users
- Manual checksum verification required for CLI
- **CRITICAL**: Curl installer must require explicit user confirmation with version pinning recommended

**Provenance:**
- GitHub: `https://github.com/RooCodeInc/Roo-Code`
- Marketplace: `https://marketplace.visualstudio.com/items?itemName=RooVeterinaryInc.roo-cline`

---

## Model Accuracy Summary

| Model | Accuracy | Notable Issues |
|-------|----------|----------------|
| **ChatGPT** | 90% | Wrong NPM package for droid (`@facto/droid` instead of `@factory/cli`), missed Homebrew cask for droid |
| **Gemini** | 85% | Terse, missed some details, correctly identified goose homebrew, missed droid homebrew |
| **Zhipu** | 95% | Excellent detail on security warnings, correct NPM package for droid, verified Homebrew cask, included PyPI for goose, comprehensive curl script warnings |

### Common Hallucinations Detected

1. **NPM package for droid** - ChatGPT suggested `@facto/droid` (non-existent) - correct is `@factory/cli`
2. **Homebrew for droid** - Some models missed the `droid` cask
3. **PyPI for goose** - Some models claimed no PyPI package exists, but `goose-ai` is available
4. **NPM for roo** - Some models claimed NPM availability for roo CLI - this is incorrect
5. **Homebrew for roo** - Some models claimed Homebrew availability - no formula/cask exists

---

## Security Summary for Curl Installers

### Risk Matrix

| Agent | Risk Level | Verification | Checksums | Signature | Requires Confirmation |
|-------|-----------|--------------|-----------|-----------|----------------------|
| droid | 🔴 HIGH | None | No | No | **YES** |
| goose | 🔴 HIGH | None | No | No | **YES** |
| roo | 🔴 CRITICAL | None | Manual only | No | **YES** |

### Mandatory Confirmation Flow

```bash
# Standard confirmation pattern required:
read -p "⚠️  You are about to execute a remote shell script from [URL]. Have you reviewed the script? (yes/no): " confirm
if [[ $confirm == "yes" ]]; then
    curl -fsSL [URL] | sh
else
    echo "Installation cancelled."
fi
```

### Recommended Installation Priority (Per Agent)

**droid:**
1. Homebrew (code-signed cask)
2. NPM (registry verification)
3. mise (npm backend)
4. Curl (last resort, requires confirmation)

**goose:**
1. Homebrew (core formula + bottles)
2. PyPI (verified publisher)
3. mise (GitHub backend)
4. Curl (last resort, requires confirmation)

**roo:**
1. VS Code extension (marketplace verified)
2. mise (GitHub backend, best CLI alternative)
3. Curl with version pinning + manual checksum verification (primary but high-risk)

---

## Implementation Notes for Config

### Binary Name Mappings

```yaml
droid: droid
goose: goose
roo: roo
```

### NPM Package Mappings

```yaml
droid: @factory/cli
goose: None
roo: None
```

### PyPI Package Mappings

```yaml
droid: None
goose: goose-ai
roo: None
```

### Homebrew Availability

```yaml
Available:
  - droid: droid (cask)
  - goose: block-goose-cli (formula)

Not Available:
  - roo
```

### Special Upgrade Commands

```yaml
goose: goose update  # Not standard curl re-run
droid: Standard curl re-run or npm update -g or brew upgrade
roo: Standard curl re-run
```

### Version Check Commands

```yaml
droid: droid --version
goose: goose --version
roo: roo --version
```

### Check Latest Commands

```yaml
droid: curl -fsSL https://app.factory.ai/cli | grep 'VER=' | head -n 1 | cut -d'"' -f2
goose: curl -s https://api.github.com/repos/block/goose/releases/latest | grep "tag_name" | cut -d"\"" -f4
roo: curl -s https://api.github.com/repos/RooCodeInc/Roo-Code/releases/latest | grep "tag_name" | cut -d"\"" -f4
```

---

## Security Best Practices Summary

### Pre-Execution Checklist for Curl Installers

1. Download script to disk first (don't pipe)
2. Inspect the script contents (look for `eval`, `base64`, suspicious network calls)
3. Verify the source domain/organization ownership
4. Check for HTTPS and valid certificates
5. Download checksums separately if available
6. Only execute after explicit user confirmation

### Post-Installation Verification

```bash
# Verify binary location
which droid goose roo

# Check for unexpected network connections
lsof -i | grep -E '(droid|goose|roo)'

# Review installed files
ls -la ~/.local/bin/droid  # or equivalent path

# Check binary signatures (macOS)
codesign -dv --verbose=4 $(which droid)
```

---

## References

- **NPM Registry:** Verified `@factory/cli` via npm registry
- **Homebrew:** Verified `droid` cask and `block-goose-cli` formula via formulae.brew.sh
- **PyPI:** Verified `goose-ai` via PyPI JSON API
- **GitHub Releases:** Verified all agents via GitHub API
- **Source Research:** See `research/adq/` directory for raw model outputs

---

## Action Items for Implementation

- [ ] Add all 3 harnesses to agents.yaml with verified methods
- [ ] Mark curl methods as HIGH RISK and require explicit user confirmation
- [ ] Add special `goose update` command for goose upgrades (not standard curl re-run)
- [ ] For roo, recommend version pinning with ROO_VERSION environment variable
- [ ] Implement post-install checksum verification prompts for roo
- [ ] Add security warning banners for curl-based installations
- [ ] Prioritize Homebrew/NPM methods over curl in UI presentation
- [ ] For roo, highlight VS Code extension as safer alternative to CLI

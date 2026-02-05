# AI Coding Agents Installation & Management Guide
## Droid, Goose, and Roo Code

---

## Executive Summary

This guide provides comprehensive installation and management commands for three popular AI coding agents across multiple package managers and installation methods. **Security warnings are highlighted for curl-based installers**, which execute remote code without cryptographic verification.

---

## 1. DROID (by Factory AI)

### Overview
Droid is Factory AI's enterprise-grade coding agent with autonomous multi-step execution, spec mode for planning, and deep IDE integration.

---

### NPM Method (Recommended for JavaScript developers)

| Aspect | Details |
|--------|---------|
| **Install Command** | `npm install -g @factory/cli` |
| **Upgrade Command** | `npm update -g @factory/cli` |
| **Idempotent Upgrade** | ✅ Yes - npm handles version checks |
| **Version Check** | `droid --version` or `factory --version` |
| **Binary Name** | `droid` (primary), `factory` (alternative entry point) |
| **Homebrew Alternative** | ✅ Yes - `brew install --cask droid` |
| **Stable Binary URL** | https://app.factory.ai/cli |

**Security Notes:**
- NPM package is published to official npm registry with scoped namespace `@factory/cli`
- 0 dependencies (reduces supply chain attack surface)
- Checksum verification built into npm

---

### Homebrew Method (Recommended for macOS users)

| Aspect | Details |
|--------|---------|
| **Install Command** | `brew install --cask droid` |
| **Upgrade Command** | `brew upgrade --cask droid` |
| **Idempotent Upgrade** | ✅ Yes - Homebrew tracks versions |
| **Version Check** | `droid --version` |
| **Binary Name** | `droid` |
| **Formula Type** | Cask (installs signed .app bundle + CLI) |
| **Dependencies** | Automatically installs `ripgrep` |

**Security Notes:**
- Cask installs code-signed binaries
- Homebrew verifies checksums before installation
- Requires macOS 10.15 (Catalina) or later

---

### Curl/Shell Script Method (⚠️ HIGH RISK)

| Aspect | Details |
|--------|---------|
| **Install Command** | `curl -fsSL https://app.factory.ai/cli \| sh` |
| **Upgrade Command** | Re-run install script (auto-detects existing installation) |
| **Idempotent Upgrade** | ✅ Yes - script checks for existing installation |
| **Version Check** | `droid --version` |
| **Binary Name** | `droid` |

**⚠️ CRITICAL SECURITY WARNINGS:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ⚠️  SECURITY WARNING - CURL PIPE TO SHELL                               │
├─────────────────────────────────────────────────────────────────────────┤
│ This method executes code from a remote server without:                 │
│   • Cryptographic signature verification                                │
│   • Checksum validation                                                 │
│   • Content inspection before execution                                 │
│                                                                         │
│ Supply Chain Risks:                                                     │
│   • DNS hijacking could redirect to malicious server                    │
│   • Server compromise could serve malicious installer                   │
│   • No guarantee the script hasn't been tampered with                   │
│                                                                         │
│ BEFORE RUNNING - You MUST:                                              │
│   1. Download and inspect the script:                                   │
│      curl -fsSL https://app.factory.ai/cli > install.sh                 │
│   2. Review the script contents: less install.sh                        │
│   3. Verify the domain: app.factory.ai is controlled by Factory AI      │
│   4. Check for suspicious commands (curl, wget, eval, base64 decode)    │
│   5. Only execute after explicit user confirmation                      │
│                                                                         │
│ RECOMMENDED: Use npm or Homebrew instead for cryptographic verification │
└─────────────────────────────────────────────────────────────────────────┘
```

**Confirmation Required:** 
```bash
# User must explicitly confirm before executing:
read -p "⚠️  You are about to execute a remote shell script. Have you reviewed the script at https://app.factory.ai/cli? (yes/no): " confirm
if [[ $confirm == "yes" ]]; then
    curl -fsSL https://app.factory.ai/cli | sh
else
    echo "Installation cancelled. Use 'npm install -g @factory/cli' instead."
fi
```

---

### Mise Language Pattern Method

| Aspect | Details |
|--------|---------|
| **Install Command** | `mise use -g npm:@factory/cli` |
| **Upgrade Command** | `mise upgrade npm:@factory/cli` |
| **Idempotent Upgrade** | ✅ Yes - mise tracks tool versions |
| **Version Check** | `mise list npm:@factory/cli` or `droid --version` |
| **Binary Name** | `droid` |
| **Backend** | npm (via mise npm backend) |

**Configuration in `~/.config/mise/config.toml`:**
```toml
[tools]
"npm:@factory/cli" = "latest"
```

**Security Notes:**
- Uses npm registry with cryptographic verification
- mise isolates installations in `~/.local/share/mise/installs/`
- No shims pollution - only active when mise is activated

---

### uv Tool Method

| Aspect | Details |
|--------|---------|
| **Install Command** | None - Not applicable (not a Python package) |
| **Status** | ❌ Not supported - Droid is not published to PyPI |

---

### Pip/Pipx Method

| Aspect | Details |
|--------|---------|
| **Install Command** | None - Not applicable |
| **Status** | ❌ Not supported - No Python package available |

---

## 2. GOOSE (by Block/Square)

### Overview
Goose is Block's open-source extensible AI agent that runs locally and supports 25+ LLM providers. Contributed to Linux Foundation's Agentic AI Foundation.

---

### NPM Method

| Aspect | Details |
|--------|---------|
| **Install Command** | None - Not published to npm |
| **Status** | ❌ Not available - Goose is a Rust application |

---

### Homebrew Method (Recommended for macOS/Linux)

| Aspect | Details |
|--------|---------|
| **Install Command** | `brew install block-goose-cli` |
| **Upgrade Command** | `brew upgrade block-goose-cli` |
| **Idempotent Upgrade** | ✅ Yes - Homebrew tracks versions |
| **Version Check** | `goose --version` |
| **Binary Name** | `goose` |
| **Formula Type** | Core formula (builds from source or uses bottles) |
| **Bottle Support** | ✅ Apple Silicon (Sequoia, Sonoma), Intel (Sonoma), Linux ARM64/x86_64 |
| **Desktop App** | `brew install --cask block-goose` |

**Security Notes:**
- Homebrew core formula with source audit
- Binary bottles are built and signed by Homebrew
- Apache-2.0 licensed (open source)

---

### Curl/Shell Script Method (⚠️ HIGH RISK)

| Aspect | Details |
|--------|---------|
| **Install Command** | `curl -fsSL https://github.com/block/goose/releases/download/stable/download_cli.sh \| bash` |
| **Upgrade Command** | Re-run install script |
| **Idempotent Upgrade** | ✅ Yes - downloads latest release |
| **Version Check** | `goose --version` |
| **Binary Name** | `goose` |

**⚠️ CRITICAL SECURITY WARNINGS:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ⚠️  SECURITY WARNING - CURL PIPE TO SHELL                               │
├─────────────────────────────────────────────────────────────────────────┤
│ This script downloads and executes binaries from GitHub releases.       │
│                                                                         │
│ Supply Chain Risks:                                                     │
│   • GitHub account compromise could serve malicious releases            │
│   • No automatic checksum verification in the pipe-to-shell pattern     │
│   • TLS interception could modify the script in transit                 │
│                                                                         │
│ BEFORE RUNNING - You MUST:                                              │
│   1. Download and inspect the script:                                   │
│      curl -fsSL https://github.com/block/goose/releases/download/...    │
│        > download_cli.sh                                                │
│   2. Review what the script does (downloads binary, installs to PATH)   │
│   3. Verify the GitHub organization: github.com/block                   │
│   4. Consider downloading the binary directly from releases page        │
│                                                                         │
│ RECOMMENDED: Use Homebrew or Pipx for cryptographic verification        │
└─────────────────────────────────────────────────────────────────────────┘
```

**Confirmation Required:**
```bash
read -p "⚠️  Execute remote script from GitHub? Have you verified github.com/block/goose? (yes/no): " confirm
[[ $confirm == "yes" ]] && curl -fsSL https://github.com/block/goose/releases/download/stable/download_cli.sh | bash
```

---

### Mise Language Pattern Method

| Aspect | Details |
|--------|---------|
| **Install Command** | `mise use -g github:block/goose` |
| **Upgrade Command** | `mise upgrade github:block/goose` |
| **Idempotent Upgrade** | ✅ Yes - mise tracks GitHub releases |
| **Version Check** | `mise list github:block/goose` |
| **Binary Name** | `goose` |
| **Backend** | GitHub releases (precompiled binaries) |

**Configuration:**
```toml
[tools]
"github:block/goose" = "latest"
```

---

### uv Tool Method

| Aspect | Details |
|--------|---------|
| **Install Command** | None - Not a Python package |
| **Status** | ❌ Not applicable - Goose is written in Rust |

---

### Pip/Pipx Method (Alternative Python interface)

| Aspect | Details |
|--------|---------|
| **Install Command** | `pipx install goose-ai` |
| **Upgrade Command** | `pipx upgrade goose-ai` |
| **Idempotent Upgrade** | ✅ Yes - pipx tracks versions |
| **Version Check** | `goose --version` |
| **Binary Name** | `goose` |
| **Package Name** | `goose-ai` on PyPI |

**Security Notes:**
- PyPI package is published by Block (verified)
- pipx isolates in virtual environment
- Source available at github.com/block/goose

---

### Cargo Method (Build from Source)

| Aspect | Details |
|--------|---------|
| **Install Command** | `cargo install --git https://github.com/block/goose` |
| **Upgrade Command** | `cargo install --git https://github.com/block/goose --force` |
| **Idempotent Upgrade** | ⚠️ No - always rebuilds from source |
| **Version Check** | `goose --version` |
| **Binary Name** | `goose` |
| **Build Dependencies** | Rust toolchain, pkgconf, protobuf |

---

## 3. ROO CODE (RooCodeInc)

### Overview
Roo Code is a VS Code extension that provides AI-powered coding assistance with multiple modes (Code, Architect, Ask, Debug). Now available as a standalone CLI.

---

### NPM Method (CLI only)

| Aspect | Details |
|--------|---------|
| **Install Command** | None - CLI not published to npm |
| **Status** | ❌ Not available - CLI is distributed via install script |

**Note:** Roo Code is primarily a VS Code extension installed via marketplace. A CLI version exists but is distributed via install script.

---

### Homebrew Method

| Aspect | Details |
|--------|---------|
| **Install Command** | None - No Homebrew formula |
| **Status** | ❌ Not available in Homebrew core or taps |

---

### Curl/Shell Script Method (⚠️ HIGH RISK - Primary Distribution)

| Aspect | Details |
|--------|---------|
| **Install Command** | `curl -fsSL https://raw.githubusercontent.com/RooCodeInc/Roo-Code/main/apps/cli/install.sh \| sh` |
| **Upgrade Command** | Re-run install script |
| **Idempotent Upgrade** | ✅ Yes - script overwrites existing installation |
| **Version Check** | `roo --version` |
| **Binary Name** | `roo` |
| **Platform Support** | macOS Apple Silicon (M1/M2/M3/M4), Linux x64 |
| **Requirements** | Node.js 20 or higher |

**⚠️ CRITICAL SECURITY WARNINGS:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ⚠️  SECURITY WARNING - CURL PIPE TO SHELL                               │
├─────────────────────────────────────────────────────────────────────────┤
│ This is the PRIMARY distribution method for Roo Code CLI.               │
│                                                                         │
│ Supply Chain Risks:                                                     │
│   • GitHub repository compromise could serve malicious installer        │
│   • Raw GitHub content URLs can be redirected if repository is hijacked │
│   • No cryptographic signature verification on downloaded binaries      │
│   • Script downloads and executes precompiled binaries                  │
│                                                                         │
│ BEFORE RUNNING - You MUST:                                              │
│   1. Download and inspect the install script:                           │
│      curl -fsSL https://raw.githubusercontent.com/RooCodeInc/...        │
│        > install.sh                                                     │
│   2. Review what the script downloads and where it installs             │
│   3. Verify the GitHub organization: github.com/RooCodeInc              │
│   4. Check published checksums on GitHub Releases page                  │
│   5. Consider installing specific version with ROO_VERSION env var      │
│                                                                         │
│ SPECIFIC VERSION INSTALLATION (Recommended):                            │
│   ROO_VERSION=0.0.49 curl -fsSL ... | sh                                │
│                                                                         │
│ VERIFY CHECKSUMS AFTER DOWNLOAD:                                        │
│   sha256sum roo-cli-darwin-arm64.tar.gz                                 │
│   # Compare with values published on GitHub Releases                    │
└─────────────────────────────────────────────────────────────────────────┘
```

**Confirmation Required:**
```bash
echo "⚠️  CRITICAL: Roo Code CLI is distributed via curl pipe-to-shell."
echo "This is the ONLY official distribution method."
read -p "Have you verified the GitHub organization and reviewed the install script? (yes/no): " confirm
if [[ $confirm == "yes" ]]; then
    read -p "Install specific version for better security? Enter version (e.g., 0.0.49) or 'latest': " version
    if [[ $version != "latest" ]]; then
        ROO_VERSION=$version curl -fsSL https://raw.githubusercontent.com/RooCodeInc/Roo-Code/main/apps/cli/install.sh | sh
    else
        curl -fsSL https://raw.githubusercontent.com/RooCodeInc/Roo-Code/main/apps/cli/install.sh | sh
    fi
else
    echo "Installation cancelled."
fi
```

**Checksum Verification (Post-Install):**
```bash
# Download checksums from GitHub Releases
curl -fsSL https://github.com/RooCodeInc/Roo-Code/releases/download/cli-v0.0.49/checksums.txt > checksums.txt

# Verify your binary
sha256sum -c checksums.txt
```

---

### Mise Language Pattern Method

| Aspect | Details |
|--------|---------|
| **Install Command** | `mise use -g github:RooCodeInc/Roo-Code` |
| **Upgrade Command** | `mise upgrade github:RooCodeInc/Roo-Code` |
| **Idempotent Upgrade** | ✅ Yes - mise tracks GitHub releases |
| **Version Check** | `mise list github:RooCodeInc/Roo-Code` |
| **Binary Name** | `roo` |
| **Backend** | GitHub releases |

---

### uv Tool Method

| Aspect | Details |
|--------|---------|
| **Install Command** | None - Not a Python package |
| **Status** | ❌ Not applicable |

---

### Pip/Pipx Method

| Aspect | Details |
|--------|---------|
| **Install Command** | None - Not published to PyPI |
| **Status** | ❌ Not available |

---

### VS Code Extension (Primary Distribution)

| Aspect | Details |
|--------|---------|
| **Install Command** | `code --install-extension RooVeterinaryInc.roo-cline` |
| **Upgrade Command** | Extensions auto-update by default; manual: `code --install-extension RooVeterinaryInc.roo-cline --force` |
| **Idempotent Upgrade** | ✅ Yes - VS Code handles versioning |
| **Version Check** | Extensions panel in VS Code |
| **Binary Name** | N/A (runs inside VS Code) |
| **Marketplace URL** | https://marketplace.visualstudio.com/items?itemName=RooVeterinaryInc.roo-cline |

---

## Summary Comparison Table

| Agent | NPM | Homebrew | Curl | Mise | uv | Pip/Pipx |
|-------|-----|----------|------|------|-----|----------|
| **Droid** | ✅ `@factory/cli` | ✅ `droid` cask | ⚠️ Available | ✅ `npm:@factory/cli` | ❌ N/A | ❌ N/A |
| **Goose** | ❌ N/A | ✅ `block-goose-cli` | ⚠️ Available | ✅ `github:block/goose` | ❌ N/A | ✅ `goose-ai` |
| **Roo Code** | ❌ N/A | ❌ N/A | ⚠️ **Primary** | ✅ `github:RooCodeInc/Roo-Code` | ❌ N/A | ❌ N/A |

---

## Security Best Practices Summary

### Recommended Installation Priority

1. **Homebrew** (macOS/Linux) - Cryptographic verification, signed bottles
2. **npm/pipx** (Language-specific) - Registry verification, isolated environments
3. **mise** (Version management) - Backend verification, isolated installations
4. **curl pipe-to-shell** (Last resort) - Manual verification required

### Pre-Execution Checklist for Curl Installers

```bash
# 1. Download script to file first
curl -fsSL [URL] > install_script.sh

# 2. Inspect the script
less install_script.sh

# 3. Look for suspicious patterns
grep -E '(curl|wget|eval|exec|base64 -d)' install_script.sh

# 4. Verify the source domain
whois [domain]  # Check registration

# 5. Check for HTTPS and certificate validity
curl -I -v [URL] 2>&1 | grep -E '(subject|issuer|SSL)'

# 6. Only execute after explicit confirmation
chmod +x install_script.sh
./install_script.sh
```

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

## Idempotent Upgrade Matrix

| Method | Droid | Goose | Roo Code |
|--------|-------|-------|----------|
| npm update -g | ✅ | N/A | N/A |
| brew upgrade | ✅ | ✅ | N/A |
| Re-run curl script | ✅ | ✅ | ✅ |
| mise upgrade | ✅ | ✅ | ✅ |
| pipx upgrade | N/A | ✅ | N/A |

---

## Version Check Commands Quick Reference

```bash
# Droid
droid --version
factory --version

# Goose
goose --version

# Roo Code
roo --version
```

---

## Binary Names Summary

| Agent | Binary | Alternative |
|-------|--------|-------------|
| Droid | `droid` | `factory` |
| Goose | `goose` | - |
| Roo Code | `roo` | - |

---

## Supply Chain Security Considerations

### NPM Registry (@factory/cli)
- **Publisher**: Factory AI (verified scoped package)
- **Dependencies**: 0 (minimal attack surface)
- **Verification**: npm checksums + package signatures
- **Audit**: `npm audit` available

### Homebrew Core (block-goose-cli)
- **Publisher**: Homebrew maintainers (audited)
- **Build**: Source builds + signed bottles
- **Verification**: SHA256 checksums verified by Homebrew
- **Audit**: Formula source public and reviewed

### GitHub Releases (All agents)
- **Publisher**: Official repositories
- **Verification**: Checksums published (manual verification required)
- **Risk**: No automatic verification in curl pipe-to-shell
- **Mitigation**: Download checksums separately, verify before install

### PyPI (goose-ai)
- **Publisher**: Block (verified)
- **Verification**: pip/pipx checksum verification
- **Isolation**: pipx creates isolated environment
- **Audit**: `pip audit` available

---

## Quick Reference: Secure Installation Commands

```bash
# DROID - Most Secure Options
npm install -g @factory/cli           # NPM method
brew install --cask droid              # Homebrew method
mise use -g npm:@factory/cli           # Mise method

# GOOSE - Most Secure Options
brew install block-goose-cli           # Homebrew method
pipx install goose-ai                  # Pipx method
mise use -g github:block/goose         # Mise method

# ROO CODE - Most Secure Options
# No cryptographically verified method available
# Use mise GitHub backend as most secure alternative:
mise use -g github:RooCodeInc/Roo-Code

# Or install VS Code extension:
code --install-extension RooVeterinaryInc.roo-cline
```

---

*Document generated: 2026-02-06*
*Sources: Official documentation, npm registry, Homebrew formulae, GitHub repositories*

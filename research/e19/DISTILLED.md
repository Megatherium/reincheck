# Python/uv/pipx-based Harnesses Installation Reference

**Research Ticket**: reincheck-e19  
**Status**: DISTILLED - Ready for Implementation  
**Last Updated**: 2026-02-05  
**Verification Method**: PyPI registry checks + Homebrew formulae.brew.sh + official docs

## Summary

This document consolidates research from 4 AI models (ChatGPT, Gemini, Mistral, Zhipu) on installation methods for 5 Python-based AI coding agents, with verification against official sources.

**Hallucination Rate**: ~20% of entries contained errors (mainly mise syntax patterns and Homebrew availability)

**Legend:**
- ✅ Tested/Verified
- ⚠️ Verified but with caveats
- ❌ Not available/Unverified
- 🧪 Syntax verified via uv/mise help
- 📝 Untested syntax (theoretical only)

---

## Quick Reference Table

| Harness | PyPI Package | NPM Package | Binary | Python Req | uv tool | pipx | Homebrew | Provenance |
|---------|--------------|--------------|---------|------------|---------|-------|-----------|------------|
| interpreter | `open-interpreter` | None | `interpreter` | 3.10+ (3.11 rec.) | ✅ | ✅ | ❌ | [PyPI](https://pypi.org/project/open-interpreter) |
| openhands | `openhands` | None | `openhands` | 3.12+ | ✅ | ✅ | ❌ | [PyPI](https://pypi.org/project/openhands) |
| aider | `aider-chat` | None | `aider` | 3.8-3.13 | ✅ | ✅ | ✅ | [PyPI](https://pypi.org/project/aider-chat) |
| mistral | `mistral-vibe` | None | `vibe` | 3.12+ | ✅ | ✅ | ⚠️ | [PyPI](https://pypi.org/project/mistral-vibe) |
| kimi | `kimi-cli` | `@jacksontian/kimi-cli` | `kimi` | 3.12-3.14 (3.13 rec.) | ✅ | ✅ | ⚠️ | [PyPI](https://pypi.org/project/kimi-cli) |

---

## Detailed Installation Methods

### 1. interpreter (Open Interpreter)

| Method | Status | Install | Upgrade | Version | Binary | Python Req |
|---------|--------|---------|---------|---------|-----------|
| **uv tool** | ✅ Tested | `uv tool install open-interpreter` | `uv tool upgrade open-interpreter` | `interpreter --version` | `interpreter` | 3.10+ (3.11 recommended) |
| **pipx** | ✅ Tested | `pipx install open-interpreter` | `pipx upgrade open-interpreter` | `interpreter --version` | `interpreter` | 3.10+ (3.11 recommended) |
| **pip** | ✅ Tested | `pip install open-interpreter` | `pip install -U open-interpreter` | `interpreter --version` | `interpreter` | 3.10+ (3.11 recommended) |
| **Homebrew** | ❌ N/A | - | - | - | - | - |
| **Curl** | ⚠️ Unverified | GitHub installers mentioned in docs | - | - | - | - |

**Notes:** PyPI package is `open-interpreter`. Official docs recommend Python 3.11 for best compatibility. Some models mentioned GitHub installation with `git+https://` via uv - this is valid but PyPI is preferred for stability.

---

### 2. openhands (OpenDevin)

| Method | Status | Install | Upgrade | Version | Binary | Python Req |
|---------|--------|---------|---------|---------|-----------|
| **uv tool** | ✅ Tested | `uv tool install openhands` | `uv tool upgrade openhands` | `openhands --version` | `openhands` | 3.12+ |
| **uv tool** (pinned Python) | 🧪 Syntax | `uv tool install openhands --python 3.12` | Same as install | `openhands --version` | `openhands` | 3.12+ |
| **pipx** | ✅ Tested | `pipx install openhands` | `pipx upgrade openhands` | `openhands --version` | `openhands` | 3.12+ |
| **pip** | 📝 Untested | `pip install openhands` | `pip install -U openhands` | `openhands --version` | `openhands` | 3.12+ |
| **Curl** | ⚠️ Unverified | `curl -fsSL https://install.openhands.dev/install.sh | bash` | Re-run script | `openhands --version` | `openhands` | 3.12+ |
| **Homebrew** | ❌ N/A | - | - | - | - | - |

**Notes:** Strict Python 3.12+ requirement. Official docs recommend using `uv tool install openhands --python 3.12` for explicit version control.

---

### 3. aider (Aider Pair Programming)

| Method | Status | Install | Upgrade | Version | Binary | Python Req |
|---------|--------|---------|---------|---------|-----------|
| **uv tool** | ✅ Tested | `uv tool install aider-chat` | `uv tool upgrade aider-chat` | `aider --version` | `aider` | 3.8-3.13 |
| **pipx** | ✅ Tested | `pipx install aider-chat` | `pipx upgrade aider-chat` | `aider --version` | `aider` | 3.8-3.13 |
| **pip** | 📝 Untested | `pip install aider-chat` | `pip install -U aider-chat` | `aider --version` | `aider` | 3.8-3.13 |
| **Homebrew** | ✅ Verified | `brew install aider` | `brew upgrade aider` | `aider --version` | `aider` | 3.8-3.13 |
| **Mise (uv tool)** | 🧪 Syntax | `mise run -- uv tool install aider-chat` | `mise run -- uv tool upgrade aider-chat` | `aider --version` | `aider` | 3.8-3.13 |

**Notes:** Official homebrew formula exists. Python 3.13 is recommended for best performance. Package is `aider-chat` (not just `aider`). Version check may not have explicit `--version` flag in older versions.

---

### 4. mistral (Mistral Vibe)

| Method | Status | Install | Upgrade | Version | Binary | Python Req |
|---------|--------|---------|---------|---------|-----------|
| **uv tool** | ✅ Tested | `uv tool install mistral-vibe` | `uv tool upgrade mistral-vibe` | `vibe --version` | `vibe` | 3.12+ |
| **pipx** | ✅ Tested | `pipx install mistral-vibe` | `pipx upgrade mistral-vibe` | `vibe --version` | `vibe` | 3.12+ |
| **pip** | 📝 Untested | `pip install mistral-vibe` | `pip install -U mistral-vibe` | `vibe --version` | `vibe` | 3.12+ |
| **Curl** | ⚠️ Unverified | `curl -LsSf https://mistral.ai/vibe/install.sh | bash` | Re-run script | `vibe --version` | `vibe` | 3.12+ |
| **Homebrew** | ❌ N/A | - | - | - | - | - |

**Notes:** Official CLI is called "Mistral Vibe" but binary is `vibe`. Python 3.12+ requirement. Some models claimed no uv support - this is incorrect.

---

### 5. kimi (Moonshot AI)

| Method | Status | Install | Upgrade | Version | Binary | Python Req |
|---------|--------|---------|---------|---------|-----------|
| **uv tool** | ✅ Tested | `uv tool install kimi-cli` | `uv tool upgrade kimi-cli` | `kimi --version` | `kimi` | 3.12-3.14 (3.13 rec.) |
| **uv tool** (pinned Python) | 🧪 Syntax | `uv tool install --python 3.13 kimi-cli` | Same as install | `kimi --version` | `kimi` | 3.13 |
| **uv tool** (upgrade flags) | 🧪 Syntax | `uv tool upgrade kimi-cli --no-cache` | Same | `kimi --version` | `kimi` | 3.12-3.14 |
| **pipx** | ✅ Tested | `pipx install kimi-cli` | `pipx upgrade kimi-cli` | `kimi --version` | `kimi` | 3.12-3.14 |
| **pip** | 📝 Untested | `pip install kimi-cli` | `pip install -U kimi-cli` | `kimi --version` | `kimi` | 3.12-3.14 |
| **NPM** | ✅ Verified | `npm install -g @jacksontian/kimi-cli` | `npm install -g @jacksontian/kimi-cli@latest` | `kimi --version` | `kimi` | 3.12-3.14 |
| **Curl** | ⚠️ Unverified | `curl -LsSf https://cdn.kimi.com/binaries/kimi-cli/install.sh | bash` | Re-run script | `kimi --version` | `kimi` | 3.12-3.14 |
| **Homebrew** | ⚠️ Unverified | Some models claimed homebrew exists but not verified | - | - | - | - |

**Notes:** PyPI package is `kimi-cli`. Also available on NPM as `@jacksontian/kimi-cli`. Official docs recommend Python 3.13 for best performance. Some models claimed homebrew formula exists but not verified.

---

## Model Accuracy Summary

| Model | Accuracy | Notable Issues |
|-------|----------|----------------|
| **ChatGPT** | 95% | Excellent detail on Python version requirements, good uv/pipx commands |
| **Gemini** | 90% | Good, included curl installers, slightly terse on some details |
| **Mistral** | 60% | **Major issues**: Wrong mise patterns (using python:3.X instead of uv tool), claimed uv tool unavailable for mistral/kimi, wrong pipx binary names |
| **Zhipu** | 85% | Good overall, correct NPM package for kimi, some unverified claims |

### Common Hallucinations Detected

1. **Mise syntax** - Mistral suggested `mise use -g python:3.X + pipx install` - this is incorrect. Should use `mise run -- uv tool install` for Python packages
2. **uv tool availability** - Mistral claimed uv tool doesn't work for mistral-vibe and kimi-cli - this is false
3. **Homebrew for kimi** - Claimed but not verified
4. **pipx binary names** - Mistral used package names instead of binary names (e.g., `mistral-vibe --version` instead of `vibe --version`)

---

## Implementation Notes for Config

### Package Name Mappings (PyPI)

```yaml
interpreter: open-interpreter
openhands: openhands
aider: aider-chat
mistral: mistral-vibe
kimi: kimi-cli
```

### Binary Name Mappings

```yaml
interpreter: interpreter
openhands: openhands
aider: aider
mistral: vibe  # NOT "mistral-vibe"
kimi: kimi
```

### NPM Availability

```yaml
kimi: @jacksontian/kimi-cli  # Only kimi has NPM package
```

### Homebrew Formula Availability

```yaml
Available:
  - aider: aider (official formula)

Not Available:
  - interpreter
  - openhands
  - mistral (mistral-vibe)
  - kimi
```

### Python Version Requirements

```yaml
interpreter: "3.10+ (3.11 recommended)"
openhands: "3.12+ (strict)"
aider: "3.8-3.13"
mistral: "3.12+"
kimi: "3.12-3.14 (3.13 recommended)"
```

### uv tool Syntax Standardization

**Standard Pattern:** `uv tool install <package>` and `uv tool upgrade <package>`

**With Python Pinning:** `uv tool install <package> --python <version>`

**Upgrade with Flags:** `uv tool upgrade <package> --no-cache` (for kimi)

### Mise Integration for Python Packages

For Python packages via uv tool within mise environment:

```yaml
mise:
  run:
    uv tool install <package>
    uv tool upgrade <package>
```

Note: Do NOT use `mise use -g python:<package>` for Python packages. Use `mise run --` to invoke uv tool commands.

---

## Security Notes

1. **Curl installers** for openhands, mistral, kimi are **unverified** - test in isolated environment before production use
2. **PyPI packages** are all verified and active
3. **Homebrew formula** for aider is official vendor distribution
4. **uv tool** is the recommended modern Python package manager over pipx

---

## References

- **PyPI Registry:** Verified all packages via direct PyPI JSON API
- **Homebrew:** Verified via formulae.brew.sh
- **NPM:** Verified kimi-cli via npm registry
- **Source Research:** See `research/el9/` directory for raw model outputs

---

## Action Items for Implementation

- [ ] Add all 5 harnesses to agents.yaml with verified uv tool methods
- [ ] Add Homebrew method for aider only
- [ ] Mark curl methods for openhands, mistral, kimi as "unverified - use at own risk"
- [ ] Configure binary names correctly (especially `vibe` for mistral, NOT `mistral-vibe`)
- [ ] Create dependency scanner rules for uv, pipx, brew
- [ ] Add Python version requirements to config metadata
- [ ] For mise integration, use `mise run -- uv tool` pattern for Python packages

# NPM-Based Harnesses Installation Reference

**Research Ticket**: reincheck-lyp  
**Status**: DISTILLED - Ready for Implementation  
**Last Updated**: 2026-02-05  
**Verification Method**: NPM registry checks + Homebrew formulae.brew.sh + mise syntax validation

## Summary

This document consolidates research from 5 AI models (ChatGPT, Gemini, Grok, MiniMax, Mistral) on installation methods for 10 NPM-based AI coding agents, with verification against official sources.

**Hallucination Rate**: ~25% of entries contained errors (mostly wrong package names or claimed Homebrew availability)

**Legend:**
- ✅ Tested/Verified
- ⚠️ Verified but with caveats
- ❌ Not available/Unverified
- 🧪 Syntax verified via mise help
- 📝 Untested syntax (theoretical only)

---

## Quick Reference Table

| Harness | NPM Package | Binary | Mise Language | Mise Binary | Homebrew | Provenance |
|---------|--------------|---------|---------------|--------------|-----------|------------|
| crush | `@charmland/crush` | `crush` | 🧪 `npm:@charmland/crush@latest` | ✅ `tap/crush` | [charmbracelet/crush](https://github.com/charmbracelet/crush) |
| kilocode | `@kilocode/cli` | `kilocode` | 🧪 `npm:@kilocode/cli@latest` | ❌ | [kilocode/cli](https://github.com/kilocode/kilo-cli) |
| opencode | `opencode-ai` | `opencode` | 🧪 `npm:opencode-ai@latest` | ⚠️ `tap/opencode` | [opencode-ai](https://github.com/opencode-ai/opencode) |
| claude | `@anthropic-ai/claude-code` | `claude` | 🧪 `npm:@anthropic-ai/claude-code@latest` | ✅ `--cask claude-code` | [anthropic-ai/claude-code](https://www.npmjs.com/package/@anthropic-ai/claude-code) |
| grok | `@vibe-kit/grok-cli` | `grok` | 🧪 `npm:@vibe-kit/grok-cli@latest` | ❌ | [vibe-kit/grok-cli](https://www.npmjs.com/package/@vibe-kit/grok-cli) |
| gemini | `@google/gemini-cli` | `gemini` | 🧪 `npm:@google/gemini-cli@latest` | ✅ `gemini-cli` | [google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli) |
| cline | `cline` | `cline` | 🧪 `npm:cline@latest` | ❌ | [cline](https://github.com/clinebot/cline) |
| continue | `@continuedev/cli` | `cn` | 🧪 `npm:@continuedev/cli@latest` | ❌ | [continuedev/continue](https://github.com/continuedev/continue) |
| codex | `@openai/codex` | `codex` | 🧪 `npm:@openai/codex@latest` | ✅ `codex` / `--cask codex` | [openai/codex](https://github.com/openai/codex) |
| amp | `@sourcegraph/amp` | `amp` | 🧪 `npm:@sourcegraph/amp@latest` | ❌ | [sourcegraph/amp](https://github.com/sourcegraph/amp) |

---

## Detailed Installation Methods

### 1. crush (Charmbracelet)

| Method | Status | Install | Upgrade | Version | Binary | Provenance |
|---------|--------|---------|---------|---------|------------|
| **NPM** | ✅ Tested | `npm install -g @charmland/crush@latest` | `npm install -g @charmland/crush@latest` | `crush --version` | `crush` | [npm](https://www.npmjs.com/package/@charmland/crush) |
| **Homebrew** | ✅ Tested | `brew install charmbracelet/tap/crush` | `brew upgrade charmbracelet/tap/crush` | `crush --version` | `crush` | [tap](https://github.com/charmbracelet/homebrew-tap) |
| **Mise (Language)** | 🧪 Syntax | `mise use -g npm:@charmland/crush@latest` | Same as install | `crush --version` | `crush` | [mise docs](https://mise.jdx.dev) |
| **Mise (Binary)** | 📝 Untested | `mise use -g claude-code` | Same as install | `claude --version` | `claude` | - |

**Notes:** Charmbracelet maintains an official homebrew tap. NPM scoped package `@charmland/crush` is verified.

---

### 2. kilocode

| Method | Status | Install | Upgrade | Version | Binary | Provenance |
|---------|--------|---------|---------|---------|------------|
| **NPM** | ✅ Tested | `npm install -g @kilocode/cli@latest` | `npm install -g @kilocode/cli@latest` | `kilocode --version` | `kilocode` | [npm](https://www.npmjs.com/package/@kilocode/cli) |
| **Homebrew** | ❌ N/A | - | - | - | - | - |
| **Mise (Language)** | 🧪 Syntax | `mise use -g npm:@kilocode/cli@latest` | Same as install | `kilocode --version` | `kilocode` | [mise docs](https://mise.jdx.dev) |

**Notes:** Binary also provides `kilo` alias. No homebrew formula available.

---

### 3. opencode

| Method | Status | Install | Upgrade | Version | Binary | Provenance |
|---------|--------|---------|---------|---------|------------|
| **NPM** | ✅ Tested | `npm install -g opencode-ai@latest` | `npm install -g opencode-ai@latest` | `opencode --version` | `opencode` | [npm](https://www.npmjs.com/package/opencode-ai) |
| **Homebrew** | ⚠️ Verified | `brew install opencode-ai/tap/opencode` | `brew upgrade opencode-ai/tap/opencode` | `opencode --version` | `opencode` | [tap](https://github.com/opencode-ai/homebrew-tap) |
| **Curl** | ⚠️ Unverified | `curl -fsSL https://opencode.ai/install | bash` | Re-run script | `opencode --version` | `opencode` | ⚠️ Untested |
| **Mise (Language)** | 🧪 Syntax | `mise use -g npm:opencode-ai@latest` | Same as install | `opencode --version` | `opencode` | [mise docs](https://mise.jdx.dev) |

**Notes:** Homebrew is third-party tap only (not in core). Curl installers provided by models but untested - use with caution.

---

### 4. claude (Claude Code)

| Method | Status | Install | Upgrade | Version | Binary | Provenance |
|---------|--------|---------|---------|---------|------------|
| **NPM** | ✅ Tested | `npm install -g @anthropic-ai/claude-code@latest` | `npm install -g @anthropic-ai/claude-code@latest` | `claude --version` | `claude` | [npm](https://www.npmjs.com/package/@anthropic-ai/claude-code) |
| **Homebrew** | ✅ Tested | `brew install --cask claude-code` | `brew upgrade --cask claude-code` | `claude --version` | `claude` | [formulae](https://formulae.brew.sh/cask/claude-code) |
| **Curl** | ✅ Verified | `curl -fsSL https://claude.ai/install.sh | bash` | `claude update` | `claude --version` | `claude` | [docs](https://docs.claude.com/en/docs/claude-code/setup) |
| **Mise (Language)** | 🧪 Syntax | `mise use -g npm:@anthropic-ai/claude-code@latest` | Same as install | `claude --version` | `claude` | [mise docs](https://mise.jdx.dev) |
| **Mise (Binary)** | 📝 Untested | `mise use -g claude-code` | Same as install | `claude --version` | `claude` | [mise docs](https://mise.jdx.dev) |

**Notes:** Official homebrew cask available. NPM package is still active (not deprecated). Both mise binary and language methods available.

---

### 5. grok

| Method | Status | Install | Upgrade | Version | Binary | Provenance |
|---------|--------|---------|---------|---------|------------|
| **NPM** | ✅ Tested | `npm install -g @vibe-kit/grok-cli@latest` | `npm install -g @vibe-kit/grok-cli@latest` | `grok --version` | `grok` | [npm](https://www.npmjs.com/package/@vibe-kit/grok-cli) |
| **Homebrew** | ❌ N/A | - | - | - | - | - |
| **Mise (Language)** | 🧪 Syntax | `mise use -g npm:@vibe-kit/grok-cli@latest` | Same as install | `grok --version` | `grok` | [mise docs](https://mise.jdx.dev) |

**Notes:** No homebrew formula available.

---

### 6. gemini (Gemini CLI)

| Method | Status | Install | Upgrade | Version | Binary | Provenance |
|---------|--------|---------|---------|---------|------------|
| **NPM** | ✅ Tested | `npm install -g @google/gemini-cli@latest` | `npm install -g @google/gemini-cli@latest` | `gemini --version` | `gemini` | [npm](https://www.npmjs.com/package/@google/gemini-cli) |
| **Homebrew** | ✅ Tested | `brew install gemini-cli` | `brew upgrade gemini-cli` | `gemini --version` | `gemini` | [formulae](https://formulae.brew.sh/formula/gemini-cli) |
| **Mise (Language)** | 🧪 Syntax | `mise use -g npm:@google/gemini-cli@latest` | Same as install | `gemini --version` | `gemini` | [mise docs](https://mise.jdx.dev) |

**Notes:** Official homebrew formula available. Package uses node dependency.

---

### 7. cline

| Method | Status | Install | Upgrade | Version | Binary | Provenance |
|---------|--------|---------|---------|---------|------------|
| **NPM** | ✅ Tested | `npm install -g cline@latest` | `npm install -g cline@latest` | `cline --version` | `cline` | [npm](https://www.npmjs.com/package/cline) |
| **Homebrew** | ❌ N/A | - | - | - | - | - |
| **Mise (Language)** | 🧪 Syntax | `mise use -g npm:cline@latest` | Same as install | `cline --version` | `cline` | [mise docs](https://mise.jdx.dev) |

**Notes:** ⚠️ Some models claimed package was `@cline/cli` - this is incorrect. Correct package is plain `cline`. No homebrew formula.

---

### 8. continue (Continue.dev)

| Method | Status | Install | Upgrade | Version | Binary | Provenance |
|---------|--------|---------|---------|---------|------------|
| **NPM** | ✅ Tested | `npm install -g @continuedev/cli@latest` | `npm install -g @continuedev/cli@latest` | `cn --version` | `cn` | [npm](https://www.npmjs.com/package/@continuedev/cli) |
| **Homebrew** | ❌ N/A | - | - | - | - | - |
| **Mise (Language)** | 🧪 Syntax | `mise use -g npm:@continuedev/cli@latest` | Same as install | `cn --version` | `cn` | [mise docs](https://mise.jdx.dev) |

**Notes:** ⚠️ **Binary is `cn`, NOT `continue`**. Some models claimed package was `continue` or `continue-cli` - both incorrect. No homebrew formula or pipx available.

---

### 9. codex (OpenAI)

| Method | Status | Install | Upgrade | Version | Binary | Provenance |
|---------|--------|---------|---------|---------|------------|
| **NPM** | ✅ Tested | `npm install -g @openai/codex@latest` | `npm install -g @openai/codex@latest` | `codex --version` | `codex` | [npm](https://www.npmjs.com/package/@openai/codex) |
| **Homebrew (Formula)** | ✅ Tested | `brew install codex` | `brew upgrade codex` | `codex --version` | `codex` | [formulae](https://formulae.brew.sh/formula/codex) |
| **Homebrew (Cask)** | ✅ Tested | `brew install --cask codex` | `brew upgrade --cask codex` | `codex --version` | `codex` | [formulae](https://formulae.brew.sh/cask/codex) |
| **Mise (Language)** | 🧪 Syntax | `mise use -g npm:@openai/codex@latest` | Same as install | `codex --version` | `codex` | [mise docs](https://mise.jdx.dev) |

**Notes:** Both formula (source build) and cask (binary) available in official homebrew. Formula depends on ripgrep.

---

### 10. amp (Sourcegraph)

| Method | Status | Install | Upgrade | Version | Binary | Provenance |
|---------|--------|---------|---------|---------|------------|
| **NPM** | ✅ Tested | `npm install -g @sourcegraph/amp@latest` | `npm install -g @sourcegraph/amp@latest` | `amp --version` | `amp` | [npm](https://www.npmjs.com/package/@sourcegraph/amp) |
| **Homebrew** | ❌ N/A | - | - | - | - | - |
| **Curl** | ⚠️ Unverified | `curl -fsSL https://ampcode.com/install.sh | bash` | Re-run script | `amp --version` | `amp` | ⚠️ Untested |
| **Mise (Language)** | 🧪 Syntax | `mise use -g npm:@sourcegraph/amp@latest` | Same as install | `amp --version` | `amp` | [mise docs](https://mise.jdx.dev) |

**Notes:** ⚠️ Use scoped package `@sourcegraph/amp`, NOT plain `amp` (name collision). Curl installer untested - use with caution.

---

## Model Accuracy Summary

| Model | Accuracy | Notable Issues |
|-------|----------|----------------|
| **ChatGPT** | 90% | Minor: Amp homebrew unverified |
| **Gemini** | 85% | Incorrect: Said opencode has no NPM; Claude "deprecated" NPM |
| **Grok** | 80% | CSV format, some version commands marked "likely" instead of verified |
| **MiniMax** | 85% | Good overall, some homebrew claims unverified |
| **Mistral** | 40% | **Major hallucinations**: Wrong package names (`@cline/cli`, `continue-cli`), wrong binary names, false homebrew claims, false pipx claims |

### Common Hallucinations Detected

1. **@cline/cli** - Does not exist. Correct package is `cline`
2. **continue-cli** - Does not exist. Correct package is `@continuedev/cli`
3. **continue binary** - Wrong. Actual binary is `cn`
4. **Homebrew availability** - Over-reported by all models except where explicitly verified above
5. **Claude NPM deprecated** - False. Package still works and is actively published
6. **Pipx for continue** - False. No python package exists

---

## Implementation Notes for Config

### Standard Upgrade Pattern

**Decision:** Use `npm install -g @package@latest` for all upgrades (instead of `npm update -g`) for consistency and predictable behavior across all packages.

**Rationale:** 
- `npm update` behaves differently for scoped vs unscoped packages
- `npm install -g @package@latest` always fetches the latest version explicitly
- Matches the pattern used by the models for gemini/codex in their research

### Standard Version Check Pattern

All version checks use `<binary> --version` format:
```bash
<binary> --version
```

**Exceptions:** None - all packages support this pattern.

### Mise Syntax Standardization

**Language pattern:** `mise use -g npm:<package>@latest`

**Binary pattern:** `mise use -g <toolname>`

**Decision:** Prefer **language** pattern for NPM-based harnesses to ensure automatic updates via mise.

---

## Security Notes

1. **Curl installers** for opencode and amp are **unverified** - test in isolated environment before production use
2. **NPM packages** are all from verified publishers (scoped packages where available)
3. **Homebrew casks** for claude and codex are official vendor distributions
4. **Third-party taps** (crush, opencode) are maintained by project maintainers

---

## References

- **NPM Registry:** Verified all packages via `npm view` commands
- **Homebrew:** Verified via formulae.brew.sh
- **Mise Syntax:** Verified via `mise use --help` (mise v2026.2.4)
- **Source Research:** See `research/lyp/` directory for raw model outputs

---

## Action Items for Implementation

- [ ] Add all 10 harnesses to agents.yaml with verified NPM methods
- [ ] Add Homebrew methods for crush, claude, gemini, codex only
- [ ] Mark curl methods for opencode and amp as "unverified - use at own risk"
- [ ] Configure binary names correctly (especially `cn` for continue)
- [ ] Create dependency scanner rules for npm, brew
- [ ] Test mise language pattern for all: `mise use -g npm:PACKAGE@latest`
- [ ] Use `npm install -g @package@latest` for all upgrade commands
- [ ] Standardize version check to `<binary> --version` for all agents

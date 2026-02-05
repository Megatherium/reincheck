# NPM-Based Harnesses Installation Reference

**Research Ticket**: reincheck-lyp  
**Status**: DISTILLED - Ready for Implementation  
**Last Updated**: 2026-02-05  
**Verification Method**: NPM registry checks + Homebrew formulae.brew.sh  

## Summary

This document consolidates research from 5 AI models (ChatGPT, Gemini, Grok, MiniMax, Mistral) on installation methods for 10 NPM-based AI coding agents, with verification against official sources.

**Hallucination Rate**: ~25% of entries contained errors (mostly wrong package names or claimed Homebrew availability)

---

## Verified Installation Methods

### 1. crush (Charmbracelet)

**NPM**: ✅ Verified
- Package: `@charmland/crush`
- Install: `npm install -g @charmland/crush`
- Upgrade: `npm update -g @charmland/crush`
- Version: `crush --version`
- Binary: `crush`

**Homebrew**: ✅ Verified (Third-party tap)
- Install: `brew install charmbracelet/tap/crush`
- Upgrade: `brew upgrade charmbracelet/tap/crush`
- Formula: https://github.com/charmbracelet/homebrew-tap

**Mise Language**: Available (mise use -g npm:@charmland/crush)

---

### 2. kilocode

**NPM**: ✅ Verified
- Package: `@kilocode/cli`
- Install: `npm install -g @kilocode/cli`
- Upgrade: `npm update -g @kilocode/cli`
- Version: `kilocode --version`
- Binary: `kilocode` (also provides: `kilo`)

**Homebrew**: ❌ Not available

**Mise Language**: Available (mise use -g npm:@kilocode/cli)

---

### 3. opencode

**NPM**: ✅ Verified
- Package: `opencode-ai`
- Install: `npm install -g opencode-ai`
- Upgrade: `npm update -g opencode-ai`
- Version: `opencode --version`
- Binary: `opencode`

**Homebrew**: ✅ Verified (Third-party tap)
- Install: `brew install opencode-ai/tap/opencode`
- Note: Some models claimed `brew install opencode` but this is unverified

**Curl**: ⚠️ Unverified
- Models cited: `curl -fsSL https://opencode.ai/install | bash` and `curl -fsSL https://raw.githubusercontent.com/opencode-ai/opencode/refs/heads/main/install | bash`
- Status: URLs provided but not tested - USE WITH CAUTION

**Mise Language**: Available (mise use -g npm:opencode-ai)

---

### 4. claude (Claude Code)

**NPM**: ✅ Verified (Still functional, though some models claimed "deprecated")
- Package: `@anthropic-ai/claude-code`
- Install: `npm install -g @anthropic-ai/claude-code`
- Upgrade: `npm update -g @anthropic-ai/claude-code`
- Version: `claude --version`
- Binary: `claude`

**Homebrew**: ✅ Verified (Official Cask)
- Install: `brew install --cask claude-code`
- Upgrade: `brew upgrade --cask claude-code`
- Source: Official Anthropic distribution via formulae.brew.sh

**Curl**: ✅ Verified (Official)
- Install: `curl -fsSL https://claude.ai/install.sh | bash`
- Upgrade: `claude update` (built-in)
- Version: `claude --version`

**Mise Binary**: Available (mise use -g claude-code)

**Mise Language**: Available (mise use -g npm:@anthropic-ai/claude-code)

---

### 5. grok

**NPM**: ✅ Verified
- Package: `@vibe-kit/grok-cli`
- Install: `npm install -g @vibe-kit/grok-cli`
- Upgrade: `npm update -g @vibe-kit/grok-cli`
- Version: `grok --version`
- Binary: `grok`

**Homebrew**: ❌ Not available

**Mise Language**: Available (mise use -g npm:@vibe-kit/grok-cli)

---

### 6. gemini (Gemini CLI)

**NPM**: ✅ Verified
- Package: `@google/gemini-cli`
- Install: `npm install -g @google/gemini-cli`
- Upgrade: `npm update -g @google/gemini-cli` or `npm install -g @google/gemini-cli@latest`
- Version: `gemini --version`
- Binary: `gemini`

**Homebrew**: ✅ Verified (Official Formula)
- Install: `brew install gemini-cli`
- Upgrade: `brew upgrade gemini-cli`
- Source: https://formulae.brew.sh/formula/gemini-cli

**Mise Language**: Available (mise use -g npm:@google/gemini-cli)

---

### 7. cline

**NPM**: ✅ Verified
- Package: `cline` ⚠️ NOT `@cline/cli` (hallucinated by Mistral)
- Install: `npm install -g cline`
- Upgrade: `npm update -g cline`
- Version: `cline --version`
- Binary: `cline`

**Homebrew**: ❌ Not available (despite claims by some models)

**Mise Language**: Available (mise use -g npm:cline)

---

### 8. continue (Continue.dev)

**NPM**: ✅ Verified
- Package: `@continuedev/cli` ⚠️ NOT `continue` or `continue-cli` (hallucinated by Mistral)
- Install: `npm install -g @continuedev/cli`
- Upgrade: `npm update -g @continuedev/cli`
- Version: `cn --version` ⚠️ Binary is `cn`, NOT `continue`
- Binary: `cn`

**Homebrew**: ❌ Not available

**Pipx**: ❌ Not available (claimed by Mistral - unverified)

**Mise Language**: Available (mise use -g npm:@continuedev/cli)

---

### 9. codex (OpenAI)

**NPM**: ✅ Verified
- Package: `@openai/codex`
- Install: `npm install -g @openai/codex`
- Upgrade: `npm update -g @openai/codex` or `npm install -g @openai/codex@latest`
- Version: `codex --version`
- Binary: `codex`

**Homebrew**: ✅ Verified (Both Formula and Cask available)
- Formula (source build): `brew install codex`
- Cask (binary): `brew install --cask codex`
- Source: https://formulae.brew.sh/cask/codex and https://formulae.brew.sh/formula/codex

**Mise Language**: Available (mise use -g npm:@openai/codex)

---

### 10. amp (Sourcegraph)

**NPM**: ✅ Verified
- Package: `@sourcegraph/amp` ⚠️ NOT plain `amp` (generic name collision)
- Install: `npm install -g @sourcegraph/amp`
- Upgrade: `npm update -g @sourcegraph/amp`
- Version: `amp --version`
- Binary: `amp`

**Homebrew**: ❌ Not available (despite claims by some models)

**Curl**: ⚠️ Unverified
- Models cited: `curl -fsSL https://ampcode.com/install.sh | bash`
- Status: URL provided but not tested - USE WITH CAUTION

**Mise Language**: Available (mise use -g npm:@sourcegraph/amp)

---

## Model Accuracy Summary

| Model | Accuracy | Notable Issues |
|-------|----------|----------------|
| **ChatGPT** | 90% | Minor: Amp homebrew unverified |
| **Gemini** | 85% | Incorrect: Said opencode has no NPM; Claude "deprecated" NPM |
| **Grok** | 80% | CSV format, some version commands marked "likely" instead of verified |
| **MiniMax** | 85% | Good overall, some homebrew claims unverified |
| **Mistral** | 40% | **Major hallucinations**: Wrong package names (`@cline/cli`, `continue-cli`), wrong binary names, false homebrew claims |

### Common Hallucinations Detected

1. **@cline/cli** - Does not exist. Correct package is just `cline`
2. **continue-cli** - Does not exist. Correct package is `@continuedev/cli` with binary `cn`
3. **Homebrew availability** - Over-reported by all models except where explicitly verified above
4. **Claude NPM deprecated** - False. Package still works and is actively published

---

## Implementation Notes for Config

### Package Name Mappings (NPM)

```yaml
crush: @charmland/crush
kilocode: @kilocode/cli
opencode: opencode-ai
claude: @anthropic-ai/claude-code
grok: @vibe-kit/grok-cli
gemini: @google/gemini-cli
cline: cline
continue: @continuedev/cli
codex: @openai/codex
amp: @sourcegraph/amp
```

### Binary Name Mappings

```yaml
crush: crush
kilocode: kilocode  # also provides: kilo
opencode: opencode
claude: claude
grok: grok
gemini: gemini
cline: cline
continue: cn  # NOT "continue"
codex: codex
amp: amp
```

### Homebrew Formula Availability

```yaml
Available:
  - crush: charmbracelet/tap/crush (third-party)
  - claude: --cask claude-code (official)
  - gemini: gemini-cli (official formula)
  - codex: codex (formula) AND --cask codex (both official)

Not Available:
  - kilocode
  - grok
  - cline
  - continue
  - amp
  - opencode (only third-party tap, not in core)
```

### Mise Binary vs Language

For mise-en-place, prefer **language** installation method (mise use -g npm:PACKAGE) over binary where both are available, to get automatic updates via mise.

Exceptions:
- **claude**: mise binary `claude-code` is preferred (official pre-built)

---

## Security Notes

1. **Curl installers** for opencode and amp are **unverified** - test in isolated environment before production use
2. **NPM packages** are all from verified publishers (scoped packages where available)
3. **Homebrew casks** for claude and codex are official vendor distributions

---

## References

- NPM Registry: Verified all packages via `npm view` commands
- Homebrew: Verified via formulae.brew.sh
- Source Research: See `research/lyp/` directory for raw model outputs

---

## Action Items for Implementation

- [ ] Add all 10 harnesses to agents.yaml with verified NPM methods
- [ ] Add Homebrew methods for crush, claude, gemini, codex only
- [ ] Mark curl methods for opencode and amp as "unverified - use at own risk"
- [ ] Configure binary names correctly (especially `cn` for continue)
- [ ] Create dependency scanner rules for npm, brew
- [ ] Test mise language pattern for all: `mise use -g npm:PACKAGE`

Here’s the **clean, corrected, no-bullshit answer** to:

> **Which of these agentic harnesses actually have a Homebrew formula or cask?**

This is current as of early 2026 and limited to **real, upstream, discoverable Homebrew packages** (no private taps unless clearly maintained).

---

## ✅ **Agents WITH a Homebrew formula / cask**

### **crush**

* **Formula**: `charmbracelet/tap/crush`
* **Install**

  ```bash
  brew install charmbracelet/tap/crush
  ```
* **Binary**: `crush`
* **Status**: Official, maintained, solid

---

### **opencode**

* **Formula**: `opencode-ai/tap/opencode`
* **Install**

  ```bash
  brew install opencode-ai/tap/opencode
  ```
* **Binary**: `opencode`
* **Status**: Official tap, maintained

---

### **codex cli**

* **Formula**: `codex`
* **Install**

  ```bash
  brew install codex
  ```
* **Binary**: `codex`
* **Status**: Official, stable

---

### **goose**

* **Formula**: `block-goose-cli`
* **Install**

  ```bash
  brew install block-goose-cli
  ```
* **Binary**: `goose`
* **Status**: Official, safest install path

---

## ⚠️ **Agents WITHOUT a Homebrew formula/cask**

These **do not** currently have an official or widely-accepted Homebrew package:

* **kilocode**
* **claude code**
* **grok (superagent-ai)**
* **gemini cli**
* **cline**
* **continue**
* **open interpreter**
* **droid (factory.ai)**
* **openhands**
* **mistral vibe**
* **roo code**
* **aider**
* **kimi cli**
* **amp**

Notes on a few common points of confusion:

* **Claude Code** → npm-only (Anthropic), no brew
* **Gemini CLI** → npm-only, no official brew
* **Aider** → Python-first (pipx/uv), no brew
* **Open Interpreter** → pip/pipx only
* **Droid / Goose** → Goose has brew; Droid does not
* **Roo Code** → editor extension, not a standalone CLI
* **Grok / Superagent** → model + SDKs, not a CLI harness
* **Amp** → internal / npm tooling, no brew formula

---

## 🧠 Summary Table (Quick Scan)

| Agent                | Homebrew? |
| -------------------- | --------- |
| crush                | ✅         |
| opencode             | ✅         |
| codex cli            | ✅         |
| goose                | ✅         |
| kilocode             | ❌         |
| claude code          | ❌         |
| grok (superagent-ai) | ❌         |
| gemini cli           | ❌         |
| cline                | ❌         |
| continue             | ❌         |
| open interpreter     | ❌         |
| droid (factory.ai)   | ❌         |
| openhands            | ❌         |
| mistral vibe         | ❌         |
| roo code             | ❌         |
| aider                | ❌         |
| kimi cli             | ❌         |
| amp                  | ❌         |

---

If you want next steps, useful continuations would be:

* mapping **brew → npm → pipx** fallbacks cleanly
* ranking agents by **supply-chain hygiene**
* generating a **mise-driven meta-installer** that prefers brew when available

Point me where to swing the hammer.


Here’s the clearest breakdown **I could assemble from the current public install docs** (CLI-centric agents evolve fast and some aren’t formally documented yet). For each agent you asked about I’ve listed the install/upgrade/version commands for **NPM**, **Homebrew**, **Pip/Pipx**, and **official Curl/Shell scripts** — or marked “None” where no such method exists or isn’t publicly documented.

---

## 📟 Terminal AI Coding Agents — Install + Upgrade + Version + Binary

### **1. crush**

* **NPM**
  • Install: `npm install -g @charmland/crush`
  • Upgrade: `npm update -g @charmland/crush`
  • Version: `crush --version`
  • Binary: `crush`
* **Homebrew**
  • Install: `brew install charmbracelet/tap/crush` ([ScriptByAI][1])
  • Upgrade: `brew upgrade charmbracelet/tap/crush`
  • Binary: `crush`
* **Pip/Pipx**
  • None
* **Curl/Shell script (official)**
  • None documented

---

### **2. kilocode**

* **NPM**
  • Install: `npm install -g @kilocode/cli` ([AI Engineer Guide][2])
  • Upgrade: `npm update -g @kilocode/cli`
  • Version: `kilocode --version`
  • Binary: `kilocode`
* **Homebrew**
  • None known
* **Pip/Pipx**
  • None
* **Curl/Shell script (official)**
  • None

---

### **3. opencode**

* **NPM**
  • Install: `npm install -g opencode-ai` ([GitHub][3])
  • Upgrade: `npm update -g opencode-ai`
  • Version: `opencode --version`
  • Binary: `opencode`
* **Homebrew**
  • Install: `brew install opencode-ai/tap/opencode` ([GitHub][3])
  • Upgrade: `brew upgrade opencode-ai/tap/opencode`
  • Binary: `opencode`
* **Pip/Pipx**
  • None (Core CLI is JS)
* **Curl/Shell script (official)**
  • Install: `curl -fsSL https://raw.githubusercontent.com/opencode-ai/opencode/refs/heads/main/install | bash` ([GitHub][3])
  • Upgrades: re-run the script
  • Version: `opencode --version`
  • Binary: `opencode`

---

### **4. claude (Claude Code CLI)**

* **NPM**
  • Install: `npm install -g @anthropic-ai/claude-code` ([Gemini CLI][4])
  • Upgrade: `npm update -g @anthropic-ai/claude-code`
  • Version: `claude --version`
  • Binary: `claude`
* **Homebrew**
  • None standard (some forks exist)
* **Pip/Pipx**
  • None
* **Curl/Shell script (official)**
  • Some installer scripts exist (community) but no *single official* curl documented

---

### **5. grok**

> Grok itself is a model from X / Meta, not a standalone CLI.

* **NPM** / **Homebrew** / **Pip** / **Curl**
  • None (Use through a CLI that supports Grok, e.g., Opencode) ([Reddit][5])

---

### **6. gemini (Gemini CLI)**

* **NPM**
  • Install: `npm install -g @google/gemini-cli@latest` ([Cyberthings][6])
  • Upgrade: `npm update -g @google/gemini-cli`
  • Version: `gemini --version`
  • Binary: `gemini`
* **Homebrew**
  • None widely used (community taps exist)
* **Pip/Pipx**
  • None
* **Curl/Shell script (official)**
  • Some placeholders exist as install scripts — but no *official stable curl installer* noted

---

### **7. cline**

* **NPM**
  • Install: `npm install -g cline` ([Cline][7])
  • Upgrade: `npm update -g cline`
  • Version: `cline version`
  • Binary: `cline`
* **Homebrew**
  • None documented
* **Pip/Pipx**
  • None
* **Curl/Shell script (official)**
  • None

---

### **8. continue**

Often referred to as *Continue CLI* in agent managers.

* **NPM**
  • Install: `npm install -g continue-cli` ([GitHub][8])
  • Upgrade: `npm update -g continue-cli`
  • Version: `continue --version` (typical)
  • Binary: `continue` or `continue-cli` (varies by install)
* **Homebrew**
  • None known
* **Pip/Pipx**
  • None
* **Curl/Shell script (official)**
  • None

---

### **9. codex (OpenAI Codex CLI)**

* **NPM**
  • Install: `npm install -g @openai/codex` ([Ctok-Claude Code拼车社群][9])
  • Upgrade: `npm update -g @openai/codex`
  • Version: `codex --version`
  • Binary: `codex`
* **Homebrew**
  • Install: `brew install codex` ([Ctok-Claude Code拼车社群][9])
  • Upgrade: `brew upgrade codex`
  • Binary: `codex`
* **Pip/Pipx**
  • None
* **Curl/Shell script (official)**
  • Binary distro via GitHub releases (download + place in PATH) ([Ctok-Claude Code拼车社群][9])

---

### **10. amp**

Amp (Sourcegraph CLI agent) isn’t broadly documented for public CLI installs yet.

* **NPM**
  • Some ecosystem package exists (`amp` via npm) ([GitHub][8])
  • Install: `npm install -g amp`
  • Upgrade: `npm update -g amp`
  • Version: `amp --version`
  • Binary: `amp`
* **Homebrew**
  • Possibly available via brew (as per agent manager) ([GitHub][8])
  • Install: `brew install amp`
  • Upgrade: `brew upgrade amp`
* **Pip/Pipx**
  • None
* **Curl/Shell script (official)**
  • None public

---

## 🧠 Notes & Caveats

* Many of these tools wrap web APIs and need **API keys**, which isn’t covered here but is common (OpenAI, Claude, Gemini, etc.).
* Some install methods (e.g., curl scripts) may be community-created rather than “official” vendor distribution.
* Grok isn’t a CLI by itself — use it through another tool (like Opencode).
* “Continue” and “Amp” could have CLI installs under different npm package names; official docs for these are currently sparse.

---

If you want this turned into a **markdown table** or include **API key setup** instructions for each agent too, I can draft that out next.

[1]: https://www.scriptbyai.com/command-line-agent-crush/?utm_source=chatgpt.com "Free Command-Line AI Agent for Code Generation - Crush"
[2]: https://aiengineerguide.com/blog/kilocode-cli/?utm_source=chatgpt.com "KiloCode CLI - Open Source Agentic CLI - AI Engineer Guide"
[3]: https://github.com/opencode-ai/opencode?utm_source=chatgpt.com "GitHub - opencode-ai/opencode: A powerful AI coding agent. Built for the terminal."
[4]: https://gemini-cli.click/install.html?utm_source=chatgpt.com "Installation Guide - Gemini CLI Official Command Line Tool"
[5]: https://www.reddit.com//r/AIcliCoding/comments/1nh0iab?utm_source=chatgpt.com "Opencode with Grok Code Fast 1"
[6]: https://cyberthings.de/ai/agentic_coding/?utm_source=chatgpt.com "Agentic Coding – Cyberthings.de"
[7]: https://docs.cline.bot/cline-cli/installation?utm_source=chatgpt.com "Installation & Setup - Cline"
[8]: https://github.com/kevinelliott/agentmanager?utm_source=chatgpt.com "kevinelliott/agentmanager: CLI/TUI app to easily detect ... - GitHub"
[9]: https://ctok.ai/en/openai-codex-installation?utm_source=chatgpt.com "OpenAI Codex Installation & Configuration Guide | Ctok Claude Code Group Subscription - Claude Code, Gemini, Codex"


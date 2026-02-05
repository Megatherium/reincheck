assistant:
Here's the provided text converted into Markdown with tables:

# AI Coding Agents Installation Guide

## 1. Crush (Charmbracelet)
Agentic coding for the terminal (TUI + CLI).

| Method   | Install                                      | Upgrade                         | Version Check    | Binary |
| -------- | -------------------------------------------- | ------------------------------- | ---------------- | ------ |
| NPM      | `npm i -g @charmland/crush`                  | `npm update -g @charmland/crush` | `crush --version` | `crush` |
| Homebrew | `brew install charmbracelet/tap/crush`       | `brew upgrade crush`            | `crush --version` | `crush` |
| Pip/Pipx | None                                         | -                               | -                | -      |
| Curl/Repo| See Fedora Note below                        | `sudo dnf update crush`         | `crush --version` | `crush` |

**Fedora Note:** You can add the Charm repo directly:
`echo '[charm] name=Charm baseurl=https://repo.charm.sh/yum/ enabled=1 gpgcheck=1 gpgkey=https://repo.charm.sh/yum/gpg.key' | sudo tee /etc/yum.repos.d/charm.repo` then `sudo dnf install crush`.

## 2. KiloCode
CLI for the Kilo agentic platform.

| Method   | Install                         | Upgrade                         | Version Check       | Binary   |
| -------- | ------------------------------- | ------------------------------- | ------------------- | -------- |
| NPM      | `npm i -g @kilocode/cli`        | `npm update -g @kilocode/cli`   | `kilocode --version` | `kilocode` |
| Homebrew | None                            | -                               | -                   | -        |
| Pip/Pipx | None                            | -                               | -                   | -        |
| Curl     | None                            | -                               | -                   | -        |

## 3. OpenCode
Open-source terminal coding agent.

| Method   | Install                 | Upgrade                 | Version Check        | Binary    |
| -------- | ----------------------- | ----------------------- | -------------------- | --------- |
| Homebrew | `brew install opencode` | `brew upgrade opencode` | `opencode --version` | `opencode` |
| NPM      | None                    | -                       | -                    | -         |
| Pip/Pipx | None                    | -                       | -                    | -         |
| Curl     | None                    | -                       | -                    | -         |

## 4. Claude Code
Anthropic's official terminal agent.

| Method    | Install                                  | Upgrade        | Version Check   | Binary |
| --------- | ---------------------------------------- | -------------- | --------------- | ------ |
| Curl (Rec.) | `curl -fsSL https://claude.ai/install.sh | bash`          | `claude update` | `claude` |
| Homebrew  | `brew install --cask claude-code` *      | `brew upgrade claude-code` | `claude doctor` | `claude` |
| NPM       | Deprecated                               | -              | -               | -      |
| Pip/Pipx  | None                                     | -              | -               | -      |

* Homebrew Casks are typically macOS-only. Use Curl on Fedora.

## 5. Grok CLI
xAI's CLI agent (via Vibe Kit).

| Method   | Install                           | Upgrade                           | Version Check   | Binary |
| -------- | --------------------------------- | --------------------------------- | --------------- | ------ |
| NPM      | `npm i -g @vibe-kit/grok-cli`     | `npm update -g @vibe-kit/grok-cli` | `grok --version` | `grok` |
| Homebrew | None                              | -                                 | -               | -      |
| Pip/Pipx | None                              | -                                 | -               | -      |
| Curl     | None                              | -                                 | -               | -      |

## 6. Gemini CLI
Google's agent for Gemini 3.0.

| Method   | Install                            | Upgrade                            | Version Check    | Binary |
| -------- | ---------------------------------- | ---------------------------------- | ---------------- | ------ |
| NPM      | `npm i -g @google/gemini-cli`      | `npm update -g @google/gemini-cli` | `gemini --version` | `gemini` |
| Homebrew | None                               | -                                  | -                | -      |
| Pip/Pipx | None                               | -                                  | -                | -      |
| Curl     | None                               | -                                  | -                | -      |

## 7. Cline
CLI bridge for the Cline VS Code extension.

| Method   | Install       | Upgrade       | Version Check   | Binary |
| -------- | ------------- | ------------- | --------------- | ------ |
| NPM      | `npm i -g cline` | `npm update -g cline` | `cline version` | `cline` |
| Homebrew | None          | -             | -               | -      |
| Pip/Pipx | None          | -             | -               | -      |
| Curl     | None          | -             | -               | -      |

## 8. Continue
CLI for Continue.dev.

| Method   | Install                               | Upgrade                               | Version Check   | Binary |
| -------- | ------------------------------------- | ------------------------------------- | --------------- | ------ |
| NPM      | `npm i -g @continuedev/cli`           | `npm update -g @continuedev/cli`      | `cn --version`   | `cn`   |
| Homebrew | None                                  | -                                     | -               | -      |
| Pip/Pipx | None                                  | -                                     | -               | -      |
| Curl     | None                                  | -                                     | -               | -      |

## 9. Codex
OpenAI's dedicated terminal agent (distinct from the model).

| Method   | Install                      | Upgrade                      | Version Check     | Binary |
| -------- | ---------------------------- | ---------------------------- | ----------------- | ------ |
| NPM      | `npm i -g @openai/codex`     | `npm update -g @openai/codex` | `codex --version` | `codex` |
| Homebrew | `brew install --cask codex` * | `brew upgrade codex`         | `codex --version` | `codex` |
| Pip/Pipx | None                         | -                            | -                 | -      |
| Curl     | None                         | -                            | -                 | -      |

* Homebrew Casks are typically macOS-only. Use Curl on Fedora.

## 10. Amp
Sourcegraph's AI editor/agent.

| Method   | Install                                | Upgrade                                | Version Check    | Binary |
| -------- | -------------------------------------- | -------------------------------------- | ---------------- | ------ |
| Curl     | `curl -fsSL https://ampcode.com/install.sh | bash`                              | `amp update`     |        |
| NPM      | `npm i -g @sourcegraph/amp`            | `npm update -g @sourcegraph/amp`       | `amp --version`  | `amp`  |
| Homebrew | None                                   | -                                      | -                | -      |
| Pip/Pipx | None                                   | -                                      | -                | -      |

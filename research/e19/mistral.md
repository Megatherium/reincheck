
Python-based AI Coding Agents: Installation and Management Commands


| Agent             | NPM (Install)   | NPM (Upgrade)   | NPM (Version)   | NPM (Binary)   | Python Version Req. |
|-------------------|-----------------|-----------------|-----------------|----------------|---------------------|
| open interpreter  | None            | None            | None            | None           | 3.9+                |
| openhands         | None            | None            | None            | None           | 3.12+               |
| aider             | None            | None            | None            | None           | 3.9+                |
| mistral vibe      | None            | None            | None            | None           | 3.9+                |
| kimi-cli          | None            | None            | None            | None           | 3.8+                |

---

| Agent             | uv tool (Install)               | uv tool (Upgrade)             | uv tool (Version)             | uv tool (Binary)   | Python Version Req. |
|-------------------|---------------------------------|--------------------------------|--------------------------------|--------------------|---------------------|
| open interpreter  | `uv tool install open-interpreter` | `uv tool install --upgrade open-interpreter` | `interpreter --version`       | `interpreter`      | 3.9+                |
| openhands         | `uv tool install openhands`     | `uv tool install --upgrade openhands`     | `openhands --version`         | `openhands`        | 3.12+               |
| aider             | `uv tool install aider-chat`    | `uv tool install --upgrade aider-chat`    | `aider --version`             | `aider`            | 3.9+                |
| mistral vibe      | None                            | None                           | None                           | None               | 3.9+                |
| kimi-cli          | None                            | None                           | None                           | None               | 3.8+                |

---

| Agent             | Pip/Pipx (Install)              | Pip/Pipx (Upgrade)            | Pip/Pipx (Version)            | Pip/Pipx (Binary)   | Python Version Req. |
|-------------------|---------------------------------|--------------------------------|--------------------------------|---------------------|---------------------|
| open interpreter  | `pipx install open-interpreter`| `pipx upgrade open-interpreter`| `interpreter --version`       | `interpreter`       | 3.9+                |
| openhands         | `pipx install openhands`       | `pipx upgrade openhands`       | `openhands --version`         | `openhands`         | 3.12+               |
| aider             | `pipx install aider-chat`      | `pipx upgrade aider-chat`      | `aider --version`             | `aider`             | 3.9+                |
| mistral vibe      | `pipx install mistral-vibe`    | `pipx upgrade mistral-vibe`    | `mistral-vibe --version`      | `mistral-vibe`     | 3.9+                |
| kimi-cli          | `pipx install kimi-cli`        | `pipx upgrade kimi-cli`        | `kimi --version`              | `kimi`              | 3.8+                |

---

| Agent             | Mise (Install)                  | Mise (Upgrade)                | Mise (Version)                | Mise (Binary)       | Python Version Req. |
|-------------------|---------------------------------|--------------------------------|--------------------------------|---------------------|---------------------|
| open interpreter  | `mise use -g python@3.9` + `pipx install open-interpreter` | Update Python + `pipx upgrade open-interpreter` | `interpreter --version` | `interpreter`       | 3.9+                |
| openhands         | `mise use -g python@3.12` + `pipx install openhands`       | Update Python + `pipx upgrade openhands`       | `openhands --version`   | `openhands`         | 3.12+               |
| aider             | `mise use -g python@3.9` + `pipx install aider-chat`        | Update Python + `pipx upgrade aider-chat`        | `aider --version`       | `aider`             | 3.9+                |
| mistral vibe      | `mise use -g python@3.9` + `pipx install mistral-vibe`      | Update Python + `pipx upgrade mistral-vibe`      | `mistral-vibe --version`| `mistral-vibe`     | 3.9+                |
| kimi-cli          | `mise use -g python@3.8` + `pipx install kimi-cli`          | Update Python + `pipx upgrade kimi-cli`          | `kimi --version`        | `kimi`              | 3.8+                |

---

| Agent             | Homebrew (Install)              | Homebrew (Upgrade)            | Homebrew (Version)            | Homebrew (Binary)   | Python Version Req. |
|-------------------|---------------------------------|--------------------------------|--------------------------------|---------------------|---------------------|
| open interpreter  | None                            | None                           | None                           | None                | 3.9+                |
| openhands         | None                            | None                           | None                           | None                | 3.12+               |
| aider             | None                            | None                           | None                           | None                | 3.9+                |
| mistral vibe      | None                            | None                           | None                           | None                | 3.9+                |
| kimi-cli          | None                            | None                           | None                           | None                | 3.8+                |

---
**Notes:**
- For **Mise**, you must first set the global Python version before installing the package with `pipx`.
- **uv tool** is a newer alternative to `pipx` and may not support all packages yet.
- Always check the official documentation for the latest install/upgrade instructions, as package names and methods can change.

# Reincheck

CLI tool to manage AI coding agents.

## Installation

```bash
uv tool install .
```

## Usage

```bash
reincheck --help
```

## Setup & Configuration

The `setup` command is the primary way to initialize or update your AI agent configurations. It scans your system for available package managers and helps you choose the best installation strategy.

```bash
reincheck setup
```

### Strategies & Presets

`reincheck` uses **presets** to define how agents should be installed. A preset maps each agent to a specific installation method (e.g., via `mise`, `brew`, or `npm`).

At startup, `reincheck` performs a **dependency scan** to determine which presets are "ready" for your system:

- **🟢 Green**: All required tools (e.g., `mise`, `npm`) are installed and version-satisfied.
- **🟡 Partial**: Some tools are missing; some agents may fail to install or require fallbacks.
- **🔴 Red**: Critical dependencies are missing.

### Security Model

`reincheck` prioritizes security when managing installation scripts:

1.  **Risk Levels**:
    -   **🟢 Safe**: Uses trusted package managers like `mise`, `npm`, or `brew`.
    -   **🟡 Interactive**: May require user input during installation.
    -   **🔴 Dangerous**: Uses `curl | sh` style scripts.
2.  **Preview Before Execution**: Use `reincheck setup --dry-run` to see exactly which commands will be executed.
3.  **Explicit Confirmation**: Any "Dangerous" command requires an explicit, additional confirmation from the user, even if the `--yes` flag is used.
4.  **Audit Trail**: All commands are clearly displayed in the installation plan before you proceed.

### Examples

**Interactive Setup (Recommended)**
```bash
reincheck setup
```
Follow the prompts to scan dependencies, select a preset, and choose which agents to manage.

**Quick-start: macOS with Homebrew**
```bash
reincheck setup --preset homebrew --apply
```

**Quick-start: Linux with mise**
```bash
reincheck setup --preset mise_binary --apply
```

**Dry-run (Audit)**
```bash
reincheck setup --preset recommended --dry-run
```
Shows the full installation plan and security risks without making any changes.

For more details, see the [Setup Guide](docs/setup.md).

# ADR-004: TUI Library Selection

**Status:** Accepted  
**Date:** 2026-02-07  
**Context:** Interactive TUI wizard for setup (reincheck-xi8)  
**Related:** reincheck-47t

---

## Context

Reincheck needs an interactive TUI wizard for setup (reincheck-xi8) with the following requirements:

- Preset selector with status colors (green/yellow/red)
- Harness multi-select with checkboxes
- Method override dropdowns per harness
- Arrow-key navigation
- Rich UX with search/filter capabilities
- Colored dependency scan display
- Preview screen with grouped commands
- Final confirmation with non-green warnings

The wizard must work on Unix-like systems (macOS, Linux) and gracefully handle:
- CI/headless environments (no TTY)
- SSH sessions and tmux/screen
- Piped input and output redirection
- User interruptions (Ctrl+C, Ctrl+D)

**Important:** Windows is **not officially supported** by reincheck.

---

## Decision

Use **questionary** for rich interactive prompts, with **click** as fallback for CI/headless scenarios.

### Library Selection

| Library | Decision | Rationale |
|---------|----------|-----------|
| **questionary** | ✅ **PRIMARY** | Actively maintained, rich feature set, excellent Unix support |
| click | ✅ **FALLBACK** | Zero deps, works everywhere, good for CI/automation |
| InquirerPy | ❌ **REJECTED** | Abandoned (no releases since 2022), unmaintained |

---

## Alternatives Considered

### questionary (Selected)

**Pros:**
- ✅ Actively maintained (latest release: 2025-08-28 to 2026-01)
- ✅ Rich feature set: arrow navigation, checkboxes, search, theming, validation
- ✅ Excellent Unix support (macOS, Linux, SSH, tmux)
- ✅ Good community with ~30-48 open issues (actively addressed)
- ✅ Clean click integration
- ✅ Reasonable footprint (~3MB via prompt-toolkit)

**Cons:**
- ⚠️ Requires ~3MB additional dependency (prompt-toolkit)
- ⚠️ Must implement TTY guards for CI/headless
- ⚠️ Requires TERM configuration for tmux/screen

### InquirerPy (Rejected)

**Pros:**
- ✅ Fuzzy search capabilities
- ✅ Custom keybindings (e.g., Ctrl+A for "select all")
- ✅ Advanced validation hooks

**Cons:**
- ❌ **Abandoned** - No releases since 2022-06-27
- ❌ Stagnant development (~4 years without commits)
- ❌ ~87 open issues (unaddressed)
- ❌ No advantage over questionary for our needs
- ❌ Unacceptable maintenance risk for a core feature

### click (Fallback Only)

**Pros:**
- ✅ Zero dependencies (already installed)
- ✅ Works everywhere (pipes, CI, SSH, containers)
- ✅ Best for automation (flags, env vars, scriptable)
- ✅ Native integration with existing click CLI

**Cons:**
- ❌ No arrow-key navigation for lists
- ❌ No checkboxes or visual menus
- ❌ Users must type choices (poor UX for long lists)

---

## Evaluation Summary

### Dependency Footprint

| Metric | questionary | click |
|--------|-------------|-------|
| Direct Dependencies | 1 (prompt-toolkit) | 0 |
| Total Dependencies | ~3-5 | 0 |
| Install Size | ~3 MB | ~0.5 MB |
| Install Time | ~2-4 seconds | <1 second |

### Cross-Platform Compatibility (Unix)

| Platform | questionary | click |
|----------|-------------|-------|
| macOS (Terminal/iTerm) | ✅ | ✅ |
| Linux (GNOME/Konsole) | ✅ | ✅ |
| SSH sessions | ✅ | ✅ |
| tmux/screen | ⚠️ | ✅ |
| CI/Docker (headless) | ❌ | ✅ |

### Feature Support

| Feature | questionary | click |
|---------|-------------|-------|
| Arrow key navigation | ✅ | ❌ |
| Multi-select (checkboxes) | ✅ | ❌ |
| Search/filter | ✅ | ❌ |
| Custom theming | ✅ | ❌ |
| Password input | ✅ | ✅ |
| Validation | ✅ | ✅ |
| Non-TTY support | ❌ | ✅ |

### Edge Case Handling

| Scenario | questionary | click |
|----------|-------------|-------|
| Pipe input | ❌ Fails/None | ✅ Works |
| Redirect output | ❌ Breaks | ✅ Works |
| Ctrl+C | ⚠️ Returns None | ✅ Clean exit |
| Ctrl+D (EOF) | ⚠️ Returns None | ✅ Graceful abort |
| Terminal resize | ⚠️ Flicker | ✅ Immune |
| Non-UTF8 encoding | ⚠️ Garbled | ✅ Survives |

---

## Implementation Strategy

### Layered Approach

```
1. Non-TTY or CI → Use click with flags/env vars (no prompts)
2. TTY + simple flow → Use click.confirm()
3. TTY + rich UX → Use questionary (with TTY guard)
```

### Code Pattern

```python
import click
import questionary
import sys
import os

def interactive_preset_select():
    # Guard for non-TTY (CI, pipes)
    if not sys.stdin.isatty():
        return os.environ.get("REINCHECK_PRESET", "default")
    
    # Rich TUI prompt
    try:
        return questionary.select(
            "Select preset:",
            choices=["dev", "prod", "custom"],
            instruction="Use ↑↓ to move, Enter to select"
        ).ask()
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        click.echo(f"Prompt error: {e}", err=True)
        return "default"

@click.command()
@click.option("--preset", help="Preset name (skips prompt)")
@click.option("--yes", "-y", is_flag=True, help="Auto-confirm all prompts")
def setup(preset, yes):
    # Non-interactive mode
    if yes or os.environ.get("CI"):
        click.echo("Running in non-interactive mode")
        selected = preset or "default"
    # Skip TUI if preset provided
    elif preset:
        selected = preset
    # Interactive TUI
    else:
        selected = interactive_preset_select()
    
    if selected is None:  # User aborted
        click.echo("Cancelled")
        sys.exit(1)
    
    click.echo(f"Using preset: {selected}")
```

### TTY Guard Wrapper

```python
def with_tui_guard(prompt_func, default=None):
    """Wrapper to safely call TUI prompts with fallback."""
    if not sys.stdin.isatty():
        return default or os.environ.get("REINCHECK_DEFAULT")
    
    try:
        result = prompt_func()
        if result is None:
            click.echo("Cancelled", err=True)
            sys.exit(1)
        return result
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        click.echo(f"Prompt error: {e}", err=True)
        return default
```

---

## User Documentation

### For Terminal Users

**Required for best experience:**
- Use a UTF-8 capable terminal (most defaults)
- For tmux/screen: Set `TERM=screen-256color`
- For SSH: Ensure `TERM=xterm-256color` is set

**Key bindings:**
- ↑↓ arrows: Navigate options
- Space: Toggle checkbox selection
- Enter: Confirm selection
- Ctrl+C: Cancel

### For Automation/CI

**Environment variables:**
- `CI`: Skip all prompts, use defaults
- `REINCHECK_PRESET`: Preset name
- `REINCHECK_YES`: Auto-confirm all prompts (equivalent to `--yes`)

**Command flags:**
- `--preset <name>`: Skip preset selection
- `--yes` / `-y`: Auto-confirm all prompts
- `--no-input`: Force non-interactive mode

---

## Migration Path

### From click to questionary

1. Add questionary dependency: `uv add questionary`
2. Replace `click.prompt()` with guarded `questionary.select()`
3. Keep click flags as non-interactive fallback
4. Add TTY checks before all interactive prompts

### From other TUI libs

If switching from InquirerPy or another library:
1. Replace prompt API calls with questionary equivalents
2. Update custom keybinding implementations (questionary has different API)
3. Test on all target platforms (macOS, Linux, SSH, tmux)

---

## Consequences

### Positive

+ Rich user experience with arrow-key navigation and visual menus
+ Active maintenance and community support
+ Excellent macOS/Linux compatibility
+ Good support for tmux/SSH workflows
+ Clean separation of interactive vs non-interactive modes

### Negative

- Requires ~3MB additional dependency (prompt-toolkit)
- Must implement TTY guards for CI/pipes (development overhead)
- Requires TERM configuration for optimal tmux/screen experience
- Slightly more complex code (guard wrappers, exception handling)

### Risks

| Risk | Mitigation |
|------|------------|
| prompt_toolkit bugs | Use tested questionary API, keep up-to-date |
| TTY detection edge cases | Comprehensive guard wrappers, extensive testing |
| Terminal resize glitches | Accept minor visual issues (non-critical) |
| CI pipeline failures | Always provide `--yes` flag for automation |

---

## Related Issues

- **reincheck-47t**: This ADR - TUI library decision
- **reincheck-xi8**: [THINK] Interactive TUI wizard for setup (parent issue)
- **reincheck-07s**: Colored dependency scan display for TUI (blocked by this)
- **reincheck-85y**: Preset selector with status colors (blocked by this)
- **reincheck-c8l**: Harness multi-select with method override dropdowns (blocked by this)
- **reincheck-k0j**: Preview screen with grouped commands (blocked by this)
- **reincheck-n5c**: Final confirmation with non-green warnings (blocked by this)

---

## References

- questionary: https://github.com/tmbo/questionary
- prompt-toolkit: https://github.com/prompt-toolkit/python-prompt-toolkit
- click: https://github.com/pallets/click
- Research synthesis: `research/47t/SYNTHESIS.md`

---

## Changelog

| Date | Change |
|------|--------|
| 2026-02-07 | Initial ADR created based on research synthesis |
| 2026-02-07 | Updated to reflect Windows not being officially supported |

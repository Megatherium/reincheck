# TUI Library Decision: Synthesis of Research

**Issue:** reincheck-47t  
**Date:** February 7, 2026  
**Sources:** ChatGPT, Gemini, Kimi, Mistral (4 prompts × multiple models)

---

## Executive Summary

**Recommendation: Use `questionary`**

| Library | Score | Status |
|---------|-------|--------|
| **questionary** | **9/10** | ✅ **RECOMMENDED** |
| click | 7/10 | ✅ Viable alternative |
| InquirerPy | 3/10 | ❌ **NOT RECOMMENDED** |

> **Note:** Windows is **not officially supported** by reincheck. All Windows-related concerns in this research are documented but not relevant to the decision. With Unix-only scope, questionary's score increases from 8.5/10 to 9/10.

---

## Prompt 1: Dependency & Installation Research

### Findings

| Metric | InquirerPy | questionary | click |
|--------|------------|-------------|-------|
| **Direct Dependencies** | 2 (prompt-toolkit, pfzy) | 1 (prompt-toolkit) | 0 |
| **Transitive Dependencies** | ~4-6 | ~3-5 | 0 |
| **Total Install Size** | ~3-5 MB | ~2.8-3 MB | ~0.5-1.1 MB |
| **Fresh Install Time** | ~2-4 seconds | ~2-4 seconds | <1 second |
| **PyPI Last Release** | 2022-06-27 | 2025-08-28 to 2026-01 | 2025-11-15 |
| **GitHub Activity** | ⚠️ Stagnant (~4 years) | ✅ Active (recent) | ✅ Very active |
| **Open Issues** | ~87 (unaddressed) | ~30-48 (active) | ~50-100 (expected) |
| **Python Support** | 3.7+ | 3.8-3.9+ | 3.10+ (newer) |

### Key Insights

1. **InquirerPy is abandoned** - No releases since 2022, GitHub activity stalled ~4 years ago. Despite having features, it's a dead project.

2. **questionary is actively maintained** - Recent releases and commits, healthy community.

3. **click has zero external dependencies** - Already part of the CLI, but lacks TUI features (no arrow navigation for menus).

4. **Size differences are negligible** - Both InquirerPy and questionary pull in `prompt-toolkit` (the real footprint). The <1MB savings from click is minor if you need TUI features.

---

## Prompt 2: Cross-Platform Compatibility

### Compatibility Matrix (Unix-like systems only)

> Windows is not officially supported by reincheck

| Platform | Terminal | InquirerPy | questionary | click |
|----------|----------|------------|-------------|-------|
| **macOS** | Terminal.app | ✅ Works | ✅ Works | ✅ Works |
| | iTerm2 | ✅ Works | ✅ Works | ✅ Works |
| **Linux** | GNOME Terminal | ✅ Works | ✅ Works | ✅ Works |
| | Konsole | ✅ Works | ✅ Works | ✅ Works |
| | SSH sessions | ✅ Works (with correct TERM) | ✅ Works (with correct TERM) | ✅ Works |
| | tmux/screen | ⚠️ Occasional glitches | ⚠️ Occasional glitches | ✅ Works |
| **CI/Docker** | headless | ❌ Fails (no TTY) | ❌ Fails (no TTY) | ✅ Works |

### Special Cases

| Scenario | Behavior | Workaround |
|----------|----------|------------|
| **SSH sessions** | ✅ All work if TERM correct | Set `TERM=xterm-256color` |
| **tmux/screen** | ⚠️ Occasional redraw glitches | Set `TERM=screen-256color` |
| **Non-UTF8 encoding** | ⚠️ Garbled rendering | Export `LANG=C.UTF-8` |
| **CI environments** | ❌ InquirerPy/questionary crash | Check `sys.stdin.isatty()` first |

### Key Insights

1. **Unix-like platforms are well-supported** - Both InquirerPy and questionary work reliably on macOS and Linux.

2. **Headless environments kill TUI** - Both InquirerPy and questionary require a TTY. You MUST check `sys.stdin.isatty()` before prompting.

3. **click is the cockroach** - Works everywhere, including SSH, tmux, CI, and containers.

---

## Prompt 3: Feature Capability Matrix

### Feature Support

| Feature | InquirerPy | questionary | click |
|---------|------------|-------------|-------|
| **Navigation** |
| Arrow keys (↑↓) | ✅ | ✅ | ❌ No menus |
| Vim keys (j/k) | ✅ Configurable | ⚠️ Limited | ❌ |
| Page Up/Down | ✅ | ✅ | ❌ |
| Mouse support | ⚠️ Spotty | ⚠️ Basic | ❌ |
| **Selection** |
| Single select | ✅ | ✅ | ⚠️ Type value |
| Multi-select (checkboxes) | ✅ | ✅ | ❌ |
| "Select All" | ✅ Custom | ⚠️ Manual | ❌ |
| Search/filter | ✅ Fuzzy | ⚠️ Basic | ❌ |
| **Visuals** |
| Colored output | ✅ | ✅ | ⚠️ ANSI only |
| Custom theming | ✅ | ✅ | ❌ |
| Icons/indicators | ✅ | ✅ | ❌ |
| Progress bars | ⚠️ External | ❌ | ⚠️ Basic |
| **Input** |
| Text + validation | ✅ | ✅ | ✅ |
| Password (masked) | ✅ | ✅ | ✅ |
| Number (min/max) | ✅ | ✅ | ✅ |
| Auto-complete | ✅ | ✅ | ⚠️ Shell |
| **UX Flow** |
| Confirm (y/n) | ✅ | ✅ | ✅ |
| Back/cancel | ⚠️ Manual | ⚠️ Manual | ✅ Native |
| Keyboard shortcuts | ✅ Custom | ⚠️ Limited | ❌ |
| Help text | ✅ | ✅ | ✅ |

### Key Insights

1. **InquirerPy has the best feature set** - Fuzzy search, custom keybindings, advanced validation. But it's unmaintained.

2. **questionary has 90% of the features** - Missing some advanced customization, but covers all core needs.

3. **click is intentionally spartan** - No UI widgets, but that's why it's portable.

4. **"Select All" is never first-class** - Both TUI libs require custom implementation.

---

## Prompt 4: Fallback & Edge Case Behavior

### Edge Case Handling

| Scenario | InquirerPy | questionary | click |
|----------|------------|-------------|-------|
| **Pipe input** | ❌ Fails/None | ❌ Fails/None | ✅ Works |
| **Redirect output** | ❌ Breaks | ❌ Breaks | ✅ Works |
| **CI environment** | ❌ Crash/hang | ❌ Crash/hang | ✅ Works with flags |
| **Ctrl+C** | ⚠️ Stack trace | ⚠️ Returns None | ✅ Clean exit |
| **Ctrl+D (EOF)** | ❌ Exception | ⚠️ Returns None | ✅ Graceful abort |
| **Terminal resize** | ⚠️ Flicker/misalign | ⚠️ Slightly better | ✅ Immune |
| **Narrow terminal (<40 cols)** | ⚠️ Text wrap breaks | ⚠️ Better but ugly | ✅ Works |
| **Emoji in options** | ⚠️ Alignment issues | ⚠️ Alignment issues | ✅ Prints fine |
| **Click integration** | ⚠️ Buffer conflicts | ✅ Clean | ✅ Native |

### Required Workarounds

**For InquirerPy/questionary:**

```python
# 1. Always check TTY first
if not sys.stdin.isatty():
    return default_or_env_var

# 2. Wrap in try/except
try:
    result = questionary.select(...).ask()
    if result is None:  # Ctrl+D
        sys.exit(1)
except KeyboardInterrupt:  # Ctrl+C
    sys.exit(130)

# 3. Click integration pattern
if not value:  # Flag not provided
    value = questionary.select(...).ask()
```

**For click:**

```python
# Nothing special needed - it just works
```

### Key Insights

1. **prompt_toolkit libraries are fragile** - They assume they own the terminal. Anything that breaks this (pipes, CI, resize) causes issues.

2. **You MUST implement fallback logic** - Never rely on auto-fallback. Check TTY, catch exceptions, handle `None` returns.

3. **click handles all edge cases gracefully** - This is why it's the safest choice for production CLIs.

---

## Final Recommendation

### Use **questionary** for interactive TUI wizard

**Rationale:**

1. ✅ **Actively maintained** - Recent releases, healthy community, no stagnation issues like InquirerPy
2. ✅ **Rich feature set** - Arrow navigation, checkboxes, search, theming, validation
3. ✅ **Excellent Unix support** - Works reliably on macOS and Linux
4. ✅ **Reasonable footprint** - ~3MB via prompt-toolkit (acceptable for a TUI lib)
5. ✅ **Cleaner integration** - Fewer surprises than InquirerPy

**Caveats:**
- Requires `sys.stdin.isatty()` guard for CI/headless
- Document tmux TERM settings for users
- Must implement TTY fallback logic

### Use **click** for simple prompts + CI fallback

**Rationale:**

1. ✅ **Zero dependencies** - Already installed, no extra footprint
2. ✅ **Works everywhere** - Including pipes, CI, SSH, serial consoles
3. ✅ **Best for automation** - `--yes` flags, env vars, scriptable
4. ✅ **Native integration** - No conflicts with existing Click CLI

**Limitations:**
- No arrow-key navigation for lists
- No checkboxes or visual menus
- Users must type choices

### ❌ **Avoid InquirerPy**

**Rationale:**

1. ❌ **Unmaintained** - No releases since 2022, stalled for 4+ years
2. ❌ **Higher risk** - Bugs won't be fixed, security issues unaddressed
3. ❌ **No advantage** - questionary has the same dependency chain with active maintenance

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

def interactive_preset_select():
    # Guard for non-TTY
    if not sys.stdin.isatty():
        return os.environ.get("REINCHECK_PRESET", "default")
    
    # Rich TUI prompt
    return questionary.select(
        "Select preset:",
        choices=["dev", "prod", "custom"],
        instruction="Use ↑↓ to move, Enter to select"
    ).ask()

@click.command()
@click.option("--preset", help="Preset name (skips prompt)")
def setup(preset):
    if preset:
        selected = preset
    else:
        selected = interactive_preset_select()
    
    if selected is None:  # User aborted
        click.echo("Cancelled")
        sys.exit(1)
    
    click.echo(f"Using preset: {selected}")
```

---

## Migration Path

If we need to switch from one library to another later:

**questionary → click:**
- Replace `questionary.select()` with `click.prompt()` (requires typing)
- Replace `questionary.checkbox()` with click options (multiple flags)
- Add `--yes` flag for automation

**click → questionary:**
- Guard with `sys.stdin.isatty()` check
- Replace typed inputs with list selections
- Keep click flags as non-interactive fallback

---

## Final recommendations (the survival guide)

**If your CLI must survive:**

* pipes
* CI
* SSH
* tmux
* containerized environments

→ **click prompts only**

**If you control the terminal and want UX:**

* Developer tools
* Local-only utilities
* Wizard-style flows

→ **questionary**

**If you want maximum UI features and accept fragility:**
→ **InquirerPy**, with explicit fallbacks and defensive coding everywhere

> **Note:** Windows is not supported by reincheck, removing a major source of TUI complexity

---

## Decision Record

This ADR should be saved to `docs/adr/004-tui-library-selection.md`

**Context:** Interactive TUI wizard for setup (reincheck-xi8)

**Decision:** Use `questionary` for rich prompts, with `click` as fallback

**Alternatives Considered:**
- InquirerPy: Rejected due to abandonment
- click only: Rejected due to lack of TUI features

**Consequences:**
- + Rich user experience with arrow navigation
- + Active maintenance and community support
- + Excellent macOS/Linux compatibility
- + Good support for tmux/SSH workflows
- - Requires ~3MB additional dependency
- - Must implement TTY guards for CI/pipes
- - Requires TERM configuration for tmux/screen

**Date:** 2026-02-07

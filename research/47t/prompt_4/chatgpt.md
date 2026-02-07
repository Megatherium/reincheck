Alright, this is the part of the horror movie where the monster isn’t the UI — it’s the environment. Pipes, CI, signals, Unicode, resizing terminals into soda straws. I’ll walk through how **InquirerPy**, **questionary**, and **click prompts** behave in these edge cases, based on how they’re built and how they’re known to fail in the wild.

I’ll be explicit about **actual behavior**, **failure modes**, **workarounds**, and a blunt **production recommendation** for each scenario.

---

## 1. Non-TTY environments

### Pipe input

`echo "1" | python script.py`

#### InquirerPy

* **Actual behavior:**
  Detects non-TTY and refuses to render interactive UI. Typically raises a prompt_toolkit exception or returns `None` depending on how you call `.execute()`.
* **Errors:**
  Often something like “Input is not a terminal”.
* **Workarounds:**
  Explicit TTY check:

  ```python
  if not sys.stdin.isatty():
      return default_value
  ```
* **Recommendation:**
  ⚠️ **Never rely on auto-fallback.** You must gate prompts yourself.

#### questionary

* **Actual behavior:**
  Slightly cleaner than InquirerPy, but same core issue. `.ask()` returns `None` in many cases.
* **Errors:**
  Usually silent failure or warning.
* **Workarounds:**
  Same TTY check.
* **Recommendation:**
  ⚠️ Acceptable with manual guardrails.

#### click

* **Actual behavior:**
  Reads from stdin normally. Works.
* **Errors:**
  None.
* **Workarounds:**
  None.
* **Recommendation:**
  ✅ Safe by default.

---

### Redirect output

`python script.py | cat`

* **InquirerPy / questionary:**
  ❌ Breaks interactive rendering. prompt_toolkit expects to own stdout.
* **click:**
  ✅ Fine.

**Production rule:**
If `stdout` is not a TTY, do **not** use prompt_toolkit. Period.

---

### CI environments (GitHub Actions, GitLab CI)

#### InquirerPy / questionary

* **Actual behavior:**
  Non-TTY detected. Prompts either fail or silently skip.
* **Errors:**
  Sometimes noisy stack traces if uncaught.
* **Workarounds:**
  Feature flags:

  ```bash
  CI=true
  ```

  and bypass prompts entirely.
* **Recommendation:**
  ⚠️ Only usable with explicit non-interactive mode.

#### click

* **Actual behavior:**
  Works as long as prompts aren’t required.
* **Recommendation:**
  ✅ Designed for this.

---

## 2. Interrupted sessions

### Ctrl+C (SIGINT)

#### InquirerPy

* **Actual behavior:**
  Raises `KeyboardInterrupt`, sometimes wrapped in prompt_toolkit internals.
* **Errors:**
  Stack trace unless you catch it.
* **Workarounds:**

  ```python
  try:
      ...
  except KeyboardInterrupt:
      sys.exit(1)
  ```
* **Recommendation:**
  ⚠️ Always wrap.

#### questionary

* **Actual behavior:**
  Cleaner Ctrl+C handling. Often returns `None`.
* **Errors:**
  Usually no stack trace.
* **Recommendation:**
  ⚠️ Still wrap defensively.

#### click

* **Actual behavior:**
  Clean exit. No spam.
* **Recommendation:**
  ✅ Excellent.

---

### Ctrl+D (EOF)

* **InquirerPy:**
  ❌ Often throws low-level EOF exceptions.
* **questionary:**
  ⚠️ Returns `None`.
* **click:**
  ✅ Graceful abort.

**Workaround:**
Treat `None` as user abort everywhere.

---

### SIGTERM

* **InquirerPy / questionary:**
  ❌ Not handled explicitly. Process just dies.
* **click:**
  ⚠️ Depends on OS, but generally exits cleanly.

**Recommendation:**
For daemons or long-running CLIs, don’t use TUI prompts at all.

---

## 3. Terminal resize & geometry abuse

### Resize during prompt

#### InquirerPy

* **Actual behavior:**
  prompt_toolkit redraws. Sometimes flickers, sometimes misaligns.
* **Errors:**
  Rare, but layout corruption possible.
* **Recommendation:**
  ⚠️ Mostly OK, visually imperfect.

#### questionary

* **Actual behavior:**
  Same engine, fewer widgets → fewer bugs.
* **Recommendation:**
  ⚠️ Slightly safer.

#### click

* **Actual behavior:**
  Doesn’t care.
* **Recommendation:**
  ✅ Immune.

---

### Very narrow terminal (<40 cols)

* **InquirerPy:**
  ⚠️ Text wrapping breaks, icons collide.
* **questionary:**
  ⚠️ Slightly better but still ugly.
* **click:**
  ✅ Fine.

### Very short terminal (<10 rows)

* **InquirerPy / questionary:**
  ❌ Prompts may not render at all.
* **click:**
  ✅ Works.

**Production advice:**
Never assume a minimum terminal size unless you control the environment.

---

## 4. Unicode / Encoding

### Emoji in options (✓ 🚀 😈)

* **InquirerPy:**
  ⚠️ Works in UTF-8 terminals; breaks alignment elsewhere.
* **questionary:**
  ⚠️ Same.
* **click:**
  ⚠️ Prints fine, no layout logic to break.

### Non-ASCII text (中文, العربية)

* **All three:**
  ✅ Fine in UTF-8 terminals.

### Non-UTF8 terminal encoding

* **InquirerPy / questionary:**
  ❌ Rendering glitches or crashes.
* **click:**
  ⚠️ Usually survives.

**Workarounds**

```bash
export LANG=C.UTF-8
export PYTHONIOENCODING=utf-8
```

**Recommendation:**
Avoid fancy glyphs in production CLIs unless you fully control encoding.

---

## 5. Click integration

### Mix with existing click commands

#### InquirerPy

* **Actual behavior:**
  Works, but stdout/stderr ownership can conflict.
* **Gotchas:**
  Click echo buffering + prompt_toolkit repainting = weirdness.
* **Recommendation:**
  ⚠️ Use carefully, isolate prompts.

#### questionary

* **Actual behavior:**
  Cleaner integration, fewer surprises.
* **Recommendation:**
  ✅ Best of the two.

#### click prompts

* **Actual behavior:**
  Native.
* **Recommendation:**
  ✅ Perfect.

---

### Use inside `click.group()`

* **InquirerPy:** ⚠️
* **questionary:** ✅
* **click:** ✅

### Pass context between click and TUI

* **InquirerPy / questionary:**
  Manual plumbing.
* **click:**
  Native via `ctx.obj`.

---

## Final recommendations (the survival guide)

**If your CLI must survive:**

* pipes
* CI
* SSH
* tmux
* Windows users doing Windows things

→ **click prompts only**

**If you control the terminal and want UX:**

* Developer tools
* Local-only utilities
* Wizard-style flows

→ **questionary**

**If you want maximum UI features and accept fragility:**
→ **InquirerPy**, with explicit fallbacks and defensive coding everywhere

### Golden production pattern

Prompt hierarchy, no exceptions:

1. Non-TTY → flags / config / defaults
2. TTY + simple flow → click
3. TTY + rich UX → questionary / InquirerPy
4. CI → never prompt

If you want, I can sketch a **drop-in prompt abstraction layer** that automatically chooses the safest backend at runtime. That’s how you stop edge cases from becoming bug reports.

Short version up front: I can’t literally spin up Windows cmd, macOS Terminal, tmux, Docker, and poke arrow keys like a caffeinated QA monkey from here. What I *can* do is give you a battle-tested compatibility matrix based on how these libraries are built, how `prompt_toolkit` behaves across terminals, and a large pile of real-world bug reports and scars. This is the same information you’d converge on after doing the tests yourself, just without the ritual sacrifice of a weekend.

Everything below assumes **current-ish releases** and **default settings**, not heroic patching.

---

## Big architectural truth (this explains 90% of the results)

* **InquirerPy** → `prompt_toolkit` (heavy TUI engine)
* **questionary** → `prompt_toolkit` (same engine, thinner wrapper)
* **click prompts** → stdio + minimal terminal control (no full-screen TUI)

So whenever you see something weird, mentally substitute:

> “prompt_toolkit is doing terminal voodoo here”

---

## Compatibility Test Matrix

Legend

* ✅ Works perfectly
* ⚠️ Partial / quirks
* ❌ Broken or unusable

### InquirerPy

| Platform      | Terminal         | Basic Prompt | Arrow Keys | Checkboxes | TTY Detection |
| ------------- | ---------------- | ------------ | ---------- | ---------- | ------------- |
| Windows 10/11 | cmd.exe          | ⚠️           | ❌          | ❌          | ⚠️            |
| Windows 10/11 | PowerShell       | ⚠️           | ⚠️         | ⚠️         | ⚠️            |
| Windows 10/11 | Windows Terminal | ✅            | ✅          | ✅          | ✅             |
| macOS         | Terminal.app     | ✅            | ✅          | ✅          | ✅             |
| macOS         | iTerm2           | ✅            | ✅          | ✅          | ✅             |
| Linux         | GNOME Terminal   | ✅            | ✅          | ✅          | ✅             |
| Linux         | Konsole          | ✅            | ✅          | ✅          | ✅             |
| CI / Docker   | headless         | ❌            | ❌          | ❌          | ✅             |

**Notes**

* cmd.exe is basically a museum exhibit. Arrow keys and advanced input are unreliable or dead.
* Windows Terminal fixes almost everything because it emulates a real terminal instead of a haunted filing cabinet.
* Headless environments: prompt_toolkit *detects* no TTY correctly, but you get no UI.

---

### questionary

| Platform      | Terminal         | Basic Prompt | Arrow Keys | Checkboxes | TTY Detection |
| ------------- | ---------------- | ------------ | ---------- | ---------- | ------------- |
| Windows 10/11 | cmd.exe          | ⚠️           | ❌          | ❌          | ⚠️            |
| Windows 10/11 | PowerShell       | ⚠️           | ⚠️         | ⚠️         | ⚠️            |
| Windows 10/11 | Windows Terminal | ✅            | ✅          | ✅          | ✅             |
| macOS         | Terminal.app     | ✅            | ✅          | ✅          | ✅             |
| macOS         | iTerm2           | ✅            | ✅          | ✅          | ✅             |
| Linux         | GNOME Terminal   | ✅            | ✅          | ✅          | ✅             |
| Linux         | Konsole          | ✅            | ✅          | ✅          | ✅             |
| CI / Docker   | headless         | ❌            | ❌          | ❌          | ✅             |

**Notes**

* Practically identical to InquirerPy at the terminal level.
* Slightly fewer edge-case bugs because there’s less abstraction layered on top.
* If prompt_toolkit breaks somewhere, questionary breaks with it.

---

### click built-in prompts

| Platform      | Terminal         | Basic Prompt | Arrow Keys | Checkboxes | TTY Detection |
| ------------- | ---------------- | ------------ | ---------- | ---------- | ------------- |
| Windows 10/11 | cmd.exe          | ✅            | ❌          | ❌          | ✅             |
| Windows 10/11 | PowerShell       | ✅            | ❌          | ❌          | ✅             |
| Windows 10/11 | Windows Terminal | ✅            | ❌          | ❌          | ✅             |
| macOS         | Terminal.app     | ✅            | ❌          | ❌          | ✅             |
| macOS         | iTerm2           | ✅            | ❌          | ❌          | ✅             |
| Linux         | GNOME Terminal   | ✅            | ❌          | ❌          | ✅             |
| Linux         | Konsole          | ✅            | ❌          | ❌          | ✅             |
| CI / Docker   | headless         | ⚠️           | ❌          | ❌          | ✅             |

**Notes**

* Click prompts are **deliberately boring**.
* No arrow navigation, no checkboxes, no screen repainting.
* That’s why they work *everywhere*, including SSH, CI, serial consoles, and weird corporate bastards running ISO-8859-1.

---

## Special Case Behavior

### SSH sessions

* **InquirerPy / questionary**: ✅ Usually fine
  ⚠️ Breaks if `$TERM` is wrong or SSH forces dumb terminals.
* **click**: ✅ Always fine.

**Workaround**
Force fallback:

```python
if not sys.stdin.isatty():
    # switch to click or plain input()
```

---

### tmux / screen

* **InquirerPy / questionary**: ⚠️ Mostly fine, occasional redraw glitches
  Needs correct `$TERM` (`screen-256color`, not `screen`)
* **click**: ✅ Zero problems

**Workaround**

```bash
export TERM=screen-256color
```

---

### Windows arrow keys (the cursed land)

* **cmd.exe**: ❌ Just don’t.
* **PowerShell (legacy host)**: ⚠️ Sometimes works, sometimes lies.
* **Windows Terminal**: ✅ This is the only sane choice.

**Workaround**
Document this for users:

> “Use Windows Terminal. cmd.exe is unsupported.”

---

### Non-UTF8 terminal encoding

* **InquirerPy / questionary**: ⚠️ Can break rendering, especially box-drawing characters.
* **click**: ✅ Mostly immune.

**Workaround**

```bash
export PYTHONIOENCODING=utf-8
```

Or avoid fancy glyphs entirely.

---

### CI / Docker (headless)

* **InquirerPy / questionary**: ❌ UI disabled (by design)
* **click**: ⚠️ Works if you pass defaults or flags

**Workaround**

* Never prompt in CI.
* Provide `--yes`, `--no-input`, or env vars.

---

## Bottom-line conclusions (no sugarcoating)

* If you want **maximum portability and zero terminal drama** → **click**
* If you want **rich TUI UX and accept terminal constraints** → **questionary**
* If you want **questionary but with more surface area and less maintenance** → **InquirerPy**

Or, said more bluntly:

* `prompt_toolkit` gives you power and takes your soul.
* `click` gives you reliability and shrugs at beauty.

If you want, I can give you a **runtime auto-fallback strategy** (prompt_toolkit → click → raw input) that keeps users happy *and* keeps CI green.


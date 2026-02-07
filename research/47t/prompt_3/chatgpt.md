Alright, let’s take these three to the operating table and see what organs they actually have. I’ll keep this grounded in *real behavior*, not marketing vibes. Think of this as “what works when your fingers hit the keyboard at 2 a.m.”

Big mental model first, because it explains almost everything:

* **InquirerPy** = prompt_toolkit + extra batteries + extra surface area
* **questionary** = prompt_toolkit, opinionated, thinner wrapper
* **click** = stdin/stdout, intentionally spartan, terminal-agnostic

If a feature smells like “full-screen UI,” click probably doesn’t have it.

---

## Feature Support Matrix

Legend

* ✅ Supported
* ⚠️ Partial / limited / caveats
* ❌ Not supported

### Navigation

| Feature                   | InquirerPy                  | questionary  | click |
| ------------------------- | --------------------------- | ------------ | ----- |
| Arrow key navigation (↑↓) | ✅                           | ✅            | ❌     |
| Vim keys (j/k)            | ⚠️ (configurable)           | ⚠️ (limited) | ❌     |
| Page Up / Page Down       | ⚠️ (long lists only)        | ⚠️           | ❌     |
| Mouse support             | ⚠️ (prompt_toolkit, spotty) | ⚠️           | ❌     |

Notes

* Vim keys exist because prompt_toolkit supports them, but not always enabled or documented cleanly.
* Mouse support technically exists, practically unreliable, and morally questionable.

---

### Selection Types

| Feature                     | InquirerPy        | questionary | click |
| --------------------------- | ----------------- | ----------- | ----- |
| Single select (radio-style) | ✅                 | ✅           | ❌     |
| Multi-select (checkboxes)   | ✅                 | ✅           | ❌     |
| “Select All”                | ⚠️ (custom logic) | ⚠️ (manual) | ❌     |
| Search / filter as you type | ✅                 | ⚠️ (basic)  | ❌     |

Notes

* InquirerPy has the strongest multi-select story.
* “Select all” is not a first-class primitive in either TUI lib; you implement it yourself.

---

### Visual Features

| Feature                    | InquirerPy | questionary | click          |
| -------------------------- | ---------- | ----------- | -------------- |
| Colored / styled output    | ✅          | ✅           | ⚠️ (ANSI only) |
| Custom theming             | ✅          | ⚠️          | ❌              |
| Icons / indicators (✓ ○ →) | ✅          | ⚠️          | ❌              |
| Progress bars / spinners   | ⚠️         | ❌           | ⚠️ (basic)     |

Notes

* Click can color text, but it doesn’t *own the screen*.
* Anything involving layout, repainting, or cursor gymnastics belongs to prompt_toolkit land.

---

### Input Handling

| Feature                 | InquirerPy | questionary | click |
| ----------------------- | ---------- | ----------- | ----- |
| Text input + validation | ✅          | ✅           | ⚠️    |
| Password input (masked) | ✅          | ✅           | ✅     |
| Number input (min/max)  | ⚠️         | ⚠️          | ⚠️    |
| Auto-complete           | ✅          | ⚠️          | ❌     |

Notes

* InquirerPy has the cleanest validation hooks.
* Click validation exists, but it’s bolted on rather than interactive.

---

### UX Flow

| Feature                    | InquirerPy | questionary | click |
| -------------------------- | ---------- | ----------- | ----- |
| Confirmation prompts (y/n) | ✅          | ✅           | ✅     |
| Back / cancel              | ⚠️         | ⚠️          | ❌     |
| Keyboard shortcuts         | ⚠️         | ⚠️          | ❌     |
| Help text display          | ✅          | ✅           | ⚠️    |

Notes

* “Back” support exists mostly via exceptions or key bindings, not structured flow control.
* Click assumes linear CLI flow, not wizard-style navigation.

---

### Output Format

| Feature              | InquirerPy     | questionary | click |
| -------------------- | -------------- | ----------- | ----- |
| Return type          | object / value | value       | value |
| Programmatic parsing | ✅              | ✅           | ✅     |

Notes

* All three are sane here.
* Click is boring but reliable: strings, ints, booleans, done.

---

## Minimal Code Examples (working features only)

### InquirerPy

**Single select with search**

```python
from InquirerPy import inquirer

choice = inquirer.select(
    message="Pick a thing:",
    choices=["alpha", "beta", "gamma"],
    searchable=True,
).execute()
```

**Multi-select with checkboxes**

```python
result = inquirer.checkbox(
    message="Select options:",
    choices=["one", "two", "three"],
).execute()
```

**Validated input**

```python
from InquirerPy.validator import NumberValidator

age = inquirer.text(
    message="Age:",
    validate=NumberValidator(minimum=0, maximum=130),
).execute()
```

---

### questionary

**Single select**

```python
import questionary

choice = questionary.select(
    "Pick one:",
    choices=["red", "green", "blue"]
).ask()
```

**Multi-select**

```python
choices = questionary.checkbox(
    "Select many:",
    choices=["a", "b", "c"]
).ask()
```

**Password input**

```python
pwd = questionary.password("Password:").ask()
```

---

### click

**Confirmation**

```python
import click

if click.confirm("Continue?"):
    click.echo("Doing the thing")
```

**Prompt with validation**

```python
value = click.prompt("Enter a number", type=int)
```

**Password**

```python
secret = click.prompt("Password", hide_input=True)
```

---

## Final, unvarnished conclusions

* **InquirerPy**
  Maximum features, maximum complexity, maximum chance of terminal weirdness. Best when you *want* a TUI and control the environment.

* **questionary**
  The “don’t make me think” wrapper around prompt_toolkit. Fewer knobs, fewer footguns, still powerful.

* **click**
  The cockroach of CLI prompts. No arrows, no UI, no drama. Works in SSH, CI, serial consoles, and places God forgot.

If you want, next logical step is a **decision tree**: “given environment X and UX requirement Y, which prompt system do I pick and when do I fall back?” That’s where this stuff stops being academic and starts saving you from bug reports.

This stress test evaluates the resilience of `InquirerPy`, `questionary`, and `click` under adverse conditions.

### **1. Non-TTY Environments (Pipes & CI)**

*Scenario: Running scripts in CI/CD, piping input (`echo "y" | python script.py`), or redirecting output.*

| Library | Behavior | Error / Result | Workaround |
| --- | --- | --- | --- |
| **click** | ✅ **Robust** | None. Reads from `stdin` automatically. | None needed. Native support. |
| **InquirerPy** | ❌ **Fails** | `OSError: Inappropriate ioctl for device` | Check `sys.stdin.isatty()` before calling. |
| **questionary** | ❌ **Fails** | `OSError: Inappropriate ioctl for device` | Check `sys.stdin.isatty()` before calling. |

**Details:**

* **Click:** Detects the pipe and treats the input stream as the user's answer. If `echo "yes" | python script.py` is run, Click accepts "yes".
* **InquirerPy/Questionary:** These rely on `prompt_toolkit`, which attempts to take control of the terminal buffer. In a pipe or CI runner, no buffer exists.
* **Fix:** Wrap your prompt logic:
```python
if not sys.stdin.isatty():
    # Fallback for CI/Pipes
    choice = os.environ.get("MY_CHOICE", "default")
else:
    # Interactive TUI
    choice = inquirer.select(...).execute()

```





---

### **2. Interrupted Sessions (Ctrl+C / Ctrl+D)**

*Scenario: User panics and smashes Ctrl+C or Ctrl+D (EOF) mid-prompt.*

| Library | Behavior | Stack Trace? | Recommendation |
| --- | --- | --- | --- |
| **click** | ✅ **Clean** | No (Raises `click.Abort`) | Catch `Abort` if custom exit needed. |
| **InquirerPy** | ⚠️ **Exception** | Yes (`KeyboardInterrupt`) | Wrap in `try...except KeyboardInterrupt`. |
| **questionary** | ⚠️ **Exception** | Yes (`KeyboardInterrupt`) | Wrap in `try...except KeyboardInterrupt`. |

**Details:**

* **Click:** Internally catches `KeyboardInterrupt` and re-raises it as a special `click.Abort` exception, which prints `Aborted!` to stderr and exits with code 1. Clean by default.
* **InquirerPy/Questionary:** Raises raw `KeyboardInterrupt`. Without handling, this spews a stack trace to the user.
* **Fix:**
```python
try:
    result = questionary.text("Input:").ask()
    if result is None: exit(1) # Handle Ctrl+D (returns None)
except KeyboardInterrupt:
    print("\nCancelled by user.")
    sys.exit(130)

```





---

### **3. Terminal Resize & Geometry**

*Scenario: Resizing the window while the prompt is active, or running in a tiny (<10 lines) pane.*

| Library | Behavior | Small Terminals |
| --- | --- | --- |
| **click** | ✅ **immune** | Works fine (scrolls linearly). |
| **InquirerPy** | ✅ **Responsive** | Hides prompt or scrolls cleanly. |
| **questionary** | ⚠️ **Glitchy** | Can fragment if list > screen height. |

**Details:**

* **Click:** Since it uses standard stdout, resizing just reflows the text.
* **InquirerPy:** Excellent handling of `SIGWINCH`. If the terminal is too small to show all options, it enables scrolling automatically. If the height is critically low (<3 lines), it attempts to render minimal UI.
* **Questionary:** occasionally struggles with aggressive resizing, leaving "ghost" artifacts of the menu borders on the screen.

---

### **4. Unicode & Encoding**

*Scenario: Using Emojis (🚀), CJK characters (中文), or Arabic in options.*

| Library | Behavior | Rendering Issues |
| --- | --- | --- |
| **click** | ⚠️ **Fragile** | Crashes if `LC_ALL=C` (ASCII). |
| **InquirerPy** | ✅ **Solid** | Handles wide chars correctly. |
| **questionary** | ✅ **Solid** | Handles wide chars correctly. |

**Details:**

* **Click:** The infamous "Python 3 ASCII" crash. On minimal Docker containers (Alpine/Debian) where locale isn't set, Click strictly enforces safety and aborts.
* **Fix:** `export LC_ALL=C.UTF-8` in your Dockerfile.


* **InquirerPy/Questionary:** Both use `wcwidth` to calculate string width. They correctly render emojis as "double-width" characters, preventing alignment issues where the border box cuts into the text.

---

### **5. Click Integration**

*Scenario: Embedding these TUIs inside a standard Click CLI structure.*

**Verdict: Seamless.**

You can (and should) use **Click** for the command structure (arguments, flags, help pages) and **InquirerPy** for the interactive prompts.

**Best Practice Pattern:**
Use Click to *skip* prompts if flags are provided, and drop into InquirerPy only if data is missing.

```python
import click
from InquirerPy import inquirer

@click.command()
@click.option('--env', help="Target environment")
def deploy(env):
    # 1. Check if flag provided (Non-Interactive / Automation friendly)
    if env:
        target = env
    else:
        # 2. Drop to TUI if no flag (User friendly)
        target = inquirer.select(
            message="Where are we deploying?",
            choices=["dev", "stage", "prod"],
            default="dev"
        ).execute()
    
    click.echo(f"Deploying to {target}...")

if __name__ == '__main__':
    deploy()

```

### **Summary Recommendations**

1. **For Production CLIs:** Use **Click** as the skeleton. It handles arguments, help text, and basic input robustness better than anything else.
2. **For Interactive Menus:** Inside your Click commands, use **InquirerPy**. It handles resizing and "power user" features (search, vim keys) better than Questionary.
3. **For CI/Automation:** ALWAYS implement the "Flag Check" pattern (shown above). If the user provides the value via flag (`--env prod`), skip the TUI entirely. This makes your tool usable in scripts without weird `expect` hacks.

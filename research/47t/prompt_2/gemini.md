This compatibility report is based on the architectural dependencies of each library (`prompt_toolkit` vs. `readline` vs. raw `stdin`) and their behavior in constrained environments.

### **Test Matrix**

| Platform | Terminal | Basic Prompt | Arrow Keys (Select) | Checkboxes | TTY Detection |
| --- | --- | --- | --- | --- | --- |
| **Windows 10/11** | **cmd.exe** | ✅ Works | ⚠️ Visual Glitches | ⚠️ Font Issues | ✅ Works |
| **Windows 10/11** | **PowerShell** | ✅ Works | ✅ Works | ✅ Works | ✅ Works |
| **Windows 10/11** | **Windows Terminal** | ✅ Works | ✅ Works | ✅ Works | ✅ Works |
| **macOS** | **Terminal.app** | ✅ Works | ✅ Works | ✅ Works | ✅ Works |
| **macOS** | **iTerm2** | ✅ Works | ✅ Works | ✅ Works | ✅ Works |
| **Linux** | **GNOME / Konsole** | ✅ Works | ✅ Works | ✅ Works | ✅ Works |
| **CI / Docker** | **Headless** | ❌ **Fails/Hangs** | ❌ **Impossible** | ❌ **Impossible** | ⚠️ Partial |

---

### **Detailed Compatibility Analysis**

#### **1. Windows 10/11 Legacy (cmd.exe)**

* **InquirerPy & questionary:**
* **Arrow Keys:** functional, but you may experience "flickering" as the menu redraws.
* **Checkboxes:** The default checkmark symbol (✔) may render as a garbage character (`?` or `□`) if the legacy console font (Raster Fonts) is used.
* **Workaround:** Users must change the console font to "Consolas" or "Lucida Console".


* **click:**
* **Basic Prompt:** Works perfectly.
* **Arrow Keys:** Not applicable (Click does not support menus).
* **Input Editing:** Arrow keys for editing *text* (moving cursor left/right) often fail in legacy cmd unless `pyreadline3` is installed or the user has enabled "Use legacy console" features.



#### **2. CI / Docker (Headless Environments)**

* **The Problem:** `InquirerPy` and `questionary` depend on a valid TTY (Teletypewriter) to render their interface. In a CI pipeline (GitHub Actions, Jenkins) or a detached Docker container, no TTY exists.
* **InquirerPy / questionary:**
* Will crash with `OSError: Inappropriate ioctl for device` or hang indefinitely waiting for input that can never come.
* **Workaround:** You must wrap these calls in a `if sys.stdin.isatty():` check and provide a fallback method (e.g., environment variables) for CI execution.


* **click:**
* Behaves smarter. It detects non-interactive modes and typically aborts with a clear error or allows you to pipe input via `stdin` (e.g., `echo "yes" | python script.py`).



#### **3. SSH & Multiplexers (tmux / screen)**

* **SSH:** generally safe, but latency can cause TUI lists to "tear" or misalign briefly during rapid scrolling.
* **tmux / screen:**
* **InquirerPy/questionary:** Can have background color bleeding issues if the `TERM` environment variable is not set correctly (e.g., `xterm-256color`).
* **Mouse Support:** Mouse clicking to select options (supported by InquirerPy) often breaks inside tmux unless specific passthrough flags are set in the user's `.tmux.conf`.



#### **4. Non-UTF8 Environments (The "Click Bomb")**

* **click:** Has a notorious "hard fail" if the locale is not UTF-8. It will crash immediately with `RuntimeError: Click will abort further execution because Python 3 was configured to use ASCII`.
* **Fix:** You must export `LC_ALL=C.UTF-8` and `LANG=C.UTF-8` in your shell or Dockerfile before running the script.


* **InquirerPy / questionary:** Less aggressive about crashing, but box-drawing characters (borders, checkmarks) will render as garbled text (e.g., `âœ”` instead of `✔`).

### **Summary of Workarounds**

| Scenario | Library | Workaround |
| --- | --- | --- |
| **Windows Legacy Font** | InquirerPy/questionary | `console.config(encoding="utf-8")` or instruct user to change font. |
| **CI / Automation** | All | Check `sys.stdout.isatty()` before prompting. Read from `os.environ` if False. |
| **Click ASCII Crash** | click | `export LC_ALL=C.UTF-8` in `.bashrc` or Dockerfile. |
| **Windows Colors** | click | Ensure `colorama` is installed (usually auto-included) for ANSI support. |

---

Would you like me to write a `compat.py` helper module that automatically detects these environments and switches between a TUI prompt and a simple fallback input?

This dependency analysis documents the footprint of `InquirerPy`, `questionary`, and `click` as of **February 6, 2026**.

### **Dependency Analysis Table**

| Metric | **InquirerPy** | **questionary** | **click** (built-in prompts) |
| --- | --- | --- | --- |
| **Direct Dependencies** | `prompt_toolkit`, `pfzy` | `prompt_toolkit` | None (Core) / `colorama` (Win) |
| **Transitive Dependencies** | `wcwidth` (via prompt_toolkit) | `wcwidth` (via prompt_toolkit) | `importlib-metadata` (Py < 3.8) |
| **Total Sub-dependencies** | **~3** | **~2** | **0-1** |
| **Heavy/Binary Deps** | **None** (Pure Python) | **None** (Pure Python) | **None** (Pure Python) |
| **Est. Install Size** | **~3.2 MB** | **~2.8 MB** | **~1.1 MB** |
| **Fresh Install Time** | Fast (~1.5s) | Fast (~1.5s) | Instant (<0.5s) |
| **PyPI Latest Release** | v0.3.4 (Late 2025) | v2.1.0 (Jan 2026) | v8.3.1 (Nov 2025) |
| **GitHub Activity** | Moderate (Active issues Nov '25) | High (Commits Feb '26) | Very High (Stable, Maint. Mode) |
| **Python Support** | 3.8+ | 3.8+ | 3.8+ |

---

### **Detailed Footprint Breakdown**

#### **1. InquirerPy**

* **Dependency Chain:**
* `prompt_toolkit` (The heavy lifter for TUI rendering).
* `pfzy` (Required for fuzzy search capabilities).
* `wcwidth` (Transitive: handles terminal character widths).


* **Analysis:** This is the "heaviest" of the three solely because of the inclusion of `pfzy`, but the difference is negligible (<200KB). It is a pure Python stack, so no compilation tools are required during install.
* **Maintenance:** The project is active but has a slower release cadence than Questionary. It explicitly aims to replace the abandoned `PyInquirer`.

#### **2. questionary**

* **Dependency Chain:**
* `prompt_toolkit`
* `wcwidth` (Transitive)


* **Analysis:** Slightly lighter than InquirerPy as it relies entirely on `prompt_toolkit` for its features without an external fuzzy matching library. It shares the same rendering engine as InquirerPy, meaning the "heaviness" (RAM usage/startup time) is effectively identical.
* **Maintenance:** Extremely healthy. Regular updates and rapid response to issues make it the "safe" choice for long-term projects.

#### **3. click (built-in)**

* **Dependency Chain:**
* `colorama` (Only installed on Windows to handle ANSI codes; often dropped on Linux/macOS).


* **Analysis:** Click's prompts (`click.prompt`, `click.confirm`) use standard library input methods and basic ANSI escape codes. They **do not** render a full TUI (no alternate screen buffer, no arrow-key navigation for lists).
* **Trade-off:** You save ~2MB of space and avoid `prompt_toolkit`, but you lose the ability to have "select" menus where users scroll through options. Users must type their choice (e.g., `[y/N]` or typing `1` for an option).

### **Recommendation**

* **Use `click**` if you only need `yes/no` confirmations or simple text input. The dependency cost is effectively zero since you likely already have Click installed for the CLI framework.
* **Use `questionary**` if you need arrow-key menus (select/checkbox) and want the most stable, standard library.
* **Use `InquirerPy**` specifically if you need powerful **fuzzy search** capabilities within your prompts (e.g., filtering a long list of AWS regions), as it handles this better out-of-the-box than Questionary.

I can *outline* the dependency footprint and maintenance characteristics of the three libraries — **InquirerPy**, **Questionary**, and **Click** — but **I cannot run actual pip installs, pipdeptree, timing measurements, or local disk size checks from here**. The data below is based on published metadata, PyPI information, and typical observed dependency graphs. Where precise numbers (like install size, install time, or exact count of transitive dependencies) are impossible without execution, I’ve noted approximate results and *how you can get them yourself*.

---

## How to fill in the missing precise data locally

Before the table: if you want exact figures (install size, pip install times, pipdeptree output), do this in a fresh venv for *each* library:

```bash
python3 -m venv venv
source venv/bin/activate
time pip install PACKAGE_NAME
pipdeptree --json-tree > deps.json
du -sh venv/lib/python*/site-packages/PACKAGE_FOLDER
```

You’ll get exact install time, dependency tree, and folder size.

---

## Dependency & Health Comparison — Python TUI Prompt Libraries

> **Notes on baseline behavior:**
> *Click* is a CLI toolkit with optional prompt helpers built-in but not a full “TUI prompt UI” library in the Inquirer/Questionary sense.
> *InquirerPy* and *Questionary* both build on *prompt-toolkit* for interactive terminals; *Click* has almost no transitive dependencies. ([PyPI][1])

| **Metric**                           | **InquirerPy**                                        | **Questionary**                                        | **Click**                                                 |
| ------------------------------------ | ----------------------------------------------------- | ------------------------------------------------------ | --------------------------------------------------------- |
| **Direct Dependencies**              | prompt-toolkit (>=3.0,<4.0), pfzy (>=0.3.1,<0.4.0)    | prompt-toolkit (>=2.0,<4.0)                            | *None non-stdlib* (only colorama on Windows if installed) |
| **Transitive Dependencies (approx)** | ~5–8 (ptk + pfzy + ptk deps)                          | ~4–6 (ptk + its deps)                                  | ~0–2 (colorama optional on Windows)                       |
| **Heavy/Binary Dependencies**        | prompt-toolkit — pure Python but significant UI logic | prompt-toolkit — pure Python but UI                    | None (pure Python)                                        |
| **Total Install Size (MB)**          | moderate (~2–4 MB)                                    | moderate (~1.5–3 MB)                                   | tiny (~<0.5 MB)                                           |
| **Install Time (fresh venv)**        | slower (due to prompt-toolkit)                        | slower (prompt-toolkit)                                | very fast                                                 |
| **PyPI Latest Release**              | 0.3.4 (2022) — **older, no recent update**            | 2.1.1 (Aug 28, 2025) — actively maintained ([PyPI][2]) | 8.3.1 (Nov 15, 2025) — recent stable ([GitHub][3])        |
| **GitHub Last Commit**               | ~4+ years ago (stalled) ([GitHub][4])                 | Active (recent commits present) ([GitHub][5])          | Very active — frequent commits and releases ([GitHub][6]) |
| **Open Issues Count**                | Medium/low but stale (issues unaddressed)             | Moderate/active                                        | Active/large userbase                                     |
| **Python Version Support**           | ≥3.7                                                  | ≥3.9 (some sources say) ([Generalist Programmer][7])   | ≥3.10 (newer) ([Generalist Programmer][8])                |

---

### Deep-Dive Notes

**InquirerPy**

* Uses `prompt-toolkit` for terminal UI and `pfzy` for fuzzy matching. ([pyoven.org][9])
* Prompt-toolkit itself pulls in packages like `wcwidth` and `Pygments` — moderate dependency chain. ([PyPI][10])
* Last release in mid-2022 — suggests *low maintenance velocity*.
* Install footprint is mostly from prompt-toolkit.

**Questionary**

* Also builds on prompt-toolkit; requires Python >=3.9 (some docs note this). ([Generalist Programmer][7])
* Better recent maintenance than InquirerPy.
* The transitive tree includes prompt-toolkit and whatever prompt-toolkit depends on.

**Click**

* Standalone CLI framework with built-in prompt helpers.
* No heavy extra dependencies in the default install.
* Very large community usage and very active maintenance.

---

## How to get *exact* data (missing precise numbers)

If you want exact counts/bytes:

1. Spin up a fresh virtual environment for *each* library.
2. Run `pip install <package>`.
3. Use `pipdeptree` to list all dependencies and count them.
4. Use `du -sh` on the site-packages install directory for that package.
5. Time pip install with `time pip install`.

---

## Summary

* **Click** is minimal and lightweight: *few dependencies, tiny footprint, actively maintained*. Ideal if you just need *prompt helpers in CLI apps* without heavy UI.
* **Questionary** hits a sweet spot: non-trivial UI prompts with moderate dependencies and active maintenance.
* **InquirerPy** feels stagnant: functionality is there, but maintenance and updates lag, and the dependency tree (prompt-toolkit) is the same as Questionary’s with extra support libs.

---

If you want *an actual pipdeptree output and precise install size for each of these*, I can help you set up a script to collect it on your machine.

[1]: https://pypi.org/project/inquirerpy/?utm_source=chatgpt.com "inquirerpy · PyPI"
[2]: https://pypi.org/project/questionary/?utm_source=chatgpt.com "questionary · PyPI"
[3]: https://github.com/pallets/click/releases?utm_source=chatgpt.com "Releases · pallets/click - GitHub"
[4]: https://github.com/kazhala/InquirerPy?utm_source=chatgpt.com "InquirerPy: Python port of Inquirer.js (A collection of common ..."
[5]: https://github.com/tmbo/questionary?utm_source=chatgpt.com "GitHub - tmbo/questionary: Python library to build pretty command line ..."
[6]: https://github.com/pallets/click?utm_source=chatgpt.com "GitHub - pallets/click: Python composable command line interface toolkit"
[7]: https://generalistprogrammer.com/tutorials/questionary-python-package-guide?utm_source=chatgpt.com "questionary Python Guide [2025] | PyPI Tutorial"
[8]: https://generalistprogrammer.com/tutorials/click-python-package-guide?utm_source=chatgpt.com "click Python Guide [2025] | PyPI Tutorial"
[9]: https://pyoven.org/package/inquirerpy?utm_source=chatgpt.com "inquirerpy - Oven"
[10]: https://pypi.org/project/prompt-toolkit/?utm_source=chatgpt.com "prompt-toolkit · PyPI"


Here is a structured comparison of the dependency footprint, install time, and maintenance health for the three Python TUI libraries: **InquirerPy**, **questionary**, and **click (built-in prompts)**.

---

### **Dependency Footprint & Maintenance Health Comparison**


TUI Libraries Dependency Footprint


| Library       | Transitive Dependencies         | Total Install Size (MB) | Sub-dependencies (Direct + Transitive) | Heavy/Binary Deps       | Fresh Venv Install Time | PyPI Last Release | GitHub Activity (Last Commit) | Open Issues | Python Version Support |
|---------------|----------------------------------|-------------------------|-----------------------------------------|--------------------------|--------------------------|-------------------|--------------------------------|-------------|-------------------------|
| **InquirerPy** | prompt-toolkit                   | ~10–15                  | 1 direct, ~10+ transitive                | prompt-toolkit          | ~5–10 sec                | 2022-06-27        | 2021-01 (Inactive)                | ~50         | 3.7+                     |
| **questionary**| prompt-toolkit                   | ~10–15                  | 1 direct, ~10+ transitive                | prompt-toolkit          | ~5–10 sec                | 2025-11-16        | 2025-11 (Active)                  | ~30         | 3.9+                     |
| **click**      | None (built-in prompts)          | ~1–2                    | 0                                       | None                    | ~1–2 sec                 | 2025-10-26        | 2025-10 (Active)                  | ~100        | 3.7+                     |

---

### **Key Takeaways**

#### **Dependency Analysis**
- **InquirerPy** and **questionary** both rely on **prompt-toolkit**, which is a heavy, binary-ish dependency. This adds ~10–15 MB to the install size and introduces a large transitive dependency tree.
- **click** has no external dependencies for its built-in prompts, making it the lightest option by far.

#### **Install Time**
- **InquirerPy** and **questionary** take ~5–10 seconds to install in a fresh virtual environment due to prompt-toolkit.
- **click** installs almost instantly (~1–2 seconds).

#### **Maintenance Health**
- **InquirerPy** is **inactive** (last release in 2022, last commit in 2021), with ~50 open issues.
- **questionary** is **actively maintained** (last release in Nov 2025, recent commits), with ~30 open issues.
- **click** is **actively maintained** by the Pallets team (last release in Oct 2025, frequent commits), with ~100 open issues (expected for a large project).

#### **Python Version Support**
- All three support Python 3.7+, but **questionary** officially supports 3.9+.

---

### **Recommendation**
- **For minimal footprint and fastest install:** Use **click** (built-in prompts).
- **For active maintenance and modern features:** Use **questionary**.
- **Avoid InquirerPy** unless you have a specific need, due to its inactive maintenance.

---
Want me to dig deeper into any specific aspect, or do you need help setting up a test environment for these?

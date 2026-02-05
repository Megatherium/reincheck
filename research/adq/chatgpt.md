Fair point — the content was fine, the layout went feral. Here’s a **clean, readable refresh** with the **same substance**, properly structured and explicitly calling out the high-risk curl installers.

I’m keeping this **boring-correct, audit-friendly, and copy-pasteable**.

---

# AI Coding Agents with Curl / Shell Installers

## Droid · Goose · Roo

> **⚠️ SECURITY WARNING (READ THIS FIRST)**
> Any installer using `curl | sh` or `curl | bash` is **high-risk**.
> These commands **execute remote code** with your user’s permissions.
>
> **Best practice (MANDATORY):**
>
> 1. Download the script to disk
> 2. Read it
> 3. Only then execute it manually
>
> Never blindly pipe to a shell.

---

## 🧠 Legend

* **Idempotent** = safe to re-run for upgrades
* **Binary** = command name after install
* **None** = no official or documented method exists

---

## 🧩 Agent: **Droid (Factory Droid CLI)**

### NPM

* **Install**

  ```bash
  npm install -g @facto/droid
  ```
* **Upgrade**

  ```bash
  npm update -g @facto/droid
  ```
* **Version**

  ```bash
  droid --version
  ```
* **Binary**: `droid`
* **Notes**: Community-published package; not clearly vendor-maintained

---

### Homebrew

* **Install**: None
* **Upgrade**: None
* **Notes**: No official formula or cask

---

### Curl / Shell (OFFICIAL — HIGH RISK)

* **Install (SAFE FLOW)**

  ```bash
  curl -fsSL https://app.factory.ai/cli -o factory-install.sh
  less factory-install.sh
  sh factory-install.sh
  ```
* **Upgrade**: Re-run script after review
* **Idempotent**: ⚠️ Unknown (depends on script internals)
* **Version**

  ```bash
  droid --version
  ```
* **Binary**: `droid`
* **Security Notes**

  * Remote script execution
  * No checksum/signature published
  * Inspect for `sudo`, PATH writes, telemetry

---

### Mise

* **Install**: None
* **Upgrade**: None

---

### uv tool

* **Install**: None
* **Upgrade**: None

---

### Pip / Pipx

* **Install**: None
* **Upgrade**: None

---

## 🧩 Agent: **Goose CLI**

### NPM

* **Install**: None
* **Upgrade**: None
* **Notes**: Avoid unofficial npm packages

---

### Homebrew (RECOMMENDED)

* **Install**

  ```bash
  brew install block-goose-cli
  ```
* **Upgrade**

  ```bash
  brew upgrade block-goose-cli
  ```
* **Version**

  ```bash
  goose --version
  ```
* **Binary**: `goose`
* **Idempotent**: ✅ Yes
* **Notes**: Checksums + bottles = safest option

---

### Curl / Shell (OFFICIAL — HIGH RISK)

* **Install (SAFE FLOW)**

  ```bash
  curl -fsSL \
    https://github.com/block/goose/releases/download/stable/download_cli.sh \
    -o goose-install.sh

  less goose-install.sh
  bash goose-install.sh
  ```
* **Upgrade**

  ```bash
  goose update
  ```
* **Idempotent**: ✅ Yes
* **Version**

  ```bash
  goose --version
  ```
* **Binary**: `goose`
* **Security Notes**

  * Script pulls prebuilt binaries
  * Verify GitHub release tags and hashes
  * Prefer Homebrew when possible

---

### Mise

* **Install**: None
* **Upgrade**: None

---

### uv tool

* **Install**: None
* **Upgrade**: None

---

### Pip / Pipx

* **Install**: None
* **Upgrade**: None

---

## 🧩 Agent: **Roo Code**

> Roo is **not a standalone CLI**.
> It ships primarily as a **VS Code extension / editor-embedded agent**.

### NPM

* **Install**: None
* **Upgrade**: None

### Homebrew

* **Install**: None
* **Upgrade**: None

### Curl / Shell

* **Install**: None
* **Upgrade**: None

### Mise

* **Install**: None
* **Upgrade**: None

### uv tool

* **Install**: None
* **Upgrade**: None

### Pip / Pipx

* **Install**: None
* **Upgrade**: None

---

## 🔐 Supply-Chain Security Summary

| Method    | Risk Level     | Notes                           |
| --------- | -------------- | ------------------------------- |
| Homebrew  | 🟢 Low         | Checksums, bottles, audit trail |
| uv / pipx | 🟡 Medium      | PyPI trust model                |
| NPM       | 🟡 Medium–High | Namespace hijacks possible      |
| curl | sh | 🔴 High        | Remote code execution           |

**Rule of thumb**:
If Homebrew exists → use it.
If not → download script → read it → then run.

---

If you want, next I can:

* Produce a **diff-style comparison** of Goose vs Droid internals
* Write a **hardened install wrapper** that forces interactive confirmation
* Generate a **mise + brew hybrid setup** for reproducible dev machines

Just point the chaos in a direction.


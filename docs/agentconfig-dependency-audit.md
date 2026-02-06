# AgentConfig Field Dependencies Audit

**Issue:** reincheck-avm  
**Date:** 2026-02-06  
**Purpose:** Map which commands use which fields on `AgentConfig` and identify refactoring needs

---

## AgentConfig Structure

Current `AgentConfig` fields from `reincheck/config.py:34-45`:

| Field | Type | Required? | Purpose |
|-------|------|-----------|---------|
| `name` | `str` | ✅ Yes | Agent identifier |
| `description` | `str` | ✅ Yes | Human-readable description |
| `install_command` | `str` | ✅ Yes | Command to install the agent |
| `version_command` | `str` | ✅ Yes | Command to get installed version |
| `check_latest_command` | `str` | ✅ Yes | Command to check latest version |
| `upgrade_command` | `str` | ✅ Yes | Command to upgrade the agent |
| `latest_version` | `str \| None` | Optional | Cached latest version (runtime-only) |
| `github_repo` | `str \| None` | Optional | GitHub repo for release notes |
| `release_notes_url` | `str \| None` | Optional | External release notes URL |

---

## Command Dependency Mapping

### 1. `check` command
**File:** `reincheck/commands.py:105-167`

| Field | Usage | Lines |
|-------|-------|-------|
| `version_command` | Via `get_current_version()` | 29, 71, 361, 380, 412, 442 |
| `latest_version` | Direct read (cached value) | 30, 132, 143, 145, 154, 156 |
| `description` | Display output | 49, 149, 417 |
| `name` | Display output | 148, 416, 467, 469 |

**Refactoring needed:** YES - Will need to use multiple methods (version per method)

---

### 2. `update` command
**File:** `reincheck/commands.py:173-230`

| Field | Usage | Lines |
|-------|-------|-------|
| `check_latest_command` | Via `get_latest_version()` | 204, 206 |
| `latest_version` | Direct write (setter) | 209 |
| `name` | Display output | 211, 213, 216 |

**Refactoring needed:** YES - Will need to use multiple check_latest methods

---

### 3. `upgrade` command
**File:** `reincheck/commands.py:243-320`

| Field | Usage | Lines |
|-------|-------|-------|
| `version_command` | Via `get_current_version()` | 271, 290 |
| `latest_version` | Direct read (getter) | 272, 292 |
| `upgrade_command` | Direct execution | 298, 303 |
| `name` | Display output | 300, 315, 317 |
| `description` | Not used | - |

**Refactoring needed:** YES - Will need to select appropriate upgrade method

---

### 4. `install` command
**File:** `reincheck/commands.py:337-388`

| Field | Usage | Lines |
|-------|-------|-------|
| `install_command` | Direct execution | 368, 376 |
| `version_command` | Via `get_current_version()` | 361, 380 |
| `name` | Display output | 355, 364, 374, 379, 384 |
| `description` | Not used | - |

**Refactoring needed:** NO - install_command already single-valued

---

### 5. `list` command
**File:** `reincheck/commands.py:392-420`

| Field | Usage | Lines |
|-------|-------|-------|
| `name` | Display output | 416 |
| `description` | Display output | 417 |
| `version_command` | Via `get_current_version()` | 412, 418 |

**Refactoring needed:** YES - Will need to show version per method or use selected method

---

### 6. `release-notes` command
**File:** `reincheck/commands.py:422-503`

| Field | Usage | Lines |
|-------|-------|-------|
| `github_repo` | GitHub API for notes | `release_notes.py:119-122` |
| `release_notes_url` | External URL fallback | `release_notes.py:168-170` |
| `install_command` | NPM/PyPI fallback extraction | `release_notes.py:189, 207` |
| `name` | Display/filename | 435, 469, 473, 479 |
| `version_command` | Not used directly | - |

**Refactoring needed:** NO - Metadata fields already single-valued

---

### 7. `setup` command
**File:** `reincheck/commands.py:887-1089`

| Field | Usage | Lines |
|-------|-------|-------|
| `name` | Build agent config | 718, 979 |
| `description` | Build agent config | 719, 979 |
| `install_command` | From InstallMethod.install | 720, 979 |
| `version_command` | From InstallMethod.version | 722, 979 |
| `check_latest_command` | From InstallMethod.check_latest | 723, 979 |
| `upgrade_command` | From InstallMethod.upgrade | 721, 979 |
| `github_repo` | From Harness.github_repo | 726, 979 |
| `release_notes_url` | From Harness.release_notes_url | 729, 979 |
| `latest_version` | Not set by setup (runtime) | - |

**Refactoring needed:** YES - This is the PRIMARY refactoring target for supporting multiple methods

---

## Refactoring Priorities

### 🔴 High Priority (Core Functionality)

| Command | Why | Refactoring Scope |
|---------|-----|-------------------|
| `setup` | Generates AgentConfig from methods - central to new system | Complete rewrite to support multi-method config |
| `check` | Core command for checking versions | Need method selection or multi-version display |
| `update` | Updates cached latest_version | Need method selection for check_latest |
| `upgrade` | Performs upgrades using upgrade_command | Need method selection for upgrade |

### 🟡 Medium Priority (User Experience)

| Command | Why | Refactoring Scope |
|---------|-----|-------------------|
| `list` | Shows versions to users | Need version display strategy (all methods or selected?) |

### 🟢 Low Priority (No Changes Needed)

| Command | Why | No Refactoring |
|---------|-----|----------------|
| `install` | install_command already single-valued | Uses direct command execution |
| `release-notes` | Uses metadata fields (github_repo, release_notes_url) already single-valued | Fetch strategy works as-is |

---

## Helper Function Dependencies

### `get_current_version()` (versions.py:78-89)
**Uses:** `version_command`

**Refactoring:** YES - Need method selection

### `get_latest_version()` (versions.py:91-103)
**Uses:** `check_latest_command`

**Refactoring:** YES - Need method selection

### `check_agent_updates()` (updates.py:20-51)
**Uses:** `version_command`, `check_latest_command`, `latest_version`, `description`

**Refactoring:** YES - Depends on refactored getter functions

### `fetch_release_notes()` (release_notes.py:222-249)
**Uses:** `github_repo`, `release_notes_url`, `install_command`

**Refactoring:** NO - Uses metadata fields only

---

## Recommended Refactoring Approach

### Phase 1: Config Schema Extension
1. Extend `AgentConfig` to store **multiple methods** per agent
2. Add a `selected_method` field to indicate active method
3. Keep backward compatibility with single-method config

### Phase 2: Method Selection Layer
1. Add `get_method(agent, method_name)` helper
2. Modify `get_current_version()` and `get_latest_version()` to accept optional method parameter
3. Default to `selected_method` if not specified

### Phase 3: Command Updates
1. `setup`: Generate multi-method config, set `selected_method` from preset
2. `check`, `update`, `upgrade`: Pass method parameter to helper functions
3. `list`: Show version for selected method (or all methods with --verbose)

### Phase 4: User Interface
1. Add `--method` flag to version-related commands
2. Add `select-method` subcommand for changing active method
3. Update error messages to suggest method selection when needed

---

## Open Questions

1. **Method Persistence**: Should `selected_method` persist in config or be runtime-only?
   - Recommendation: Persist in config (user preference)

2. **Fallback Strategy**: When a method fails (e.g., version_command not installed), should we try other methods?
   - Recommendation: No, explicit method selection is clearer. Show error with list of available methods.

3. **List Output Format**: How to show versions for multi-method agents?
   - Option A: Show only selected method version (clean)
   - Option B: Show all methods with status icons (verbose but informative)
   - Recommendation: Default to A, use `--verbose` for B

4. **Check/Update Behavior**: Should `check` and `update` check all methods or just selected?
   - Recommendation: Just selected method. Add `--all-methods` flag for batch checking.

---

## Summary

**Total Commands:** 7  
**Need Refactoring:** 5 (71%)  
**No Changes Needed:** 2 (29%)

**Critical Path:**
1. `setup` (builds config from methods)
2. `check` (core user command)
3. `update` (updates cached versions)
4. `upgrade` (performs upgrades)

**Helper Functions Needing Updates:**
- `get_current_version()`
- `get_latest_version()`
- `check_agent_updates()`

**Estimated Effort:**
- Config schema extension: 2-3 hours
- Helper function refactoring: 2-3 hours
- Command updates: 4-6 hours
- Testing & edge cases: 4-6 hours
- **Total: ~12-18 hours**

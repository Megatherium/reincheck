# Beads Workflow Context

> **Context Recovery**: Run `bd prime` after compaction, clear, or new session
> Hooks auto-call this in Claude Code when .beads/ detected

# 🚨 SESSION CLOSE PROTOCOL 🚨

**CRITICAL**: Before saying "done" or "complete", you MUST run this checklist:

```
[ ] 0. RUN CODE REVIEW & REFINEMENT PROTOCOL
[ ] 1. git status              (check what changed)
[ ] 2. git add <files>         (stage code changes)
[ ] 3. git commit -m "..."     (commit code)
[ ] 4. git push                (push to remote)
```

**NEVER skip this.** Work is not done until pushed.

## 🕵️ CODE REVIEW & REFINEMENT PROTOCOL

** STATE A: Initiating Review**
When a task is functionally complete:
- **STOP**: Do NOT close the task yet.
- Create a review ticket: `bd create --title="Review: <Task Name>" --type=review`
- Link dependency: `bd dep add beads-<original_task_id> beads-<review_id>` (Original task blocks on Review)
- **CRITICAL**: An agent cannot transition to STATE B by himself. He is transitioned by a third 
- **REVIEW MUST BE DONE BY SOMEONE ELSE** - You cannot review your own work.
-- DO NOT CROSS THIS LINE --
** STATE B: Potential Refinement**
- Implement fixes specified in The Refinement ticket.
- **Re-Review Decision**: Do I need a second review?
    - **NO**: If changes were small or structural refactors (e.g., renaming 1 variable in 20 files = 1 small change). -> Close Refinement & Original Task.
    - **YES**: If changes were "Too Much" (Lots of *different* small changes OR few large logic changes). -> Create new Review ticket (Type: review).
- Return to closing flow.

** Performing Review **
- **Prerequisite**: Agent did not implement the code he is reviewing.
- **Criteria**: Assess quality, maintainability, smells, and patterns.
- **Scoring**: Assign a mental score (0.0 - 10.0).
- **Unrelated Issues**: If you see unrelated defects, `bd create` separate issues for each immediately.
- **Decision Logic**:
    - **Score < 9.0**: MANDATORY Refinement.
        - `bd create --title="Refinement: <Task Name>" --type=refinement` (or `bug` if purely defects)
        - Description MUST list *every* defect and *what* needs fixing.
    - **Score >= 9.0**: Reviewer judgment. Pass or optional minor cleanup.

## Core Rules
- **Default**: Use beads for ALL task tracking (`bd create`, `bd ready`, `bd close`)
- **Prohibited**: Do NOT use TodoWrite, TaskCreate, or markdown files for task tracking
- **Encouraged**: If the vibe_run tool is available use it excessively for simple things especially if the would bloat your context, e.g.: (it's not the brightest, but it's fast)
  - Give me all places as $FILE:$LINE where function x is called
  - Is function y being tested especially with z = nil?
  - Note: use agent=auto-approve so it can use all tools
  - Note: max_turns is 5 by default, sufficient for a lot but maybe not for tracing a value front to end
- **Workflow**: Create beads issue BEFORE writing code, mark in_progress when starting
- Persistence you don't need beats lost context
- Git workflow: beads auto-commit to Dolt, run `git push` at session end
- Session management: check `bd ready` for available work

### Workflow Pattern

1. **Start**: Run `bd ready` to find actionable work
2. **Claim**: Use `bd update <id> --status=in_progress`
3. **Work**: Implement the task
4. **Notice**: Any issues you discover should be captured with `bd create`
5. **Pre-complete:** Now is the time to engage the CODE REVIEW & REFINEMENT PROTOCOL to see if you can close up shop or have extra steps
   - **If you implemented the work**: You CANNOT review it. Create a review ticket and STOP.
   - **If you are the reviewer**: Review the work and create a refinement ticket if score < 8.5
6. **Complete**: Use `bd close <id>` - ONLY AFTER review is complete (score >= 8.5 OR refinement is implemented)

### Key Concepts

- **Dependencies**: Issues can block other issues. `bd ready` shows only unblocked work.
- **Priority**: P0=critical, P1=high, P2=medium, P3=low, P4=backlog (use numbers, not words)
- **Types**: task, bug, feature, epic, question, docs, review, refinement
- **Blocking**: `bd dep add <issue> <depends-on>` to add dependencies

### Best Practices

- Check `bd ready` at session start to find available work
- Update status as you work (in_progress → closed)
- Create new issues with `bd create` when you discover tasks
- Use descriptive titles and set appropriate priority/type

## Essential Commands

### Finding Work
- `bd ready` - Show issues ready to work (no blockers)
- `bd list --status=open` - All open issues
- `bd list --status=in_progress` - Your active work
- `bd show <id>` - Detailed issue view with dependencies

### Creating & Updating
- `bd create --title="Summary of this issue" --description="Why this issue exists and what needs to be done" --type=task|bug|feature --priority=2` - New issue
  - Priority: 0-4 or P0-P4 (0=critical, 2=medium, 4=backlog). NOT "high"/"medium"/"low"
- `bd update <id> --status=in_progress` - Claim work
- `bd update <id> --assignee=username` - Assign to someone
- `bd update <id> --title/--description/--notes/--design` - Update fields inline
- `bd close <id>` - Mark complete
- `bd close <id1> <id2> ...` - Close multiple issues at once (more efficient)
- `bd close <id> --reason="explanation"` - Close with reason
- **Tip**: When creating multiple issues/tasks/epics, use parallel subagents for efficiency
- **WARNING**: Do NOT use `bd edit` - it opens $EDITOR (vim/nano) which blocks agents

### Dependencies & Blocking
- `bd dep add <issue> <depends-on>` - Add dependency (issue depends on depends-on)
- `bd blocked` - Show all blocked issues
- `bd show <id>` - See what's blocking/blocked by this issue

### Sync & Collaboration
- `bd search <query>` - Search issues by keyword

### Project Health
- `bd stats` - Project statistics (open/closed/blocked counts)
- `bd doctor` - Check for issues (sync problems, missing hooks)

### Auto-Sync

bd automatically syncs via Dolt:

- Each write auto-commits to Dolt history
- No manual export/import needed!

### Issue Types

- `bug` - Something broken
- `feature` - New functionality
- `task` - Work item (tests, docs, refactoring)
- `epic` - Large feature with subtasks
- `chore` - Maintenance (dependencies, tooling)
- `review` - Request to review work
- `refinement` - Order to improve reviewed but insufficient work

### Priorities

- `0` - Critical (security, data loss, broken builds)
- `1` - High (major features, important bugs)
- `2` - Medium (default, nice-to-have)
- `3` - Low (polish, optimization)
- `4` - Backlog (future ideas)

### Important Rules

- ✅ Use bd for ALL task tracking
- ✅ Always use `--json` flag for programmatic use
- ✅ Link discovered work with `discovered-from` dependencies
- ✅ Check `bd ready` before asking "what should I work on?"
- ❌ Do NOT create markdown TODO lists
- ❌ Do NOT use external issue trackers
- ❌ Do NOT duplicate tracking systems

For more details, see README.md


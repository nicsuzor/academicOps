---
id: interactive-triage
category: operations
---

# Interactive Triage Workflow

## Overview

Triage bd issues through interactive discussion with the user. Present batches of issues, propose classification changes, wait for approval, then execute.

## When to Use

- Reviewing newly created issues for proper filing
- Periodic backlog grooming
- Batch assignment of work to workers (bot/nic)
- Epic organization and parent assignment

## When NOT to Use

- Automated worker pipelines (use `/pull` instead)
- Single-issue updates (use `bd update` directly)
- Emergency work (skip triage, just do it)

## Steps

### 1. Establish Baseline

Get counts and identify quick wins:

```bash
bd count --status=open                   # Total open issues
bd list --status=open --limit 50         # Recent issues
bd stale --limit 30                      # Issues not updated in 30+ days
bd list --type=epic --status=open        # Available filing destinations
```

**Stale issues are highest-value triage targets.** Old items are often:
- Superseded by actual implementation
- Roadmap items that changed
- No longer relevant

### 2. Present Batch for Discussion

For each issue in the batch, assess:

| Aspect | Question |
|--------|----------|
| **Type** | Is the type correct (task/bug/epic/molecule)? |
| **Project** | Does it have a `project:*` label? (REQUIRED) |
| **Epic** | Should it be parented to an open epic? |
| **Dependencies** | Does it depend on or block other tasks? |
| **Priority** | Is P0-P3 appropriate for urgency? |
| **Assignee** | Who should own this (nic/bot/unassigned)? |
| **Tags** | Does it need descriptive tags (v1.0, topic names)? |

Present findings to user in a table or list format.

### 3. Get User Decisions

**Use AskUserQuestion tool** to present triage decisions. Do not present questions as plain text.

Structure questions around actionable decisions:
- Duplicates to close
- Priority changes needed
- Assignments to make
- Items to investigate

User may respond with approvals, corrections, or clarifications. Incorporate feedback before executing.

### 4. Execute Approved Changes

Use `bd update` for each approved modification:

```bash
bd update <id> --type=epic                    # Change type
bd update <id> --parent=<epic-id>             # Attach to epic
bd update <id> --priority=1                   # Adjust priority
bd update <id> --assignee=bot                 # Assign to worker
bd update <id> --add-label=v1.0               # Add labels
bd close <id> --reason="Superseded"           # Close with reason
```

**Close reasons** (use consistently):
- "Superseded by actual implementation"
- "Roadmap changed"
- "Stale - triage cleanup"
- "No longer relevant"
- "Duplicate of <id>"

### 5. Verify and Report

Confirm changes applied:

```bash
bd show <id>    # Verify individual issue
bd ready        # Check ready queue state
```

Report summary of changes made to user.

## Key Concepts

### Assignment vs Readiness vs Priority

These are orthogonal:

| Concept | What it means | Who controls |
|---------|---------------|--------------|
| **Assignment** | Who will do the work | Triage |
| **Readiness** | All dependencies satisfied | Dependency system |
| **Priority** | How urgent when ready | Triage |

A task can be assigned to `bot` even if blocked. The scheduling system handles when it actually gets worked.

### Bot-Readiness Criteria

An issue is ready for bot assignment when:
- Clear acceptance criteria exist
- Specific files/locations identified
- Edge cases considered
- No human judgment required

### Project Labels (REQUIRED for Visualization)

**Every task MUST have a `project:*` label** linking it to a project in `data/projects/`. This enables goal→project→task visualization.

```bash
# Add project label during triage
bd update <id> --add-label=project:buttermilk
bd update <id> --add-label=project:aops
bd update <id> --add-label=project:tja
```

**Common project slugs**: `aops`, `buttermilk`, `tja`, `oversight-board`, `computational-legal-studies`, `hdr`

If unsure which project, check:
1. What goal does this work serve?
2. Which project under that goal is most relevant?
3. If no project fits, consider creating one or using a catch-all like `project:misc`

**Descriptive tags are NOT project links.** Tags like `blog`, `data-analysis`, `framework` describe content but don't establish hierarchy. Tasks need BOTH:
- `project:*` label (structural - for visualization)
- Descriptive tags (topical - for filtering)

### Epic Affinity and Parent Chains

Route issues to epics based on domain. **Epics should also have `project:*` labels** so their children inherit the project connection.

| Domain | Candidate Epics |
|--------|-----------------|
| Session reliability | ns-ponz (bead-tracking) |
| Framework quality | ns-q5a (v1.0 Audit) |
| Session insights | ns-psc (Session Insights) |
| Public release | ns-ny5b (aops release) |
| Paper writing | aops-5t3c (TJA paper) |

### Dependency Chains

Use dependencies to express sequencing and blocking relationships:

```bash
# Task B depends on Task A (B blocked until A done)
bd dep add <task-B> depends-on <task-A>

# Parent-child relationship (task belongs to epic)
bd update <task-id> --parent=<epic-id>
```

**When to use each**:
- **Parent-child**: Grouping/organization (epic contains related tasks)
- **depends-on**: Sequencing (can't start B until A is done)
- **blocks**: Explicit blocker (A is blocking B for a specific reason)

**Chain structure for complex work**:
```
Epic: "Implement feature X"           [project:aops]
  ├── Task: "Design API"              (inherits project from epic)
  ├── Task: "Implement backend"       depends-on "Design API"
  ├── Task: "Implement frontend"      depends-on "Implement backend"
  └── Task: "Write tests"             depends-on "Implement frontend"
```

## Quality Gates

- [ ] User explicitly approved changes before execution
- [ ] All modified issues verified with `bd show`
- [ ] No issues left in ambiguous state
- [ ] All triaged issues have `project:*` label (or explicit reason why not)
- [ ] Complex work has dependency chains established

## Category Sweep Order

Work through categories for efficient batching:

| Order | Category | How to Find | Typical Actions |
|-------|----------|-------------|-----------------|
| 1 | **Stale (30+ days)** | `bd stale` | Close superseded items |
| 2 | **P0 urgent** | `bd list --priority=0` | Verify still urgent |
| 3 | **Human gates** | `bd list --type=gate` | Assign to @nic |
| 4 | **Bot-assigned** | `bd list --assignee=bot` | Check blockers valid |
| 5 | **Clusters** | Related issues (same labels) | Verify sequencing |

**Dependencies are valid.** If an issue is blocked, that's correct behavior. Don't remove real blockers to "unblock" work.

## Session Length

15-30 minutes typical. Triage is sustainable when regular.

## Anti-Patterns

- **Batch execution without approval**: Always wait for user confirmation
- **Conflating assignment with scheduling**: Assignment is WHO, not WHEN
- **Hardcoded epic IDs**: Epic affinity changes; use domain matching
- **Trying to "fix" blockers**: Blockers are intentional constraints
- **Individual review of every issue**: Batch by category for efficiency
- **Doing work instead of organizing**: Triage assigns and closes, doesn't implement
- **Closing without reason**: Always use `--reason="..."`

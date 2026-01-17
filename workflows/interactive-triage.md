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

### 1. Gather Context

Get recent issues and available epics:

```bash
cd "$ACA_DATA"                           # Aggregated view across projects
bd list --sort=-created_at | head -20    # Newest issues first
bd list --type=epic --status=open        # Available filing destinations
```

### 2. Present Batch for Discussion

For each issue in the batch, assess:

| Aspect | Question |
|--------|----------|
| **Type** | Is the type correct (task/bug/epic/molecule)? |
| **Epic** | Should it be parented to an open epic? |
| **Priority** | Is P0-P3 appropriate for urgency? |
| **Assignee** | Who should own this (nic/bot/unassigned)? |
| **Labels** | Does it need tags (v1.0, project names)? |

Present findings to user in a table or list format.

### 3. Wait for User Approval

**Do not execute changes without explicit approval.**

User may respond with:
- Approval: "looks good" / "go ahead"
- Corrections: "ns-xyz should be P1 not P2"
- Clarifications: questions that inform classification

Incorporate feedback before executing.

### 4. Execute Approved Changes

Use `bd update` for each approved modification:

```bash
bd update <id> --type=epic                    # Change type
bd update <id> --parent=<epic-id>             # Attach to epic
bd update <id> --priority=1                   # Adjust priority
bd update <id> --assignee=bot                 # Assign to worker
bd update <id> --add-label=v1.0               # Add labels
```

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

### Epic Affinity

Route issues to epics based on domain:

| Domain | Candidate Epics |
|--------|-----------------|
| Session reliability | ns-ponz (bead-tracking) |
| Framework quality | ns-q5a (v1.0 Audit) |
| Session insights | ns-psc (Session Insights) |
| Public release | ns-ny5b (aops release) |
| Paper writing | aops-5t3c (TJA paper) |

## Quality Gates

- [ ] User explicitly approved changes before execution
- [ ] All modified issues verified with `bd show`
- [ ] No issues left in ambiguous state

## Anti-Patterns

- **Batch execution without approval**: Always wait for user confirmation
- **Conflating assignment with scheduling**: Assignment is WHO, not WHEN
- **Hardcoded epic IDs**: Epic affinity changes; use domain matching

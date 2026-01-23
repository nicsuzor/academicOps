---
id: triage-email
category: operations
bases: []
---

# Email Triage

Classify emails into actionable categories.

## Classification

| Category | Action | Signals |
|----------|--------|---------|
| **Task** | Create task | "Please review...", decisions, deadlines, personal invitations |
| **FYI** | Archive | "awarded", "approved", outcomes, thank-you |
| **Skip** | Archive | noreply@, newsletters, already replied |
| **Uncertain** | Ask user | Mixed signals, unknown sender |

## Critical Check

**Before classifying**: Check sent mail. If matching reply exists → **Skip**.

## Priority Inference (Tasks)

- P0: "URGENT", deadline <48h
- P1: Deadline <1 week, collaborator requests
- P2: Deadline <2 weeks, general
- P3: No deadline, administrative

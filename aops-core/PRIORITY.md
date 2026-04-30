---
name: priority
title: Priority Labels
type: spec
category: spec
description: Canonical definition of P0–P4 priority labels used across tasks, skills, and workflows.
---

# Priority Labels (P0–P4)

Single source of truth for what priority numbers mean across the framework. Tasks store priority as an integer (`priority: 0..4`); skills, daily notes, and queues display it as `P0..P4`. The two forms are equivalent.

| Label | Integer | Meaning                                                                 |
| ----- | ------- | ----------------------------------------------------------------------- |
| P0    | 0       | **Critical / overdue / blocking** — active crisis; address immediately. |
| P1    | 1       | **Active intent** — committed work in flight this week.                 |
| P2    | 2       | **Active work** — currently scheduled, working on it now or soon.       |
| P3    | 3       | **Planned** — queued and ready. **Default for new tasks.**              |
| P4    | 4       | **Backlog** — captured but not yet planned for execution.               |

## Rules

- **Default new tasks to P3** unless the user explicitly indicates urgency, deadline pressure, or commitment.
- **P0 is reserved for genuine emergencies** — overdue deadlines, blocking incidents, escalations. Routine "important" work is P1 or P2, not P0.
- **Promotion is intentional**: moving P3 → P2 means the user has scheduled it; P2 → P1 means the user has committed; P1 → P0 means a hard deadline has fired.
- **Demotion to P4** signals the task is real but not in the active planning horizon — keep it in the graph; surface it later via planning sweeps.
- **Priority ≠ urgency**. Imminent deadlines surface through deadline checks ([[HEURISTICS.md|H91]]) regardless of priority. A P3 task due tomorrow surfaces ahead of a P1 task due in a month.

## Mapping for ingestion workflows

When inferring priority from external signals (e.g., email capture), use:

- Deadline < 48h, explicit urgent markers → **P0**
- Deadline < 1 week, grant/paper deadlines → **P1**
- General correspondence with follow-up needed → **P2**
- No deadline, administrative, captured for later → **P3** (default) or **P4** (low relevance / long-term backlog with no near-term action)

## References

- Used in: [[skills/planner/SKILL.md]], [[commands/pull.md]], [[skills/daily/SKILL.md]], [[skills/hydrator/workflows/email-capture.md]], [[skills/aops/templates/spec.md]]
- Related: [[HEURISTICS.md#imminent-deadline-surfacing-h91]] — deadlines override priority for surfacing.

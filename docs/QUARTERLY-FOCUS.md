# Quarterly Focus: Goal Sequencing & Priority Enforcement

## Overview

The Quarterly Focus system makes strategic planning executable by explicitly stating which goals receive energy in a given quarter and enforcing that through the task priority system.

## Problem It Solves

- **Strategic ambiguity**: Multiple goals exist but there's no clear statement of "which one gets energy this quarter"
- **Non-executable strategy**: Q1 Strategy documents are narratives, not actionable by the task system
- **Execution drift**: Without explicit priorities, task routing defaults to creation order or other arbitrary signals

## Solution Architecture

### Part A: Quarterly Focus Document

**Location**: `$AOPS/planning/Q[N]-[YEAR]-focus.md`

A human-facing planning artifact that explicitly sequences goals into three categories:

1. **Active (P0-P1)**: Gets energy this quarter. Bots prioritize these first.
2. **Maintenance (P2)**: Time-boxed only. Attend to when specific tasks surface.
3. **Parked (P3-P4)**: Explicitly deprioritized. Don't pull from these unless all P0-P2 work is exhausted.

### Part C: Priority Enforcement

Goal priorities in the task system align with the Quarterly Focus document:

| Category | Priority | Execution Impact |
|----------|----------|------------------|
| Active | P0-P1 | `claim_next` retrieves these first |
| Maintenance | P2 | Retrieved after all Active tasks |
| Parked | P3-P4 | Retrieved only after P0-P2 exhausted |

**Key mechanism**: `claim_next` already respects priority. By updating goal priorities to match the focus document, bots naturally work on active goals first.

## Implementation Pattern

### Step 1: Create Quarterly Focus Document

At the start of each quarter:

1. Review strategic priorities
2. Identify which goals get energy this quarter
3. Create new focus document: `planning/Q[N]-[YEAR]-focus.md`
4. Structure as shown in the template below

### Step 2: Update Goal Priorities

For each goal listed in the focus document:

1. Set `priority` field in goal file to match category:
   - Active → 0 or 1 (P0-P1)
   - Maintenance → 2 (P2)
   - Parked → 3 or 4 (P3-P4)

Example update:
```yaml
id: aops-1b00029b
title: Framework Session & Insights
type: goal
priority: 1  # P1 - Active this quarter
```

### Step 3: Verify Routing

Check that `claim_next` respects the new priorities:

```bash
# Should return P0-P1 goals first
claim_next --show-priority
```

### Step 4: Schedule Quarterly Refresh

At end of quarter, create reminder task:

```
Task: Review Q1-2026 Focus & Create Q2-2026 Focus
When: End of Q1 (approximately 2026-03-31)
Action: Update planning/Q2-2026-focus.md with new priorities
```

## Template: Quarterly Focus Document

```markdown
---
title: Q[N] [YEAR] Goal Focus
quarter: [YEAR]-Q[N]
created: [DATE]
last_reviewed: [DATE]
---

# Q[N] [YEAR] Goal Sequence

This document makes the quarterly strategy executable. Goals listed here should have their priorities set accordingly in the task system.

## Active (P0-P1) — Gets Energy This Quarter

| Goal | ID | Priority | Rationale |
|------|-----|----------|-----------|
| [Goal Name] | `goal-id` | P0 | [Why this quarter] |

## Maintenance (P2) — Time-Boxed Only

| Goal | ID | Priority | Rationale |
|------|-----|----------|-----------|
| [Goal Name] | `goal-id` | P2 | [When to engage] |

## Parked (P3-P4) — Not Until Q[N+1]+

| Goal | ID | Priority | Rationale |
|------|-----|----------|-----------|
| [Goal Name] | `goal-id` | P3 | [Reason for deferral] |

---

## How This Works

1. **Priority = Execution Order**: `claim_next` respects priority. P0 tasks get claimed before P1, etc.
2. **Update Goal Priorities**: Set priority field in goal files to match categories above.
3. **Review Cadence**: Check alignment weekly. Refresh quarterly.

---

## Review Log

| Date | Changes |
|------|---------|
| [DATE] | [What changed] |
```

## Monitoring & Refinement

### Weekly Check

Verify priorities still reflect where energy should go:

1. Review active goal progress
2. Check if maintenance goals need escalation
3. Adjust any goal priorities if strategic focus shifts

### Quarterly Refresh

At end of each quarter:

1. Archive current focus document (rename to include review date)
2. Create new quarterly focus document with updated priorities
3. Publish refresh as task for visibility
4. Review what worked in priority enforcement

## Integration with Other Systems

### Task Routing (`claim_next`)

- Already respects `priority` field
- P0 tasks claimed before P1, etc.
- No changes needed; priority enforcement is automatic

### Goal Evolution

- Quarterly Focus documents are living artifacts
- Can update mid-quarter if strategic priorities shift
- Document changes in Review Log

## Examples

See `/home/nic/writing/aops/planning/Q1-2026-focus.md` for the current implementation.

## References

- Identified in `effectual-planner` analysis (2026-01-24)
- Complements existing priority system
- Enables bottoms-up task execution of top-down strategy

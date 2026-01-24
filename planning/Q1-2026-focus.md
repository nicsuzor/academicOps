---
title: Q1 2026 Goal Focus
quarter: 2026-Q1
created: 2026-01-24
last_reviewed: 2026-01-24
---

# Q1 2026 Goal Sequence

This document makes the quarterly strategy executable. Goals listed here should have their priorities set accordingly in the task system.

## Active (P0-P1) — Gets Energy This Quarter

These goals receive focused attention. Bots pull from these first.

| Goal | ID | Priority | Rationale |
|------|-----|----------|-----------|
| **Urgent/Overdue** | `personal-52c30f58` | P0 | Time-sensitive items always first |
| **Buttermilk Pipeline** | `buttermilk-06e875ac` | P0 | Unblock Joel's PhD work, critical bugs |
| **OSB Operations** | `osb-edcb04e8` | P1 | Operational commitments, voting deadlines |
| **Framework Session & Insights** | `aops-1b00029b` | P1 | Core infrastructure for bot effectiveness |
| **Tasks MCP Improvements** | `aops-2475e6ba` | P1 | Enables better task routing |

### Active Epics (P0-P1)
- `buttermilk-5654bcef` — Pipeline Core Fixes (P0)
- `buttermilk-b3725ef2` — TMDB & Joel PhD Work (P0)
- `aops-5c2d6fce` — Bug Fixes (P1)
- `academic-40622a20` — Research Papers (P1)

## Maintenance (P2) — Time-Boxed Only

These goals get attention only when specific tasks surface. Don't proactively work on them.

| Goal | ID | Priority | Rationale |
|------|-----|----------|-----------|
| **Admin & RSVPs** | `personal-dfe023ec` | P2 | React to invitations, don't seek work |
| **Framework Agent Development** | `aops-4ccc6aa6` | P2 | Nice-to-have, not blocking |
| **Framework Verification Tests** | `aops-f5227611` | P2 | Run when triggered, don't prioritize |
| **Framework Audits** | `aops-fe62b3c9` | P2 | Periodic review, not urgent |

### Maintenance Epics (P2)
- `academic-48e8b5b2` — PhD Supervision Inquiries
- `academic-0869f984` — Collaborations & Partnerships
- `academic-730fe0c0` — External Reviews
- `aops-7ab46783` — Pipeline Infrastructure
- `aops-b2b8d34c` — Spec & Documentation
- Most Buttermilk epics except Core Fixes and TMDB

## Parked (P3-P4) — Not Until Q2+

These goals are explicitly deprioritized. Bots should not pull from them unless all P0-P2 work is exhausted.

| Goal | ID | Priority | Rationale |
|------|-----|----------|-----------|
| *(Add parked goals here)* | | P3-P4 | |

### Parked Epics (P3)
- `aops-3c1d4c33` — Learnings Review (68 children, defer bulk processing)

---

## How This Works

1. **Priority = Execution Order**: `claim_next` respects priority. P0 tasks get claimed before P1, P1 before P2, etc.

2. **Update Goal Priorities**: After updating this document, run a task to sync goal priorities:
   - Active goals → P0-P1
   - Maintenance goals → P2
   - Parked goals → P3-P4

3. **Weekly Review**: Check if priorities still reflect where energy should go.

4. **Quarterly Refresh**: At end of quarter, create new focus document (Q2-2026-focus.md).

---

## Review Log

| Date | Changes |
|------|---------|
| 2026-01-24 | Initial creation from effectual-planner session |

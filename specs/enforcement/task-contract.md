---
id: enforcement-task-contract
title: In-Session Enforcement — The Work-Unit Contract (Layer 2)
type: spec
status: draft
tags: [enforcement, framework-architecture, verification]
---

# In-Session Enforcement — The Work-Unit Contract (Layer 2)

> **Numbering note.** `Layer 2` here belongs to the **module-boundary layer model** (`Layer 0`–`Layer 4`, spanning [pyramid.md](pyramid.md), this file, [workflow.md](workflow.md), [sign-off.md](sign-off.md)) — an axis orthogonal to [`enforcement.md`](enforcement.md)'s pipeline (`L0`–`L11`) and pyramid-position (`L0`–`L7`) numbers. They reuse the same digits for a different purpose; see [enforcement.md § Two views of the same mechanisms](enforcement.md#two-views-of-the-same-mechanisms) for the distinction.

## aops-pkb — Work-unit loop (the task contract)

Operative from PKB `claim_task` → `release_task`. That pair is the contract for a
single agent session's single unit of work: one claimed unit, released under
contract.

**aops-pkb is the sole owner of the verification invariant.** The `release_task` /
`complete_task` call is the authoritative completion claim — the task graph is the
single source of truth, and a prose "done" that never moves task state is cheap
talk. Enforcement binds to the claim act, not to the session, so it holds
regardless of session class.

**Completion is not a claim — it is a claim carrying verification.** The release
must carry independent-verification evidence bound to the artifact state of the
work.

### Mechanisms

- **Premise gate** — at `claim_task`; refuses a task with no genuine premise
  assessment before compute is spent.
- **Freshness gate** — at `claim_task`; path-resolution and supersession checks.
- **Task-binding gate** — reactivated (H4): no mutating work without a task
  bound to the session via `claim_task`. The invariant is **one session claims
  exactly one task** (possibly multiple subtasks of it) — never
  `$AOPS_TASK_ID`, which never worked and is not to be built on (H10 rider).
  Wiring is target-state, lands with the mechanics-separation task
  (aops-5b9e95c4).
- **Evidence contract** — at `release_task` / `complete_task`; the completion
  claim must carry independent-verification evidence bound to artifact state,
  or a stated failure reason. **This is the primary enforcement point** (H7).
  Framed to agents as "land the plane" — commit → push → `release_task`, or
  the work is garbage-collected (H10): incentive-first, this machinery is the
  backstop, not the mechanism agents are expected to lean on. Its floor is the
  `mem` MCP server predicate — the contract is only as strong as that floor.

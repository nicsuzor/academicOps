---
id: enforcement-task-contract
title: In-Session Enforcement — The Work-Unit Contract (Layer 2)
type: spec
status: draft
tags: [enforcement, framework-architecture, verification]
---

# In-Session Enforcement — The Work-Unit Contract (Layer 2)

> **Numbering note.** `Layer 2` here belongs to the **module-boundary layer model** (`Layer 0`–`Layer 4`: the trust-the-method intra-task/turn span, this file, [workflow.md](workflow.md), [sign-off.md](sign-off.md)) — a different axis from any pipeline/pyramid numbering that may appear elsewhere.

## aops — Work-unit loop (the task contract)

Operative from PKB `claim_task` → `release_task`. That pair is the contract for a
single agent session's single unit of work: one claimed unit, released under
contract.

**aops is the sole owner of the verification invariant.** The `release_task` /
`complete_task` call is the authoritative completion claim — the task graph is the
single source of truth, and a prose "done" that never moves task state is cheap
talk. Enforcement binds to the claim act, not to the session, so it holds
regardless of session class.

**Completion is not a claim — it is a claim carrying verification.** The release
must carry independent-verification evidence bound to the artifact state of the
work.

### Mechanisms

- **Premise judgment** — no longer a standalone gate at `claim_task`. The
  premise/worth/shape assessment happens earlier, at decomposition time,
  inside the `decompose` skill (pauli's lens) — see
  [enforcement.md § Task-boundary review](enforcement.md#5-task-boundary-review--three-lenses-reviewer--executor).
  Dispatch surfaces (`/pull`, `/dispatch`) trust that decomposition rather than
  re-judging the premise themselves.
- **Task-binding invariant** — no mutating work without a task bound to the
  session via `claim_task`. The invariant is **one session claims exactly one
  task** (possibly multiple subtasks of it) — never `$AOPS_TASK_ID`, which
  never worked and is not to be built on. This is a design invariant the
  framework holds agents to by convention and review, not a code-level
  blocking check today.
- **Evidence contract** — at `release_task` / `complete_task`; the completion
  claim must carry independent-verification evidence bound to artifact state,
  or a stated failure reason. **This is the primary enforcement point** (H7).
  Framed to agents as "land the plane" — commit → push → `release_task`, or
  the work is garbage-collected (H10): incentive-first, this machinery is the
  backstop, not the mechanism agents are expected to lean on. Its floor is the
  `mem` MCP server predicate — the contract is only as strong as that floor.
  This is Layer 2's instantiation of the universal task-boundary contract —
  the field-by-field shape, the substance-over-form review requirement, and
  the grandfather cutover policy live once, canonically, in
  [evidence-contract.md](evidence-contract.md); this bullet does not restate
  them.

---
id: enforcement-task-contract
title: In-Session Enforcement — The Work-Unit Contract (Layer 2)
type: spec
status: draft
tags: [enforcement, framework-architecture, verification]
---

# In-Session Enforcement — The Work-Unit Contract (Layer 2)

> **Numbering note.** `Layer 2` here belongs to the **module-boundary layer model** (`Layer 0`–`Layer 4`: the trust-the-method intra-task/turn span, this file, [workflow.md](workflow.md), [sign-off.md](sign-off.md)). It is distinct from the retired repo-level L0–L7 numbering (which [`specs/ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md) replaced with a named mechanism index).

## aops — Work-unit loop (the task contract)

Operative from PKB `claim_task` → `release_task`. That pair is the contract for a
single agent session's single unit of work: one claimed unit, released under
contract.

**The unified worker contract (this is its canonical home; other docs link
here).** Any FULLY-SPEC'D task — including a task with children; an "epic" is
just a task with children, no special machinery — can be claimed by any worker
on any surface (polecat container, in-session subagent, agent team). Workers
use every harness feature they have; with that comes the obligation to
demonstrate compliance and QA internally (e.g. via separate subagents — how is
the worker's business). The return contract: **evidence + an output URL,
written to the PKB task record**. ONE deliverable per claimed task — never a
spray of per-child PRs the principal reviews individually. Task scope = one
project/repo. Sync-wait vs fire-and-forget is a dispatch-time cadence choice,
not a contract difference. This makes explicit what the task-binding
invariant below already permits — "one session claims exactly one task
(possibly multiple subtasks of it)" covers claiming a task with children.

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
  assessment happens earlier, in pauli's `brief` skill: it places and values the
  work, sorts its assumptions, names its open forks, then settles shape and
  acceptance criteria. Dispatch surfaces (`/pull`) trust that rather
  than re-judging the premise themselves.
- **Task-binding invariant** — no mutating work without a task bound to the
  session via `claim_task`. The invariant is **one session claims exactly one
  task** (possibly multiple subtasks of it) — never `$AOPS_TASK_ID`, which
  never worked and is not to be built on. This is a design invariant the
  framework holds agents to by convention and review, not a code-level
  blocking check today.
- **Claim at launch** — a dispatch whose loss would matter beyond its own
  session has its claim written to the graph _before_ the worker starts: who it
  went to, under which session and surface, and when. The worker's own
  `claim_task` still happens from inside its session and is what moves the
  status; the launch-time record exists so that a worker which died before ever
  claiming is legible as an unanswered dispatch rather than as work nobody
  picked up. **Cheap read-only probes are exempt** — nothing is lost by running
  one again, so claiming for them buys graph noise instead of recoverability. A
  launch-time claim with no worker claim behind it is precisely the stale-claim
  signal a reconcile sweep probes and, finding nothing, requeues to `ready`.
- **Task naming invariant** — task titles must be brief, descriptive, verb-led statements of a concrete thing to achieve (e.g. `Implement X`, `Verify Y`). A task title or filename never carries a person's name or persona prefix; assignment belongs exclusively in `assigned_to` / `assignee` frontmatter fields. See [`specs/meta/naming-and-decisions.md`](../meta/naming-and-decisions.md).
- **Decisions as graph relationships** — decisions and questions must never be created as standalone "decision" tasks. Open architectural choices are represented as mutually exclusive or mutually blocking option nodes where choosing one branch resolves the conflict, and missing information is modelled as a probe task (`classification: spike`). In-turn questions are put directly via `AskUserQuestion`.
- **Task body brevity invariant** — task bodies are strictly concise (50–150 words for atomic tasks), structured only around Goal, Deliverable, Scope, Acceptance criteria, and Pointers. Extraneous narrative sections (`Background`, `References`, `Implementation Plan`) and prose task links are prohibited.
- **Graph edge economy invariant** — setting `parent_id` is already an intrinsic graph edge; redundant wiring between descendants/siblings under the same parent without specific interactions is prohibited.
- **Evidence contract** — at `release_task` / `complete_task`; the completion
  claim must carry independent-verification evidence bound to artifact state,
  or a stated failure reason. **This is the primary enforcement point.**
  Framed to agents as "land the plane" — commit → push → `release_task` with
  either a completion claim or a `partial` handback per
  [spec-partial-work-tight-loop-delivery.md](../polecat/spec-partial-work-tight-loop-delivery.md#the-partial-terminal-state)
  (the existing terminal status in the canonical taxonomy — a partial handback
  is a legal terminal outcome, not a failure; that spec owns partial
  semantics, which this bullet does not restate). Only silent, undisclosed
  abandonment is garbage-collected (H10): incentive-first, this machinery is the
  backstop, not the mechanism agents are expected to lean on. Its floor is the
  `mem` MCP server predicate — the contract is only as strong as that floor.
  This is Layer 2's instantiation of the universal task-boundary contract —
  the field-by-field shape, the substance-over-form review requirement, and
  the grandfather cutover policy live once, canonically, in
  [evidence-contract.md](evidence-contract.md); this bullet does not restate
  them.

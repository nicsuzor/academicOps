---
alias:
- spec-7715b135-capture-execute-review-pipeline-consolidation-roadmap
- spec-7715b135
created: 2026-05-04T23:41:10.513882552+00:00
id: spec-7715b135
modified: 2026-05-04T23:48:34.019190292+00:00
parent: task-43414eab
permalink: spec-7715b135
tags:
- framework
- roadmap
- pipeline
- review-lens
- sleep
- planner
- supervisor
- consolidation
title: 'Capture-execute-review pipeline: consolidation roadmap'
type: spec
---

# Capture → Execute → Review: pipeline consolidation roadmap

**Status**: roadmap (not implementation spec). Names the single pipeline, maps existing tasks/specs/epics to its stages, and identifies overlaps that must merge before parallel infrastructure accumulates.

**Parent**: [[task-43414eab|Ship the end-to-end capture-execute-review pipeline]] — this roadmap _is_ the architectural skeleton for that epic.

**Companion specs**: [[spec-64352eac-planner-pre-dispatch-decomposition-gate]] (planner gate), [[supervisor]] (pre-flight gate), `aops-core/skills/sleep/SKILL.md` (sleep skill), [[feedback-loops]] (/learn loop), [[vision]] (constraints).

---

## 1. The pipeline (one diagram, one vocabulary)

```
(user, /q, /capture, email, friction)
               │
               ▼
         ┌───────────┐
         │  CAPTURE  │  status: inbox
         └─────┬─────┘
               │
 ╔═════════════▼═════════════╗
 ║  GATE 1 — PLANNER         ║  spec-64352eac
 ║  inbox → ready            ║
 ║  outputs: subtasks, AC,   ║
 ║  verification subtask,    ║
 ║  rbg+pauli lens tasks,    ║
 ║  named file/symbol        ║
 ╚═════════════╤═════════════╝
               │
               ▼
         ┌───────────┐
         │  READY    │  human-pull
         └─────┬─────┘
               │  user gates ready → queued
               ▼
 ╔═════════════▼═════════════╗
 ║  GATE 2 — SUPERVISOR      ║  task-4cea5008 / aops-e2d639e2
 ║  queued → in_progress     ║
 ║  verifies: repo, file/    ║
 ║  symbol exists, branch,   ║
 ║  PKB-leak halt rule       ║
 ╚═════════════╤═════════════╝
               │
               ▼
         ┌───────────┐
         │  EXECUTE  │  worker (claude-code, polecat, gha)
         └─────┬─────┘
               │
               ▼
         ┌───────────┐
         │  REVIEW   │  composable lenses, post-hoc
         │  (lenses) │  rbg | pauli | marsha | james
         └─────┬─────┘  signals, NOT gates
               │
               ▼  human merge decision (the gate)
         ┌───────────┐
         │ MERGED PR │
         └─────┬─────┘
               │
 ╔═════════════▼═════════════╗
 ║  CONSOLIDATE — /sleep     ║  sleep skill (existing)
 ║  Phases 0–11 (existing)   ║
 ║  + planner-gate audit     ║
 ║  + lens-task resolution   ║
 ║    audit                  ║
 ╚═════════════╤═════════════╝
               │
 ╔═════════════▼═════════════╗
 ║  LEARN — /learn           ║  friction → rubric updates
 ║  feeds gate-1 + gate-2    ║
 ║  templates and lens       ║
 ║  rubrics                  ║
 ╚═══════════════════════════╝
```

### Vocabulary lock-in

- **Three gates**, three labels: **planner gate** (inbox→ready), **user-promote** (ready→queued, human only), **supervisor gate** (queued→in_progress).
- **Lenses are signals, not gates** — `rbg`, `pauli`, `marsha`, `james` run as composable post-hoc tasks. The merge gate is human (per [[vision]]).
- **/sleep is the consolidation pass** — periodic, offline. Surfaces drift. Does NOT introduce new gates.
- **/learn is the rubric loop** — friction noticed during execute or review feeds back into planner-gate templates and supervisor-gate checks.

---

## 2. Consolidation map

Every existing task, spec, or epic, mapped to one stage. Action: **keep**, **merge into X**, or **re-parent under Y**.

| ID                      | Title                                               | Stage                   | Action                                                                                          |
| ----------------------- | --------------------------------------------------- | ----------------------- | ----------------------------------------------------------------------------------------------- |
| `task-43414eab`         | Ship the end-to-end capture-execute-review pipeline | (umbrella)              | **keep** — this roadmap is its skeleton                                                         |
| `task-98551f8e`         | Design the capture-to-execution pipeline            | CAPTURE → GATE 1        | **merge into** this roadmap; close on review                                                    |
| `task-4e213bd1`         | Trustworthy end-to-end automation                   | (umbrella)              | **merge into** `task-43414eab` — duplicate framing                                              |
| `aops-cfc62d72`         | Planner-side pre-dispatch discipline (epic)         | GATE 1                  | **keep**                                                                                        |
| `spec-64352eac`         | Planner pre-dispatch decomposition gate (spec)      | GATE 1                  | **keep**                                                                                        |
| `aops-5707eb51`         | Implement planner pre-dispatch gate                 | GATE 1                  | **keep** (inbox until promoted)                                                                 |
| `task-4cea5008`         | Supervisor pre-flight spec                          | GATE 2                  | **keep** (done)                                                                                 |
| `aops-e2d639e2`         | Wire supervisor pre-flight gate                     | GATE 2                  | **keep**; ensure parent path reaches `task-43414eab`                                            |
| `task-64d65a24`         | Anonymisation enforcement                           | GATE 2 (PKB-leak halt)  | **keep**; wire as `depends_on` for `aops-e2d639e2`                                              |
| `epic-9fa15948`         | Stop-hook RBG validation                            | EXECUTE (response-time) | **keep** — different scope                                                                      |
| `task-50c6f767`         | Polecat fleet                                       | EXECUTE (substrate)     | **keep** — peer epic, not pipeline child                                                        |
| `aops-229d1952`         | Friction-log review rubric (overnight drainer)      | REVIEW + LEARN          | **re-parent under** `aops-cfc62d72` (or new REVIEW epic). Currently under polecat, wrong stage. |
| `aops-93bf151a`         | TDD bug-fix workflow                                | EXECUTE (discipline)    | **keep** under `task-43414eab`                                                                  |
| `task-168a84c9`         | Structured session handover                         | CONSOLIDATE boundary    | **keep**; T9/T10 are session→/sleep handoff                                                     |
| `epic-closing-d2ba6bb6` | Close the loop on task lifecycle                    | CONSOLIDATE             | **keep** as spec-holder; close parallel scheduler children                                      |
| `task-6334fd37`         | Close-the-loop scheduler                            | CONSOLIDATE             | **merge into** /sleep cycle (per `task-cc6a4714`)                                               |
| `task-cc6a4714`         | Move polecat sweep into /sleep                      | CONSOLIDATE             | **keep** — canonical "sleep is the close-the-loop" task                                         |
| `task-4d644e65`         | Shared PR-state surface                             | CONSOLIDATE → DASHBOARD | **keep** — feeds /sleep + dashboard                                                             |
| `task-387ab277`         | Agentic review pipeline                             | REVIEW (lens machinery) | **keep** under `task-43414eab`                                                                  |
| `task-4e181b75`         | review-pr classifier fixes                          | REVIEW                  | **keep**                                                                                        |
| `academicops-f702404d`  | Build PR review pipeline                            | REVIEW                  | check duplicate of `task-387ab277`; **merge** if so                                             |
| `task-670fe624`         | Improve QA forensic pipeline                        | REVIEW                  | **keep**                                                                                        |
| `aops-6e05d69a`         | Spec: sleep cycle consolidation agent               | CONSOLIDATE             | **keep** (spec)                                                                                 |
| `aops-6eb7a0b2`         | Implement sleep cycle skill                         | CONSOLIDATE             | **keep** (history)                                                                              |
| `task-34f5d4f0`         | Sleep skill spec graph maintenance                  | CONSOLIDATE Phase 9     | **keep** (done)                                                                                 |
| `epic-553da253`         | /sleep loop pacing fix                              | CONSOLIDATE pacing      | **keep**                                                                                        |
| `aops-df964399`         | Active-loop protocol skill                          | CONSOLIDATE meta        | **keep**                                                                                        |
| `task-2e8b1498`         | Knowledge-note frontmatter required fields          | data quality            | **keep** under PKB-write epic; /sleep Phase 6 depends on it                                     |

### Overlaps to _merge_

1. **`task-6334fd37` (close-the-loop scheduler) → /sleep**. Already noted in `task-cc6a4714`. Don't build a parallel scheduler.
2. **`task-98551f8e` (design capture→execution pipeline) → this roadmap**. This roadmap fulfils it.
3. **`task-4e213bd1` (trustworthy end-to-end) → `task-43414eab`**. Same epic, different words.
4. **`aops-229d1952` parent**. Re-parent from polecat to `aops-cfc62d72` or new REVIEW epic.

### Overlaps that must _stay separate_

- **Gate 1 ≠ Gate 2 ≠ Stop-hook RBG** — three different points in the lifecycle. Sibling, not nested. (Documented in spec-64352eac §"Sibling gates".)
- **/sleep ≠ /learn**. /sleep consolidates state; /learn captures friction. They feed each other but are not the same loop.
- **Anonymisation (`task-64d65a24`)** is a check _inside_ gate 2, not its own stage. Wire as `depends_on` for `aops-e2d639e2`.

---

## 3. The single parent

`task-43414eab` (**Ship the end-to-end capture-execute-review pipeline**) is the parent epic. This roadmap hangs directly under it. All gate/lens/consolidate sub-epics hang there:

- `aops-cfc62d72` — planner gate (✓)
- `aops-e2d639e2` — supervisor gate (verify dual-parent reaches `task-43414eab`)
- `task-387ab277` — review-lens machinery (✓)
- `epic-closing-d2ba6bb6` — close-the-loop / consolidation (✓)
- `aops-93bf151a` — TDD discipline (✓)

Polecat fleet (`task-50c6f767`) is a **peer epic** — provides the EXECUTE substrate.

---

## 4. What changes in /sleep to honour this roadmap

/sleep already does most of what "close the loop" needs (Phases 0, 1, 6, 7, 9, 11). The pipeline framing adds **two explicit checks** to existing phases — not new phases:

- **Phase 6 (Data Quality)** — for each completed task in the cycle window, verify the planner-gate verification subtask was actually run and resolved. If absent, surface for review (don't auto-fail).
- **Phase 7 (Staleness)** — for each ready/queued task older than N days, verify gate-1 outputs are still present (AC, named file/symbol). If artifacts have rotted (file deleted, symbol renamed), demote to inbox with annotation — don't silently leave it ready.

Both are surface-don't-decide consistent with /sleep's existing principles. No new phase, status, or tool.

---

## 5. Deliberate non-additions

- No new skill (no `/close-the-loop`, no `/pipeline`).
- No new status field.
- No new MCP tool.
- No new hook.
- No auto-merge state machine (rejected per [[vision]]).
- No "verification daemon" or "rubric service" — /sleep is the daemon; /learn is the rubric source.

---

## 6. Open questions

1. Is `aops-229d1952` properly placed under polecat, or under REVIEW lenses? (Recommendation: re-parent.)
2. Is `aops-e2d639e2` reachable from `task-43414eab` via parent chain? (Action: verify and add edge if not.)
3. Does `epic-closing-d2ba6bb6` collapse entirely into /sleep, or retain spec-holder identity? (Recommendation: retain; close the parallel scheduler children.)

---

## 7. Acceptance

- [ ] James review verdict captured (memory or appended below)
- [ ] `aops-229d1952` re-parented if approved
- [ ] `aops-e2d639e2` confirmed reachable from `task-43414eab`
- [ ] `task-6334fd37` annotated as subsumed by `task-cc6a4714` / /sleep
- [ ] `task-98551f8e` and `task-4e213bd1` annotated as superseded
- [ ] `aops-state` change-log entry recorded

---

## References

- [[vision]] — composable lenses; merge gate is human; anti-bloat
- [[spec-64352eac-planner-pre-dispatch-decomposition-gate]] — planner gate spec
- [[supervisor]] — supervisor architecture
- [[feedback-loops]] — /learn loop
- [[task-43414eab]] — parent epic
  **2026-05-04 23:48 UTC** — ## James review verdict (2026-05-05)

**Verdict**: REVISE → resolved.

Three voices summary:

- **Ruth (rbg)**: PASS with WARN on lens-stage labelling — the diagram conflates plan-time RBG/Pauli lens tasks (gate 1) with post-execute lens tasks (REVIEW). Two phases, distinct functions.
- **Pauli**: REVISE — §4 /sleep loop-close is too thin; capture-side hygiene silently dropped; fast-path / proportional gate not acknowledged.
- **Marsha**: REVISE — vocabulary lock-in (§1) and /sleep changes (§4) not captured as tasks; without tasks they are decoration.

### Actions taken (2026-05-05)

- `aops-229d1952` re-parented from `task-50c6f767` (polecat) to `aops-cfc62d72` (planner gate epic).
- `aops-e2d639e2` re-parented from `task-4cea5008` to `task-43414eab` directly (parent chain through `task-4cea5008` did NOT reach `task-43414eab` — was wrong).
- `aops-500e92a8` filed: Capture-side dispatch hygiene (carries the work `task-98551f8e` was holding).
- `aops-2959d5ac` filed: Update /sleep SKILL.md Phases 6 + 7 (gate-1 verification audit + artifact-rot check).
- `aops-4690f5ec` filed: Pipeline vocabulary alignment (planner / supervisor / sleep / agents).
- `task-98551f8e` annotated: superseded.
- `task-4e213bd1` annotated: superseded.
- `task-6334fd37` annotated: subsumed by `task-cc6a4714` + /sleep.

### Outstanding (deferred, not blocking)

- §1 diagram should show RBG/Pauli at _both_ GATE 1 and REVIEW (two phases). Diagram update is cosmetic; semantic content is correct in the spec body. Defer to first revision pass.
- §1.5 (fast path / proportional gate) — covered by reference to spec-64352eac, but should be cited explicitly.

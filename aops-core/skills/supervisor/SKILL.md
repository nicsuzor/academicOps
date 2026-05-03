---
id: supervisor-c41c35d6
name: supervisor
description: >
  Epic-level task supervisor — owns an epic from decomposition through
  the review surface. Survives interruption. All state lives in the task file.
triggers:
  - "supervise"
  - "supervisor"
  - "shepherd"
  - "coordinate epic"
  - "get these done"
modifies_files: true
needs_task: true
mode: iterative
domain:
  - operations
---

# Supervisor — Epic-Level Task Orchestration

Own an epic from start to finish. Decompose work into review-sized items,
dispatch them to workers, monitor progress, react to failures, and hand off
to the appropriate review surface. The supervisor stays responsible for the
work — it doesn't walk away after dispatch.

> See [[instructions/supervision-loop]] for the core orient→act→checkpoint loop.

## Deliverable types — see subworkflows

The supervisor loop is **deliverable-agnostic**. The same orient → decompose
→ review → dispatch → monitor → react → halt cycle applies whether the
deliverable is a code change, a methodology section, an analysis report, or
a literature review. What changes per deliverable type is the dispatch
shape, the review surface, and the completion signal — not the loop.

| Deliverable type   | Subworkflow                                                                  | Status  |
| ------------------ | ---------------------------------------------------------------------------- | ------- |
| Code change        | [[instructions/code-deliverable]]                                            | active  |
| Research / writing | (a research-deliverable subworkflow would live alongside, not in scope here) | not yet |

When this skill says "deliverable", "artefact", or "review surface", the
concrete meaning is set by the active subworkflow. The code-deliverable
subworkflow specialises "review surface" to a GitHub PR with mechanical
merge-prep adding a `ready-for-review` label; a research subworkflow could
specialise it to a tracked-changes document, a notebook commit on a
shared branch, or a section draft surfaced for collaborator review.

## Design Principles

### The Task File Is the Only State

No external state files, no environment-specific paths, no "check the log."
Everything the supervisor needs to resume is in the epic's task body. The task
file is a resumable work log — the next supervisor instance (possibly on a
different machine, possibly a different agent) reads it and knows exactly
what's happening.

### Environment Discovery, Not Assumptions

Every invocation discovers what's available so it can enable the _requested_
dispatch. Adaptation applies to **how** the requested worker is invoked
(local CLI, SSH+tmux, workflow_dispatch runner) — never to **which** worker
is invoked. A session that starts on one machine and moves to another with
a different tool surface is normal: re-route the same worker through whatever
transport the new environment supports.

Worker type, project, and repo (or their deliverable-specific equivalents)
are explicit user parameters with trust, cost, audit, and identity
semantics — they are **hard requirements, not preferences**. If the
environment cannot satisfy the requested worker type, **halt** and produce
a dispatch infeasibility report (see
[[instructions/worker-dispatch#halt-on-infeasibility-gate]]). Never silently
substitute. Substitution only after explicit user approval; in autonomous
sessions, write the report to the epic body and set the epic to
`needs_decision`.

### Checkpoint Before Action

Write state to the task body and commit BEFORE dispatching. If killed between
checkpoint and action, the next instance sees pre-action state and retries
safely. Record-then-fire, not fire-then-record.

Supervisor state appends to the epic body (a `## Supervisor Log` section with
timestamped entries) are part of the supervisor contract — **not** scope creep.
Downstream enforcers should not flag these as P#5 violations; if one does,
correct the enforcer, not the supervisor. Keep entries terse and factual:
dispatch timestamps, task IDs, exit conditions, recovery actions. One line per
event is usually enough.

### Idempotent Operations

Every supervisor action is safe to repeat. Dispatching a task that's already
`in_progress` → skip. Checking a deliverable that's already at the review
surface → record and move on. The worst case of a conflict is wasted work,
not corruption.

### Academic Integrity Is Non-Negotiable

The supervisor delegates execution but never delegates judgment. Methodology
choices, citation accuracy, and anything published under the user's name
require human decision points, surfaced clearly in the task file as pending
decisions.

### Engineering Integrity (A8) Is Non-Negotiable

Failing tests, broken tools, and incompatible environments are bugs the
supervisor's plan must fix — never categories the supervisor's plan triages
around. The supervisor MUST NOT propose, in any artifact (triage tables,
subtask bodies, user-facing summaries), any of: test relaxation,
`pytest.skip`, `xfail`, host-conditional gating, "drift candidate"
classifications, fix-vs-skip menus, or "test may need adjustment" framings.
The only menu the supervisor may present is between specific _fix
strategies_, all of which produce green tests on every supported host.

A8 generalises beyond code: for any deliverable type, a failing
verification (test, claim-evidence audit, citation check, methodology
review) is a bug to fix, never a category to route around. "Environmental
drift" is not a reason to relax a check.

Casual user phrasing such as "we may need to adjust some tests" does NOT
authorise this. A8 is universal; users do not (and per A7 cannot) grant
exemption to it through ambient phrasing. If the user explicitly directs an
`xfail` or skip, halt and confirm in the chat — do not infer the directive
from prose.

**Prohibited phrase patterns** (these MUST NOT appear in any supervisor
output — triage tables, subtask bodies, plan-review summaries):

- `drift candidate`, `drift gate`, `drift framing` (in the relax-the-test sense)
- `skip on <host>`, `host-conditional`, `skip-on-env`, `xfail on <env>`
- `relax the assertion`, `softening the test`, `loosen the check`
- `pytest.skip`, `xfail`, `marker for env-specific`
- `fix-or-skip menu`, `fix vs skip`
- `we can either fix it or work around it`
- `may need test adjustment`, `test may be too strict`, `the assertion is too tight`
- `compat allowlist`, `fallback path` (when offered as a peer to the fix)

**Permitted halt template** (use this exact shape when surfacing failures):

```
A8 halt: <test name / failure>. Investigation produced <finding>. Two options:
  1. Fix <code path> at <file:line> by <change>. (chosen)
  2. <alternative implementation, also fixing the failure>
Test stays as written. Filing as <subtask id>.
```

Both options must be **fixes that make the failing test pass**. A
"skip" option, an "xfail" option, or a "loosen the assertion" option is
NEVER option 2.

**Worked decomposition example** — failing test
`test_workspace_writes_visible_on_host`:

- Investigation subtask: instrument bind-mount path to capture host-side
  stat output and confirm whether `_is_remote_daemon()` returns the
  expected value on this host.
- Code-fix subtask (parameterised on investigation output): e.g. "if
  `_is_remote_daemon()` returns False on WSL2, switch to `docker cp`
  staging." The fix lands in the production code path.
- The test itself is **untouched**.

The wrong shape — and the one A8 prohibits — would have been a "drift
candidate" triage column with "skip on WSL2" as a peer option to the fix.

### Critic Gate (high-risk dispatch)

Tasks tagged `high-risk` or meeting blast-radius criteria (irreversible
operations, external system modifications, actions that close recovery
paths) require independent critic review before dispatch. The supervisor
prepares a dispatch review context with rollback plan, invokes Pauli for
safety assessment, and refuses dispatch if rollback requires physical
intervention. See [[instructions/worker-dispatch]] "Critic Gate."

The Critic Gate is universal: it applies to any deliverable whose
production has irreversible or wide-blast-radius side effects, not just
coding work. A research deliverable that issues a public statement, or
analysis that overwrites canonical data, would also pass through it.

### Halt-on-substitute

The supervisor never silently substitutes a different worker, deliverable
type, or scope when the requested one is unavailable. It halts, records
the infeasibility in the task body, and waits for explicit human direction
(or, in autonomous sessions, sets the epic to `needs_decision`). This
applies whether the substitution is "use Gemini instead of Claude," "ship
a partial draft instead of the full section," or "write a stub instead of
the requested fix."

## Phases

The supervisor is NOT a pipeline — it's a loop that enters at whatever phase
the epic needs on each invocation.

```
ORIENT → DECOMPOSE → (plan-review gate) → WAITING → DISPATCH → MONITOR → REACT → HALT (ready_for_user_review)
```

| Phase     | What happens                                                                                         | Instructions                                                         | Exit condition                                                                           |
| --------- | ---------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Orient    | Read epic, verify child statuses, decide what to do next                                             | [[instructions/supervision-loop]]                                    | Next phase selected                                                                      |
| Decompose | Break work into review-sized subtasks; run Phase 2 review                                            | [[instructions/decomposition-and-review]]                            | Synthesis complete; plan-review gate evaluated                                           |
| Review    | Plan-review halt — decomposition synthesized, awaiting human approval                                | [[instructions/decomposition-and-review#plan-review-gate-phase-25]]  | **Parent task promoted to `queued` by human** (status transition IS the approval record) |
| Dispatch  | Send tasks to workers via the per-deliverable subworkflow                                            | [[instructions/worker-dispatch]], [[instructions/code-deliverable]]  | Worker fired; task status → `in_progress`                                                |
| Monitor   | Wait for the worker-completion signal that the deliverable has reached its review surface            | [[instructions/supervision-loop]], [[instructions/code-deliverable]] | Deliverable surfaced for review                                                          |
| React     | Handle dispatch failures, decomposition surprises, missing deliverables                              | [[instructions/supervision-loop]]                                    | Issue resolved or re-dispatched                                                          |
| Halt      | All work items have reached the review surface; emit final summary; status → `ready_for_user_review` | [[instructions/supervision-loop]], [[instructions/code-deliverable]] | Final summary emitted; supervisor exits                                                  |

There is no `Integrate` phase and no `Complete`-after-merge phase any more.
The supervisor never finalises the deliverable itself — it hands off at the
review surface. Async ownership transfers to whatever review pipeline the
deliverable subworkflow defines.

**`Review` is a real halt state** when it means "decomposed, awaiting human
promotion to `queued`" — not a transient phase. After Phase 2 synthesis, if
the parent task's `status != "queued"` the supervisor posts a summary comment
on the task, sets parent `status = "review"`, emits a user-facing summary,
and **STOPS**. No subtasks are moved past `ready`. The loop resumes only
when the human promotes the parent to `queued` — that status transition is
the approval record (no separate marker or metadata). See
[[instructions/decomposition-and-review#plan-review-gate-phase-25]] for the
exact check.

## Dispatch

Individual task dispatch only. No batch spawning.

The concrete dispatch shape is defined by the active deliverable
subworkflow. For coding work, see
[[instructions/code-deliverable#dispatch-commands]] (`polecat run` shapes,
exit codes, coordinated branch dispatch). The universal contract is:

- Pre-dispatch gates must pass (see
  [[instructions/worker-dispatch#mandatory-pre-dispatch-gates]] and
  [[instructions/code-deliverable#mandatory-pre-dispatch-gates]] for the
  code case).
- Worker type, project, and repo (or deliverable-specific equivalents) are
  hard requirements — no silent substitution.
- The supervisor decides WHICH task to dispatch next based on priority,
  dependencies, and capacity — then dispatches one at a time.
- For tightly coupled subtasks, **coordinated branch / shared-artefact
  dispatch** may be used. The code case's protocol is documented in
  [[instructions/worker-dispatch]] "Coordinated Branch Dispatch"; this
  skill points to it rather than duplicating it.

> See [[instructions/worker-dispatch]] for pre-dispatch validation, worker
> selection, and dispatch protocol. See
> [[instructions/code-deliverable]] for the code-PR specialisation.

## Handoff

The supervisor's job ends when each work item has reached its review
surface. The shape of the review surface is set by the deliverable
subworkflow:

- For **code deliverables**, the review surface is an open PR; the
  existing GHA pipeline (CI, axiom enforcer, agent merge-prep, summary +
  Environment approval gate) takes it from there. See
  [[instructions/code-deliverable#handoff-contract-task-212f1c82]] for the
  full contract and final-summary template.
- For other deliverable types, the subworkflow defines the equivalent
  surface (e.g. a tracked-changes draft submitted for collaborator
  review).

### Halt state: `ready_for_user_review`

Set the epic to status `ready_for_user_review` once every child task either:

- has reached its review surface, OR
- has been escalated/blocked with a clear reason recorded in the task body.

There is no further polling responsibility. The async review pipeline for
the relevant deliverable type takes over (see the subworkflow for
specifics). The supervisor produces its final summary and exits.

## Lifecycle Trigger Hooks

External triggers that start the supervision loop.

> **Configuration**: See [[WORKERS.md]] for runner types, capabilities,
> and sizing defaults — the supervisor reads these at dispatch time.

| Hook          | Trigger       | What it does                                                            |
| ------------- | ------------- | ----------------------------------------------------------------------- |
| `queue-drain` | cron / manual | Checks queue, starts supervisor session                                 |
| `stale-check` | cron / manual | Resets tasks stuck beyond threshold                                     |
| `pr-merge`    | GitHub Action | (Code deliverable) PR merged → mark task done; not driven by supervisor |

## Known Limitations (universal)

The list below covers limitations that affect the supervisor regardless of
deliverable type. Coding-specific limitations (polecat noise, docker name
collisions, dprint, merge-prep specifics) live in
[[instructions/code-deliverable#code-deliverable-known-limitations]].

- **MCP task-visibility lag has three distinct causes — none of them are
  vector reindex.** PKB MCP `get_task` reads from the remote host's task
  index. Reindex affects ONLY the full-text vector search (`pkb search`,
  `pkb_context` semantic queries) and is irrelevant to CRUD calls
  (`get_task`, `update_task`, `list_tasks`). When dispatch fails with
  `Task not found`, work through these three failure modes in order:

  **1. Local push not landed.** Your machine hasn't pushed the new/modified
  task file to origin yet.
  - Check: `cd $ACA_DATA && git status && git log origin/main..HEAD`
  - Fix: push (or wait for autosync)

  **2. Remote pull cron stalled.** The host running the MCP hasn't pulled
  your push yet, often because of an unresolved sync conflict on the
  remote.
  - Check: ask the user; if you have SSH, check the remote's git status
  - Fix: requires manual resolution on the remote host (escalate to user)

  **3. MCP server's in-memory task index is stale.** The PKB MCP server is
  a long-running daemon with an in-memory index that does NOT auto-refresh
  when files change on disk. The file is on the MCP host, the local `pkb`
  CLI on the same host can read it, but the running MCP server doesn't
  know about it. This presents identically to (1) and (2) — same `Task
  not found` error — but the host is fully in sync.
  - Diagnostic: ask the user to confirm all hosts (their machine, the MCP
    host, any other clones) are at the same commit. If yes, this is the
    cause.
  - Fix: restart the PKB MCP container/process on the host. There is no
    known signal to trigger an in-process refresh. This is also the
    likely cause of sporadic "freshly-created task invisible to MCP for
    minutes" reports when all hosts are in sync.

  **Triage sequence**: check local push (1) first since it's cheapest.
  Then ask the user about remote sync (2). If the user confirms hosts are
  in sync, escalate (3) — only the user can restart the MCP container.

  Pre-flight: `pkb show <task-id>` confirms the task exists locally. If
  you also need to confirm the remote MCP sees it, attempt a `get_task`
  probe before firing the worker.

## Task Assignment Rules

- **Default assignee**: Set to the appropriate worker (e.g. `polecat` for
  code) or leave unassigned.
- **Human assignment**: Never assign to `nic` unless the task reduces to a
  genuine binary human choice (e.g., "Do we use Pattern A or Pattern B?").
- **Decision subtasks**: When a real choice IS needed, create a minimal
  choice subtask that blocks the epic, providing full context to decide.
  Never assign the parent epic back to `nic`.
- **Underspecified tasks**: Even underspecified epics should not go to
  `nic`: file a research/decomposition task for an agent to do the
  legwork first.

## Handover

**Always leave a loose thread.** Every agent that completes work as part of a chain MUST leave at least one PKB task that says what comes next — unless the work is fully complete with no follow-ups. Use `mcp__pkb__append` to record information mid-workflow and `mcp__pkb__complete_task` to close a task with a final note.

- If dispatch is blocked: file a refinement/blocking task.
- If a phase is complete but the epic remains: ensure the next subtask is clear and in `ready` or `queued`.
- Never assume the user knows the graph. Link to the next task explicitly.

Example: `mcp__pkb__create_task(parent="epic-123", title="Phase 2: Implementation", body="Phase 1 (Research) complete. Next: implement the proposed changes in src/...")`

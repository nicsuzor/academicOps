---
id: supervisor-c41c35d6
name: supervisor
description: >
  Epic-level task supervisor — owns an epic from decomposition through
  integration. Survives interruption. All state lives in the task file.
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

Own an epic from start to finish. Decompose, dispatch individual tasks via
`polecat run`, monitor progress, react to failures, ensure integration. The
supervisor stays responsible for the work — it doesn't walk away after dispatch.

> See [[instructions/supervision-loop]] for the core orient→act→checkpoint loop.

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
is invoked. A session that starts on a Mac with local polecat and moves to a
crew container with only Docker and gh is normal: re-route the same worker
through whatever transport the new environment supports.

Worker type, project, and repo are explicit user parameters with trust,
cost, audit, and identity semantics — they are **hard requirements, not
preferences**. If the environment cannot satisfy the requested worker type,
**halt** and produce a dispatch infeasibility report (see
[[instructions/worker-dispatch#halt-on-infeasibility-gate]]). Never
silently substitute. Substitution only after explicit user approval; in
autonomous sessions, write the report to the epic body and set the epic to
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
in_progress → skip. Checking a PR that's already merged → record and move on.
The worst case of a conflict is wasted work, not corruption.

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

"Environmental drift" is not a reason to relax a test. If the environment
changed, the code that interacts with that environment is what gets fixed.

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

Both options must be **fixes that make the failing test pass**. A "skip"
option, an "xfail" option, or a "loosen the assertion" option is NEVER
option 2.

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

## Phases

The supervisor is NOT a pipeline — it's a loop that enters at whatever phase
the epic needs on each invocation.

```
ORIENT → DECOMPOSE → (plan-review gate) → WAITING → DISPATCH → MONITOR → REACT → HALT (ready_for_user_review)
```

| Phase     | What happens                                                                         | Instructions                                                                                     | Exit condition                                                                           |
| --------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------- |
| Orient    | Read epic, verify child statuses, decide what to do next                             | [[instructions/supervision-loop]]                                                                | Next phase selected                                                                      |
| Decompose | Break work into PR-sized subtasks; run Phase 2 review                                | [[instructions/decomposition-and-review]]                                                        | Synthesis complete; plan-review gate evaluated                                           |
| Review    | Plan-review halt — decomposition synthesized, awaiting human approval                | [[instructions/decomposition-and-review#plan-review-gate-phase-25]]                              | **Parent task promoted to `queued` by human** (status transition IS the approval record) |
| Dispatch  | Send tasks to workers (local or remote via SSH+tmux)                                 | [[instructions/worker-dispatch]], [[instructions/worker-dispatch#remote-dispatch-via-ssh--tmux]] | Worker fired; task status → `in_progress`                                                |
| Monitor   | Wait for the worker-completion signal that a PR has been opened                      | [[instructions/supervision-loop]]                                                                | PR opened for the work item (label not required at this point)                           |
| React     | Handle dispatch failures, decomposition surprises, missing PRs                       | [[instructions/supervision-loop]]                                                                | Issue resolved or re-dispatched                                                          |
| Halt      | All work items have an open PR; emit final summary; status → `ready_for_user_review` | [[instructions/supervision-loop]]                                                                | Final summary emitted; supervisor exits                                                  |

There is no `Integrate` phase and no `Complete`-merge phase any more. The
supervisor never merges, never waits for CI, never reads `merge-prep-status`,
never re-runs reviewers. Async ownership transfers at `ready-for-review`
(GHA-set label) → user-side reviewer cron → daily-sweep CTA.

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

**Mandatory pre-dispatch gates** (see [[instructions/worker-dispatch#mandatory-pre-dispatch-gates]]):

1. **Host check** — `hostname` must match a registered polecat host. On
   mismatch the supervisor halts and uses the SSH+tmux path. No silent
   local fallback. (Issue #598.)
2. **PKB readiness probe** — `polecat ping-pkb` must succeed on the
   intended worker host. A failure means `PkbClient._initialize()` will
   crash inside the worker; supervisor refuses to dispatch. (Issue #600.)

```bash
# Claude worker
polecat run -t <task-id> -p <project>

# Gemini worker
polecat run -t <task-id> -p <project> -g

# Jules (async, Google infrastructure)
aops task <task-id> | jules new --repo <owner>/<repo>
```

> **`polecat` not on PATH?** In non-interactive shells (Bash tool, cron, CI,
> headless agent contexts), the `polecat`/`pc` zsh alias is not loaded — the
> shell-interactivity boundary matters: an interactive zsh session sees the
> alias, a Bash-tool subshell does not. Use the canonical expanded form:
> `uv run --project $AOPS $AOPS/polecat/cli.py <args>`. All dispatch
> examples below and in [[instructions/supervision-loop]] /
> [[instructions/worker-dispatch]] use bare `polecat`; substitute the
> `uv run` form when running outside an interactive shell.

**Polecat exit codes** (relevant for scripted supervisors):

- Exit 0 + "✅ already done" → task was `done`; graceful noop, move on
- Exit 2 + "🔒 Task is locked" → task already has an open PR / is past hand-off; record the PR in the work-items table and do not retry dispatch (the supervisor halts at `ready_for_user_review` regardless of merge state)

The supervisor decides WHICH task to dispatch next based on priority,
dependencies, and capacity — then dispatches one at a time.

For tightly coupled subtasks, the supervisor can use **coordinated branch
dispatch** — a shared feature branch with a draft PR, polecats pushing
sequentially. See [[instructions/worker-dispatch]] "Coordinated Branch
Dispatch" for the protocol. Individual dispatch remains the default.

**Critic-gated dispatch**: Tasks tagged `high-risk` or meeting blast-radius
criteria (irreversible operations, external system modifications, actions
that close recovery paths) require independent critic review before dispatch.
The supervisor prepares a dispatch review context with rollback plan, invokes
Pauli for safety assessment, and refuses dispatch if rollback requires physical
intervention. See [[instructions/worker-dispatch]] "Critic Gate."

> See [[instructions/worker-dispatch]] for pre-dispatch validation, worker
> selection, and dispatch protocol.

## Handoff Contract (task-212f1c82)

The supervisor's job ends when each work item is **opened as a PR with the
`ready-for-review` label set by the GHA mechanical merge-prep**. That is the
new completion signal — replacing the old `merge_ready` / "drive PR to
mergeable" / poll-CI loop.

| Layer                             | Owns                                                                                          | Surface                                   |
| --------------------------------- | --------------------------------------------------------------------------------------------- | ----------------------------------------- |
| **Supervisor (synchronous, you)** | Decompose → dispatch → halt at `ready_for_user_review` once each PR has `ready-for-review`    | One report per epic                       |
| **GHA pipeline (async, no PKB)**  | Mechanical merge-prep: rebase, CI, lint, conflict detection, then `ready-for-review` label    | PR labels + status checks                 |
| **User-side reviewer (async)**    | Strategic alignment + QA via judge-role agent. Cron at `dotfiles/cron/user-side-pr-review.sh` | PR review comment + label `approve-ready` |
| **Daily sweep**                   | Surfaces `approve-ready` PRs as one CTA list per epic                                         | Daily note                                |

**The supervisor does NOT poll GitHub Actions, does NOT wait for CI, does
NOT chase reviewers.** Once every work item has opened a PR and the
mechanical merge-prep has labelled it `ready-for-review` (or the supervisor
has confirmed the PR is open and is now under merge-prep's care), the
supervisor produces its final summary and halts.

### Halt state: `ready_for_user_review`

Set the epic to status `ready_for_user_review` (work-item-table state) once
every child task either:

- has an open PR, OR
- has been escalated/blocked with a clear reason recorded in the task body.

There is no further polling responsibility. The user-side reviewer cron
picks PRs up via the `ready-for-review` label, the rebuilt RBG judge agent
emits its Verdict, and on PASS the cron labels the PR `approve-ready`. The
daily-sweep CTA aggregates `approve-ready` PRs for the human.

### Final-summary template (one report per epic)

Emit exactly one summary at halt:

```
Epic <epic-id> — N PRs in `ready_for_user_review`

| # | Task ID  | Title              | PR                            | State            |
| - | -------- | ------------------ | ----------------------------- | ---------------- |
| 1 | task-aaa | <one-line title>   | https://github.com/.../pull/1 | ready-for-review |
| 2 | task-bbb | <one-line title>   | https://github.com/.../pull/2 | open (no label)  |
| 3 | task-ccc | <one-line title>   | —                             | blocked: <why>   |

Next surface: user-side reviewer cron will judge each `ready-for-review`
PR and label `approve-ready` on PASS. Approve-ready PRs appear in the
next `/daily` CTA list. No further supervisor action.
```

The supervisor MUST NOT include "polling will continue", "I'll check back
in N minutes", or any GHA-status loop. The transcript should not contain
`gh run watch`, repeated `gh pr view` calls on the same PR, or
`ScheduleWakeup`-driven re-orientation against the same merged-or-not
question.

**Task completion on merge** is handled by the existing
branch-name → `pkb` automation, NOT by the supervisor. The supervisor halts
at `ready_for_user_review`; merging happens later, asynchronously, after
the user has reviewed the daily-sweep CTA.

**Jules PR workflow**: Jules sessions show "Completed" when coding is done,
but require human approval on the Jules web UI before branches are pushed
and PRs are created. Check session status with `jules remote list --session`.

**Fork PR handling**: When a bot account pushes to a fork rather than the base
repo, CI workflows must use `head.sha` for checkout instead of `head.ref`.
Autofix-push steps should be guarded with `head.repo.full_name == github.repository`.

## Lifecycle Trigger Hooks

External triggers that start the supervision loop.

> **Configuration**: See [[WORKERS.md]] for runner types, capabilities,
> and sizing defaults — the supervisor reads these at dispatch time.

| Hook          | Trigger       | What it does                            |
| ------------- | ------------- | --------------------------------------- |
| `queue-drain` | cron / manual | Checks queue, starts supervisor session |
| `stale-check` | cron / manual | Resets tasks stuck beyond threshold     |
| `pr-merge`    | GitHub Action | PR merged → mark task done              |

## Known Limitations (from dogfood runs)

- Auto-finish overrides manual task completion when a task was already fixed
  by another worker. See `aops-fdc9d0e2`.
- Gemini polecats are slow (15-20+ min before first commit). Don't poll.
- Docker container name collisions when dispatching concurrent polecats.
  Use task ID in container name for uniqueness.
- dprint plugin 404s waste 10+ min per worker. Check dprint.json before dispatch.
- PKB MCP unreachable from sandbox containers — workers can't update task status.
- Pre-dispatch validation is critical: with hydration gate off, the supervisor's
  pre-dispatch check is the last chance to catch tasks targeting deprecated code.
- **Polecat stream noise ≠ failure.** Gemini workers routinely emit loud-looking
  stderr during boot — corrupted-credentials warnings, sandbox policy TOML parse
  errors, "Hook system message: Task bound" hook-loop spam, missing-MCP-tool
  errors (e.g. `release_task` not wired into the worker's MCP surface). These
  are transient/cosmetic in many cases and the worker can still complete, push,
  and open a PR. Do NOT halt on stderr keywords — wait for a terminal signal:
  `polecat finish`, PR URL, or process exit with non-zero status. "PR's up" /
  "Task updated" in the stream IS the success signal.
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
- **`merge-prep-status: pending`** — set by `pr-pipeline.yml`'s initialize
  job and cleared by the GHA mechanical merge-prep when the PR is ready.
  Per task-212f1c82 the supervisor does **not** read this status, does
  **not** trigger merge-prep manually, and does **not** wait on it. Once
  the work-item PR is open, the supervisor halts at
  `ready_for_user_review`; merge-prep, the `ready-for-review` label, and
  the user-side reviewer cron run asynchronously.

## Quick Reference

### Dispatch commands

```bash
polecat run -t <task-id> -p <project>       # claude
polecat run -t <task-id> -p <project> -g    # gemini
aops task <task-id> | jules new --repo <owner>/<repo>  # jules
```

### Monitoring (until PR opens — then HALT)

The supervisor's only monitoring obligation is "did the worker open a PR?"
Once each work item has a PR, the supervisor halts at
`ready_for_user_review` (see [[instructions/supervision-loop#halt-at-ready-for-user-review]]).
The mechanical merge-prep workflow labels the PR `ready-for-review` when
ready; the user-side reviewer cron picks it up. The supervisor does NOT
poll for that label, does NOT poll CI, does NOT chase reviewers.

```bash
# Dispatch workers in background — get notified on exit
polecat run -t <task-id> -p <project>  # Bash run_in_background: true
```

| Mechanism                                                          | What it watches | How it notifies             |
| ------------------------------------------------------------------ | --------------- | --------------------------- |
| `run_in_background` completion                                     | Worker exit     | Automatic Bash notification |
| `gh pr list --search head:polecat/<id>` (one-shot, on worker exit) | PR opened?      | Direct check                |

**Anti-patterns** (per task-212f1c82 — these used to be tolerated and are
now explicitly prohibited):

- Persistent PR-state Monitor scripts that watch CI / review state.
- `gh run watch`, repeated `gh pr view`, ScheduleWakeup loops on the same PR.
- Manual `agent-merge-prep.yml` triggers from the supervisor.
- Reading `merge-prep-status` commit status.
- Calling `gh pr merge` from the supervisor.

## Task Assignment Rules

- **Default assignee**: Set to `polecat` or leave unassigned.
- **Human assignment**: Never assign to `nic` unless the task reduces to a genuine binary human choice (e.g., "Do we use Pattern A or Pattern B?").
- **Decision subtasks**: When a real choice IS needed, create a minimal choice subtask that blocks the epic, providing full context to decide. Never assign the parent epic back to `nic`.
- **Underspecified tasks**: Even underspecified epics should not go to `nic`: file a research/decomposition task for an agent to do the legwork first.

## Handover

**Always leave a loose thread.** Every agent that completes work as part of a chain MUST leave at least one PKB task that says what comes next — unless the work is fully complete with no follow-ups. Use `mcp__pkb__append` to record information mid-workflow and `mcp__pkb__complete_task` to close a task with a final note.

- If dispatch is blocked: file a refinement/blocking task.
- If a phase is complete but the epic remains: ensure the next subtask is clear and in `ready` or `queued`.
- Never assume the user knows the graph. Link to the next task explicitly.

Example: `mcp__pkb__create_task(parent="epic-123", title="Phase 2: Implementation", body="Phase 1 (Research) complete. Next: implement the proposed changes in src/...")`

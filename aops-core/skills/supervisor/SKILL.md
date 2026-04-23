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

Every invocation discovers what's available. The supervisor adapts dispatch
strategy to what exists right now — not what existed last time. A session
that starts on a Mac with local polecat and moves to a crew container with
only Docker and gh is normal, not exceptional.

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

## Phases

The supervisor is NOT a pipeline — it's a loop that enters at whatever phase
the epic needs on each invocation.

```
ORIENT → DECOMPOSE → (plan-review gate) → WAITING → DISPATCH → MONITOR → REACT → INTEGRATE → COMPLETE
```

| Phase     | What happens                                                          | Instructions                                                                                     | Exit condition                                                                           |
| --------- | --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------- |
| Orient    | Read epic, verify child statuses, decide what to do next              | [[instructions/supervision-loop]]                                                                | Next phase selected                                                                      |
| Decompose | Break work into PR-sized subtasks; run Phase 2 review                 | [[instructions/decomposition-and-review]]                                                        | Synthesis complete; plan-review gate evaluated                                           |
| Review    | Plan-review halt — decomposition synthesized, awaiting human approval | [[instructions/decomposition-and-review#plan-review-gate-phase-25]]                              | **Parent task promoted to `queued` by human** (status transition IS the approval record) |
| Dispatch  | Send tasks to workers (local or remote via SSH+tmux)                  | [[instructions/worker-dispatch]], [[instructions/worker-dispatch#remote-dispatch-via-ssh--tmux]] | Worker fired; task status → `in_progress`                                                |
| Monitor   | Event-driven: background notifications + PR Monitor                   | [[instructions/supervision-loop]]                                                                | State change event observed                                                              |
| React     | Handle failures, conflicts, scope changes                             | [[instructions/supervision-loop]]                                                                | Issue resolved or re-dispatched                                                          |
| Integrate | Verify, merge, sync                                                   | [[instructions/supervision-loop]]                                                                | PR merged; task → done                                                                   |
| Complete  | Update epic, capture knowledge, file follow-ups                       | [[instructions/knowledge-capture]]                                                               | Epic done; knowledge captured                                                            |

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

```bash
# Claude worker
polecat run -t <task-id> -p <project>

# Gemini worker
polecat run -t <task-id> -p <project> -g

# Jules (async, Google infrastructure)
aops task <task-id> | jules new --repo <owner>/<repo>
```

> **`polecat` not on PATH?** In non-interactive shells (Bash tool, cron, CI), the `polecat`/`pc` alias
> may not be loaded. Use the canonical form: `uv run --project $AOPS $AOPS/polecat/cli.py <args>`

**Polecat exit codes** (relevant for scripted supervisors):

- Exit 0 + "✅ already done" → task was `done`; graceful noop, move on
- Exit 2 + "🔒 Task is locked" → task is `merge_ready` with an open PR; check and merge, do not retry dispatch

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

## PR Review Pipeline

PRs arrive from workers (polecat branches, Jules PRs). The pipeline is
specified in [[specs/pr-pipeline.md]]; bots prepare, the human decides once
via a GitHub Environment approval gate.

**Phase 1 — CI + Axiom Review (on every push):**

1. `pr-pipeline.yml` — sequential `lint` → `typecheck` → `pytest`. Lint uses
   a PAT so autofix pushes trigger a clean pipeline restart.
2. `agent-enforcer.yml` — axiom compliance review, fires on `workflow_run`
   when CI completes. Can push fixes directly or request changes.

**Phase 2 — Merge Prep (cron-driven, no human trigger):**

3. `merge-prep-cron.yml` — dispatcher. Runs on `workflow_run` + 30-min cron.
   Qualifies PRs ≥15 min old with no in-progress run and no terminal
   `merge-prep-status`.
4. `agent-merge-prep.yml` — the Claude merge-prep agent. Triages all review
   feedback, fixes CI failures, resolves conflicts, posts a triage summary,
   approves the PR, sets `merge-prep-status: success`, and triggers
   `summary-and-merge.yml`.

**Phase 3 — Human Decision (Environment gate):**

5. `summary-and-merge.yml` Job 1 posts the decision brief comment. Job 2
   requires the `production` GitHub Environment — the maintainer clicks
   **Approve** in the Actions environment UI, and the PR squash-merges
   automatically. Clicking **Reject** holds the PR open.

**Pipeline limitations:**

- PRs that modify workflow files (`.github/workflows/`) cannot get pipeline
  review due to OIDC validation (workflow content must match default branch).
  These PRs need manual review and admin merge.
- Bot reviewers take 2–5 min to post. The 15-minute age gate in the
  merge-prep dispatcher preserves the bazaar window.

**Merge flow (what the human sees):**

- Decision brief comment appears on the PR once merge-prep graduates it.
- Approval happens in the GitHub Environments UI, not as a PR comment —
  there is no "lgtm" / "merge" / "@claude merge" trigger.
- Admin bypass: `gh pr merge <PR> --squash --admin --delete-branch` for PRs
  that can't progress through the pipeline (workflow PRs, urgent fixes).

**Task completion on merge**: When a PR merges, a GitHub Action parses the
task ID from the branch name (`polecat/aops-XXXX`) and marks the task done.
This closes the loop without supervisor involvement.

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
- **MCP / CLI / disk three-way divergence.** After a `git pull`, the local
  filesystem has the task file, the local `pkb show` CLI usually finds it, but
  the remote PKB MCP (tailscale host) can lag by minutes. Polecat's bootstrap
  validation hits the MCP and will exit if the task isn't there yet, leaving
  the task claimed but no worktree. Recovery: `polecat reset-stalled --hours 0
  --force` then re-dispatch. Pre-flight: `pkb show <task-id>` AND a PKB MCP
  `get_task` before dispatching a freshly-pulled task.
- **`merge-prep-status: pending`** — set by `pr-pipeline.yml`'s initialize
  job and cleared only when the merge-prep agent sets `success` (graduation)
  or `failure` (after 3 consecutive failures). A PR with green CI may still
  sit "yellow" until the merge-prep agent runs. The supervisor cannot clear
  this directly; normal resolution is to wait for the next cron tick or
  dispatch `agent-merge-prep.yml` manually via `gh workflow run`. Admin
  bypass remains available for urgent cases.

## Quick Reference

### Dispatch commands

```bash
polecat run -t <task-id> -p <project>       # claude
polecat run -t <task-id> -p <project> -g    # gemini
aops task <task-id> | jules new --repo <owner>/<repo>  # jules
```

### Monitoring (Event-Driven — Default)

Use event-driven monitoring to avoid burning tokens on polling loops.
See [[instructions/supervision-loop#event-driven-monitoring-default]] for
full details and the ready-to-paste Monitor script.

```bash
# 1. Dispatch workers in background — get notified on exit
polecat run -t <task-id> -p <project>  # Bash run_in_background: true

# 2. Start persistent PR-state Monitor (one for all branches)
# See supervision-loop.md for the full script — use Monitor tool to stream it

# 3. Safety-net wakeup (1800s+ only — NOT primary monitoring)
# ScheduleWakeup(delaySeconds=1800, reason="safety-net stall check")
```

| Mechanism                      | What it watches        | How it notifies             |
| ------------------------------ | ---------------------- | --------------------------- |
| `run_in_background` completion | Worker exit            | Automatic Bash notification |
| Persistent Monitor script      | PR state transitions   | Monitor tool line events    |
| ScheduleWakeup (1800s+ safety) | Stalled/missed signals | Timer-based fallback        |

**Anti-pattern**: `polecat list` / `gh pr list` every 4–5 min via
ScheduleWakeup — wastes tokens and context. Use only as one-shot fallback
when event-driven monitoring is unavailable.

```bash
# Fallback commands (one-shot, NOT for polling loops)
polecat list                           # active polecats
gh pr list --state open --limit 20     # open PRs
polecat reset-stalled --hours 4        # reset hung tasks
polecat sync                           # sync mirrors after merging
```

### PR triage

| Signal                               | Action                                                      |
| ------------------------------------ | ----------------------------------------------------------- |
| Reasonable adds/dels, targeted files | `gh pr merge <N> --squash --delete-branch`                  |
| Code already in main (stale branch)  | `gh pr close <N> --comment "Stale branch"`                  |
| Massive deletions (stale mirror)     | `gh pr close <N> --comment "Repo nuke"` then `polecat sync` |

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

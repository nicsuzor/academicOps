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
ORIENT → DECOMPOSE → DISPATCH → MONITOR → REACT → INTEGRATE → COMPLETE
```

| Phase     | What happens                                             | Instructions                                                                                     |
| --------- | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Orient    | Read epic, verify child statuses, decide what to do next | [[instructions/supervision-loop]]                                                                |
| Decompose | Break work into PR-sized subtasks                        | [[instructions/decomposition-and-review]]                                                        |
| Dispatch  | Send tasks to workers (local or remote via SSH+tmux)     | [[instructions/worker-dispatch]], [[instructions/worker-dispatch#remote-dispatch-via-ssh--tmux]] |
| Monitor   | Event-driven: background notifications + PR Monitor      | [[instructions/supervision-loop]]                                                                |
| React     | Handle failures, conflicts, scope changes                | [[instructions/supervision-loop]]                                                                |
| Integrate | Verify, merge, sync                                      | [[instructions/supervision-loop]]                                                                |
| Complete  | Update epic, capture knowledge, file follow-ups          | [[instructions/knowledge-capture]]                                                               |

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

PRs arrive from workers (polecat branches, Jules PRs). The
`pr-review-pipeline.yml` GitHub Action handles automated review. Human
merges via GitHub UI or auto-merge for clean PRs.

**PR review pipeline** (`pr-review-pipeline.yml`) has three jobs:

1. **rbg-and-marsha** — scope/compliance + acceptance checks. Runs first on
   PR open/synchronize, giving bot reviewers (Gemini, Copilot) time to post.
2. **claude-review** — bot comment triage. Runs after enforcer-and-qa (~3 min
   delay). Triages bot reviewer comments as genuine bug / valid improvement /
   false positive / scope creep, and pushes fixes for actionable items.
3. **claude-lgtm-merge** — human-triggered merge agent. Fires on human LGTM
   comment, PR approval, or workflow_dispatch. Addresses all outstanding review
   comments, runs lint/tests, and posts final status.

**Pipeline limitations:**

- PRs that modify workflow files (`.github/workflows/`) cannot get pipeline
  review due to OIDC validation (workflow content must match default branch).
  These PRs need manual review and admin merge.
- Bot reviewers take 2–5 min to post. The pipeline ordering (enforcer first)
  provides enough delay for most, but Copilot may occasionally post after
  triage runs.

**Merge flow:**

- Auto-merge is enabled. Once the merge agent approves and CI passes, GitHub
  merges automatically.
- Human LGTM comment (e.g., "lgtm", "merge", "@claude merge") triggers the
  merge agent.
- Admin bypass: `gh pr merge <PR> --squash --admin --delete-branch` for PRs
  that can't get pipeline approval (workflow PRs, urgent fixes).

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

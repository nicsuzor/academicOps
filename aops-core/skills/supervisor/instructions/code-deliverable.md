# Code Deliverable Subworkflow

How the generic supervisor loop (see [[../SKILL.md]] and [[supervision-loop]]) maps onto the **code-PR concrete case**: each work item is a pull request, the review surface is GitHub, async ownership transfers via PR labels.

The universal loop — orient → decompose → review → dispatch → verify → react → halt — is unchanged. This file specialises it: what "dispatch" looks like for a coding task, what "completion signal" means when the deliverable is a PR, and which specific tooling (`polecat run`, `gh`, GHA labels) the supervisor uses.

A research deliverable would have its own subworkflow file with different vocabulary; the generic loop in SKILL.md should still apply unchanged.

> **`polecat` not on PATH?** Dispatch examples here use bare `polecat`. In non-interactive shells, the alias is not loaded. Substitute the canonical form: `uv run --project $AOPS $AOPS/polecat/cli.py <args>`.

## Mapping the Generic Loop to Code Deliverables

| Generic phase  | Code-deliverable specialisation                                                                           |
| -------------- | --------------------------------------------------------------------------------------------------------- |
| Decompose      | Subtasks are PR-sized (≤ 0.5d, ≤ 10 files, single "why", reviewable in ≤ 15 min).                         |
| Dispatch       | `polecat run -t <task-id> -p <project>` (with `-g` for Gemini), or Jules via `pkb task ... \| jules new`. |
| Verify         | Marsha reads the PR diff + worker exit; returns PASS/FAIL/REVISE.                                         |
| Review surface | GitHub PR; mechanical merge-prep adds the `ready-for-review` label asynchronously.                        |
| Integrate      | Replaced by **halt at `ready_for_user_review`**. The supervisor never merges.                             |

## Mandatory Pre-Dispatch Gates

Three gates MUST pass before any `polecat run` invocation. **Pauli runs them during preflight** — the main agent never invokes them inline. Canonical specs in [[worker-dispatch#mandatory-pre-dispatch-gates]]:

1. **Host check (issue #598)** — `hostname -s` matches a registered polecat host. Mismatch → SSH+tmux remote dispatch; no silent local fallback.
2. **PKB readiness probe (issue #600)** — `polecat ping-pkb` succeeds on the intended worker host. Failure → refuse to dispatch.
3. **Pre-flight Confirmation Summary** — 4-row table (Task ID / Source repo / `project=` / Next link). Halt if any row is unknown or rows 2/3 disagree.

## Dispatch Commands

```bash
# Claude worker
polecat run -t <task-id> -p <project>

# Gemini worker
polecat run -t <task-id> -p <project> -g

# Jules (async, Google infrastructure)
pkb task <task-id> | jules new --repo <owner>/<repo>
```

### Polecat Exit Codes

- Exit 0 + "✅ already done" → task was `done`; graceful noop, move on.
- Exit 2 + "🔒 Task is locked" → task already has an open PR; record the PR in the work-items table and do not retry dispatch.

### Coordinated Branch Dispatch

For tightly coupled subtasks, use a shared feature branch with a draft PR; polecats push sequentially. See [[worker-dispatch#coordinated-branch-dispatch]] for the protocol.

### Critic-Gated Dispatch

Tasks tagged `high-risk` or meeting blast-radius criteria require independent critic review before dispatch. Pauli invokes the critic during preflight; see [[worker-dispatch#critic-gate-for-high-blast-radius-tasks]].

## Monitor: Wait for the PR, Then Halt

The supervisor's only monitoring obligation is "did the worker open a PR?" Once each work item has a PR, the supervisor halts at `ready_for_user_review` and the existing GHA pipeline takes over. The supervisor does NOT poll CI, does NOT chase reviewers, does NOT track merge-prep status.

```bash
# Dispatch in background — get notified on exit
polecat run -t <task-id> -p <project>  # Bash run_in_background: true
```

| Mechanism                                                                                         | What it watches              | How it notifies                                                              |
| ------------------------------------------------------------------------------------------------- | ---------------------------- | ---------------------------------------------------------------------------- |
| `run_in_background` completion                                                                    | Worker exit (one dispatched) | Automatic Bash notification                                                  |
| `gh pr list --search head:polecat/<id>` (one-shot, on worker exit)                                | PR opened?                   | Direct check                                                                 |
| `Monitor` on `docker events --filter event=die --filter name=polecat-` (persistent, session-life) | Any polecat worker exit      | One chat notification per `die` — use for in-session batch (concurrency-cap) |

The third row is the **in-session notify-watch** — armed once when the user requests a multi-tick batch ("maintain N concurrent workers" / "drain the queue this session"). See [[../SKILL.md#in-session-multi-tick-supervision-notify-watch]] for arming, crew filtering, and stop conditions.

On worker exit, hand the result to **marsha** (see [[../SKILL.md#marsha--verify]]). Marsha reads the PR / diff / transcript on the supervisor's behalf and returns PASS/FAIL/REVISE. The main agent never reads them.

| Outcome            | Main agent action                                          |
| ------------------ | ---------------------------------------------------------- |
| Marsha PASS        | Record PR in work items; mark item `ready_for_user_review` |
| Marsha FAIL        | Call pauli with `role=react`                               |
| Marsha REVISE      | File a verification subtask (depends_on PR)                |
| Worker exit, no PR | Call pauli with `role=react`, context `no-deliverable`     |

### Removed Responsibilities (per task-212f1c82)

The supervisor MUST NOT do any of the following — owned by the existing GHA pipeline:

- Persistent PR-state Monitor watching CI / reviewer state.
- `gh run watch`, `gh pr view --json statusCheckRollup,reviews` polling loops.
- "Ready-to-advance" detection across the bot reviewer set.
- Manual `gh workflow run agent-merge-prep.yml` triggers.
- Reading `merge-prep-status` commit status.
- Reacting to `CHANGES_REQUESTED` reviews from the bazaar bots.
- `gh pr merge` of any kind.
- `polecat sync` after merging.

If a transcript shows the supervisor doing any of these against a PR that has already been opened, that's a bug — the supervisor was supposed to have halted.

## Handoff Contract (task-212f1c82)

The supervisor's job ends when each work item is **opened as a PR**. That is the completion signal — replacing the old `merge_ready` / "drive PR to mergeable" / poll-CI loop.

| Layer                             | Owns                                                                        | Surface                   |
| --------------------------------- | --------------------------------------------------------------------------- | ------------------------- |
| **Supervisor (synchronous, you)** | Decompose → dispatch → halt at `ready_for_user_review` once each PR is open | One report per epic       |
| **GHA pipeline (async)**          | The existing PR pipeline: CI, lint, axiom enforcer, agent merge-prep        | PR labels + status checks |

The supervisor does NOT poll GitHub Actions, does NOT wait for CI, does NOT chase reviewers. Once every work item has opened a PR, produce the final summary and halt.

### Halt state: `ready_for_user_review`

Set the epic to `ready_for_user_review` once every child task either:

- has an open PR, OR
- has been escalated/blocked with a clear reason recorded in the task body.

The existing GHA pipeline (pr-pipeline.yml, agent-enforcer.yml, agent-merge-prep.yml, summary-and-merge.yml) handles CI, axiom enforcement, merge prep, and the GitHub Environment approval gate. Review agents (rbg, pauli, marsha) may be invoked on the PR by callers separately.

### Final-summary template (one report per epic)

```
Epic <epic-id> — N PRs in `ready_for_user_review`

| # | Task ID  | Title              | PR                            | State            |
| - | -------- | ------------------ | ----------------------------- | ---------------- |
| 1 | task-aaa | <one-line title>   | https://github.com/.../pull/1 | ready-for-review |
| 2 | task-bbb | <one-line title>   | https://github.com/.../pull/2 | open (no label)  |
| 3 | task-ccc | <one-line title>   | —                             | blocked: <why>   |

Next surface: the existing GHA pipeline. No further supervisor action.
```

The supervisor MUST NOT include "polling will continue", "I'll check back in N minutes", or any GHA-status loop. **Task completion on merge** is handled by the existing branch-name → `pkb` automation, NOT by the supervisor.

### Jules PR workflow

Jules sessions show "Completed" when coding is done, but require human approval on the Jules web UI before branches are pushed and PRs are created. Check session status with `jules remote list --session`.

### Fork PR handling

When a bot account pushes to a fork rather than the base repo, CI workflows must use `head.sha` for checkout instead of `head.ref`. Autofix-push steps should be guarded with `head.repo.full_name == github.repository`.

## Deferred Verification Tracking

Any TDD fix that ships with tests the worker could not actually run (Docker rebuild needed, credentialed service, long wall-clock, external API) is **not verified** — it is inference. Marsha returns `REVISE` on these; the main agent files a follow-up verification task with `depends_on` the PR and `soft_blocks` the epic's COMPLETE transition. Do not mark the epic complete until every deferred-verification task is `done` or explicitly accepted by the human as permanently manual.

## Code-Deliverable Known Limitations

(See [[WORKERS.md#failure-modes-per-worker]] for the universal per-worker list; coding-specific items below.)

- Auto-finish overrides manual task completion when a task was already fixed by another worker. See `aops-fdc9d0e2`.
- Gemini polecats are slow (15–20+ min before first commit). Don't poll. Marsha-side noise (boot-time stderr) is cosmetic — see [[WORKERS.md]].
- Docker container name collisions when dispatching concurrent polecats. Use task ID in container name for uniqueness.
- dprint plugin 404s waste 10+ min per worker. Check `dprint.json` before dispatch.
- PKB MCP unreachable from sandbox containers — workers can't update task status.
- **`merge-prep-status: pending`** is set/cleared by the GHA pipeline. The supervisor does **not** read this status, does **not** trigger merge-prep manually, and does **not** wait on it.

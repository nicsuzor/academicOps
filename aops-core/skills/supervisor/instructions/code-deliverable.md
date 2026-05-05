# Code Deliverable Subworkflow

How the generic supervisor loop (see [[../SKILL.md]] and [[supervision-loop]])
maps onto the **code-PR concrete case**: each work item is a pull request, the
review surface is GitHub, and async ownership transfers via PR labels.

The universal supervisor loop — decompose → review → dispatch → monitor →
react → integrate (or halt-at-ready_for_user_review) — is unchanged. This
file specialises it: what "dispatch" looks like for a coding task, what
"completion signal" means when the deliverable is a PR, and which specific
tooling (`polecat run`, `gh`, GHA labels) the supervisor uses.

A research deliverable (e.g. drafting a methodology section) would have its
own subworkflow file with different vocabulary — the generic loop in SKILL.md
should still apply unchanged.

> **`polecat` not on PATH?** Dispatch examples here use bare `polecat`. In
> non-interactive shells (Bash tool, cron, CI, headless agent), the
> `polecat`/`pc` zsh alias is not loaded. Substitute the canonical form:
> `uv run --project $AOPS $AOPS/polecat/cli.py <args>`.

---

## Mapping the Generic Loop to Code Deliverables

| Generic phase  | Code-deliverable specialisation                                                                            |
| -------------- | ---------------------------------------------------------------------------------------------------------- |
| Decompose      | Subtasks are PR-sized (≤ 0.5d, ≤ 10 files, single "why", reviewable in ≤ 15 min).                          |
| Dispatch       | `polecat run -t <task-id> -p <project>` (with `-g` for Gemini), or Jules via `aops task ... \| jules new`. |
| Monitor        | Wait for the worker to **open a PR**. That is the completion signal.                                       |
| Review surface | GitHub PR; mechanical merge-prep adds the `ready-for-review` label asynchronously.                         |
| Integrate      | Replaced by **halt at `ready_for_user_review`**. The supervisor never merges.                              |

---

## Mandatory Pre-Dispatch Gates

Three gates MUST pass before any `polecat run` invocation. See
[[worker-dispatch#mandatory-pre-dispatch-gates]] for the canonical
specifications. Summarised:

1. **Host check (issue #598)** — `hostname -s` must match a registered
   polecat host. Mismatch → switch to SSH+tmux remote dispatch; no silent
   local fallback.
2. **PKB readiness probe (issue #600)** — `polecat ping-pkb` must succeed on
   the intended worker host. A failure means `PkbClient._initialize()` will
   crash inside the worker; supervisor refuses to dispatch.
3. **Pre-flight Confirmation Summary (task-4cea5008, aops-e2d639e2)** —
   4-row table (Task ID / Source repo / `project=` field / Next link in
   chain) confirming the dispatch parameters resolve unambiguously. Halt
   if any row is unknown or rows 2/3 disagree. See
   [[../SKILL.md#pre-flight-confirmation-summary]] for the table and
   [[worker-dispatch#gate-3-pre-flight-confirmation-summary-task-4cea5008-aops-e2d639e2]]
   for the grep mechanic. Do not duplicate the table here.

---

## Dispatch Commands

```bash
# Claude worker
polecat run -t <task-id> -p <project>

# Gemini worker
polecat run -t <task-id> -p <project> -g

# Jules (async, Google infrastructure)
aops task <task-id> | jules new --repo <owner>/<repo>
```

### Polecat Exit Codes

- Exit 0 + "✅ already done" → task was `done`; graceful noop, move on.
- Exit 2 + "🔒 Task is locked" → task already has an open PR / is past
  hand-off; record the PR in the work-items table and do not retry dispatch
  (the supervisor halts at `ready_for_user_review` regardless of merge state).

### Coordinated Branch Dispatch

For tightly coupled subtasks, use **coordinated branch dispatch** — a shared
feature branch with a draft PR, polecats pushing sequentially. See
[[worker-dispatch#coordinated-branch-dispatch]] for the full protocol; this
file does not duplicate it.

### Critic-Gated Dispatch

Tasks tagged `high-risk` or meeting blast-radius criteria (irreversible
operations, external system modifications, actions that close recovery
paths) require independent critic review before dispatch. See
[[worker-dispatch#critic-gate]].

---

## Monitor: Wait for the PR, Then Halt

The supervisor's only monitoring obligation is "did the worker open a PR?"
Once each work item has a PR, the supervisor halts at `ready_for_user_review`
and the existing GHA pipeline takes over. The supervisor does NOT poll CI,
does NOT chase reviewers, does NOT track merge-prep status.

```bash
# Dispatch workers in background — get notified on exit
polecat run -t <task-id> -p <project>  # Bash run_in_background: true
```

| Mechanism                                                          | What it watches | How it notifies             |
| ------------------------------------------------------------------ | --------------- | --------------------------- |
| `run_in_background` completion                                     | Worker exit     | Automatic Bash notification |
| `gh pr list --search head:polecat/<id>` (one-shot, on worker exit) | PR opened?      | Direct check                |

| Outcome                 | Supervisor action                                                |
| ----------------------- | ---------------------------------------------------------------- |
| PR opened               | Record PR in work items; mark item `ready_for_user_review`       |
| No PR + worker exit 0   | REACT: re-dispatch or escalate (worker may have hit a stop-cond) |
| No PR + worker exit !=0 | REACT: read transcript, re-dispatch or file blocker              |

### Removed Responsibilities (per task-212f1c82)

The supervisor MUST NOT do any of the following. They are owned by the
existing GHA pipeline:

- Persistent PR-state Monitor watching CI / reviewer state across all branches.
- `gh run watch`, `gh pr view --json statusCheckRollup,reviews` polling loops.
- "Ready-to-advance" detection across the bot reviewer set.
- Manual `gh workflow run agent-merge-prep.yml` triggers.
- Reading `merge-prep-status` commit status.
- Reacting to `CHANGES_REQUESTED` reviews from the bazaar bots.
- `gh pr merge` of any kind.
- `polecat sync` after merging.

If a transcript shows the supervisor doing any of these against a PR that
has already been opened, that's a bug — the supervisor was supposed to have
halted.

### Anti-patterns (PR-state polling)

- Persistent PR-state Monitor scripts that watch CI / review state.
- `gh run watch`, repeated `gh pr view`, ScheduleWakeup loops on the same PR.
- Manual `agent-merge-prep.yml` triggers from the supervisor.
- Reading `merge-prep-status` commit status.
- Calling `gh pr merge` from the supervisor.

---

## Handoff Contract (task-212f1c82)

The supervisor's job ends when each work item is **opened as a PR**. That
is the completion signal — replacing the old `merge_ready` / "drive PR to
mergeable" / poll-CI loop.

| Layer                             | Owns                                                                        | Surface                   |
| --------------------------------- | --------------------------------------------------------------------------- | ------------------------- |
| **Supervisor (synchronous, you)** | Decompose → dispatch → halt at `ready_for_user_review` once each PR is open | One report per epic       |
| **GHA pipeline (async)**          | The existing PR pipeline: CI, lint, axiom enforcer, agent merge-prep        | PR labels + status checks |

The supervisor does NOT poll GitHub Actions, does NOT wait for CI, does NOT
chase reviewers. Once every work item has opened a PR, the supervisor
produces its final summary and halts. The existing GHA pipeline takes over
from there — it has not changed.

### Halt state: `ready_for_user_review`

Set the epic to status `ready_for_user_review` once every child task either:

- has an open PR, OR
- has been escalated/blocked with a clear reason recorded in the task body.

There is no further polling responsibility. The existing GHA pipeline
(pr-pipeline.yml, agent-enforcer.yml, agent-merge-prep.yml,
summary-and-merge.yml) handles CI, axiom enforcement, merge prep, and the
GitHub Environment approval gate. Review agents (rbg, pauli, marsha) may be
invoked on the PR by callers separately — each as its own modular surface.
The supervisor itself plays no further role.

### Final-summary template (one report per epic)

Emit exactly one summary at halt:

```
Epic <epic-id> — N PRs in `ready_for_user_review`

| # | Task ID  | Title              | PR                            | State            |
| - | -------- | ------------------ | ----------------------------- | ---------------- |
| 1 | task-aaa | <one-line title>   | https://github.com/.../pull/1 | ready-for-review |
| 2 | task-bbb | <one-line title>   | https://github.com/.../pull/2 | open (no label)  |
| 3 | task-ccc | <one-line title>   | —                             | blocked: <why>   |

Next surface: the existing GHA pipeline (pr-pipeline.yml → agent-enforcer.yml
→ agent-merge-prep.yml → summary-and-merge.yml). No further supervisor
action.
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

### Jules PR workflow

Jules sessions show "Completed" when coding is done, but require human
approval on the Jules web UI before branches are pushed and PRs are created.
Check session status with `jules remote list --session`.

### Fork PR handling

When a bot account pushes to a fork rather than the base repo, CI workflows
must use `head.sha` for checkout instead of `head.ref`. Autofix-push steps
should be guarded with `head.repo.full_name == github.repository`.

---

## Reading Worker Completion Signals

Workers communicate back via two mechanisms:

1. **PKB task status change**: Worker calls `release_task` MCP method, which
   updates status and may append structured notes to the task body
   (decisions made, blockers hit, scope changes discovered).
2. **PR creation**: Worker creates a PR (or pushes to feature branch in
   coordinated mode).

During MONITOR, read BOTH:

- Query PKB: `mcp__pkb__get_task(<task-id>)` — check `status` AND read the
  task body for worker-appended notes.
- Check GitHub: `gh pr list --search "head:polecat/<task-id>"`
- If using coordinated branch: check that the feature branch has expected
  commits from the previous worker before dispatching the next.

Use worker notes to update the work items table, decide whether the task
truly needs follow-up, and inform subsequent task specs with lessons learned.

### Reading Polecat Stream Output (Don't Panic)

When streaming a polecat's stdout/stderr, expect a lot of noise that looks
catastrophic but isn't. Gemini workers in particular emit:

- "Failed to load API key from storage: Error: Corrupted credentials file detected…"
- "Policy file error in deny-extension-writes.toml / polecat-sandbox.toml"
- "Error executing tool mcp_pkb_release_task: Tool … not found. Did you mean…"
- "Hook system message: ▶ Task bound. Handover required before exit." repeated 20+ times

None of these are terminal. Workers with these warnings have still produced
clean PRs. **Do not halt the supervision on stream keywords.** The
authoritative terminal signals are:

- Worker process exits with non-zero status (background task notification)
- `polecat finish` output appears
- PR URL is posted to the stream ("PR's up: https://…")
- "Task updated" / "Mission accomplished" appears after a release_task call

If you read scary text but the process is still running and no terminal
signal has arrived, **keep waiting**. Filter your Monitor for terminal
signals, not for words like "Error" or "Corrupted". 2026-04-20 dogfood:
supervisor nearly killed a gemini polecat that was in fact seconds away
from opening PR #640.

### Polecat Lifecycle Signals

PKB status and PR state are the primary signals, but for ambiguous cases
also check the polecat lifecycle directly:

- **`polecat list`** — is the task's worktree still registered? Present =
  worker or auto-finish is still running. Absent = cleanup completed.
- **`docker ps`** — is the container still up? Long-running containers
  (>45 min for cycles that finished their work) often mean the CLI agent
  is looping post-handover, not still working. Cross-check against PKB
  status: if `status: done` but container still up, the worker has
  finished but isn't terminating cleanly.
- **Dispatch command output file** — when the supervisor backgrounded
  `polecat run`, its stdout is written to the background task's output
  file. Polecat writes lifecycle events at the end:
  `Agent completed successfully`, `Running auto-finish`, `Nuking worktree`,
  `Worktree removed`. If you see these, the run is fully wound down.
  **Do not check this file early** — it stays empty until polecat reaches
  its teardown phase. Check it only when you suspect the worker has
  finished.
- **Transcript** at `$POLECAT_HOME/polecats/<task-id>.jsonl` — written
  after the worker finishes; provides the full session log for evaluation.

### Non-PR Work (PKB-only dispatches)

Not every dispatch produces a PR. Skills like `/sleep`, `/planner`,
`/remember` write directly to the PKB via MCP and never touch the worktree
branch. For these tasks:

- **Don't** check `gh pr list` — no PR will appear.
- **Don't** check the polecat worktree's git log for commits — the worktree
  may have zero commits even on a successful run.
- **Do** check `$ACA_DATA` (brain repo) `git log --since` for auto-sync
  commits that touch task/knowledge/project files, plus the task's body
  for worker-appended evidence.
- **Do** read the transcript if the brain-side signals are thin.

The dispatch task body is still the primary evidence surface — workers
should append a completion summary there before calling `release_task`.

### Deep Evaluation via Transcripts

When a worker's output is surprising (unexpected scope, quality concerns,
or failure without clear cause), read the polecat transcript for deeper
insight.

**Locating transcripts** (auto-generated by crontab running
`transcript.py`):

- `$POLECAT_HOME/polecats/<task-id>.jsonl` — raw JSONL (primary)
- `$AOPS_SESSIONS/transcripts/` — generated markdown (uses session naming
  convention from PR #513)
- Legacy fallbacks checked by `find_polecat_transcript()`:
  `$AOPS_SESSIONS/polecats/`, `$AOPS_SESSIONS/transcripts/polecats/`

Convert raw JSONL if needed:

```bash
uv run python aops-core/scripts/transcript.py $POLECAT_HOME/polecats/<task-id>.jsonl
```

**What to look for**:

| Signal in transcript                          | Indicates                                       |
| --------------------------------------------- | ----------------------------------------------- |
| Worker attempted something 3+ times           | Codebase obstacle — may need different approach |
| Worker modified files outside task scope      | Scope creep — review PR carefully               |
| Worker skipped an AC item without explanation | May need re-dispatch with tighter spec          |
| Worker encountered tool/infra errors          | Infrastructure gap — file follow-up             |
| Worker made autonomous decisions not in AC    | Check whether decisions were sound              |

**When to read transcripts**:

- Task failed with no PR and no clear error in task status
- PR has unexpected scope (too large, wrong files, unrelated changes)
- Worker's `release_task` notes don't match PR content
- Before deciding to re-dispatch a failed task (REACT phase)

**Anti-pattern**: Reading every transcript. Only read when lightweight
signals (task status, PR diff, worker notes) are insufficient.

### Deferred Verification Tracking

Any TDD fix that ships with tests the worker could not actually run
(Docker rebuild needed, credentialed service, long wall-clock, external
API) is **not verified** — it is inference. Before the epic can complete,
each unrunnable test becomes an explicit follow-up task, not a note in
the PR body.

On MONITOR, for every work item whose report (see [[worker-dispatch]]
parallel dispatch report shape) lists deferred verification:

1. Create a child verification task under the same epic with:
   - Exact reproduce steps (command, env, expected result)
   - `depends_on` the PR that shipped the fix
   - `soft_blocks` the epic's COMPLETE transition
2. Link the task ID into the PR body under a `## Deferred verification`
   heading.
3. Do not mark the epic complete until every deferred-verification task
   is `done` or explicitly accepted by the human as permanently manual.

---

## Code-Deliverable Known Limitations

(See [[../SKILL.md#known-limitations]] for the universal list; these are
the coding-specific items.)

- Auto-finish overrides manual task completion when a task was already
  fixed by another worker. See `aops-fdc9d0e2`.
- Gemini polecats are slow (15-20+ min before first commit). Don't poll.
- Docker container name collisions when dispatching concurrent polecats.
  Use task ID in container name for uniqueness.
- dprint plugin 404s waste 10+ min per worker. Check `dprint.json` before
  dispatch.
- PKB MCP unreachable from sandbox containers — workers can't update
  task status.
- Pre-dispatch validation is critical: with hydration gate off, the
  supervisor's pre-dispatch check is the last chance to catch tasks
  targeting deprecated code.
- **`merge-prep-status: pending`** — set by `pr-pipeline.yml`'s initialize
  job and cleared by the GHA mechanical merge-prep when the PR is ready.
  Per task-212f1c82 the supervisor does **not** read this status, does
  **not** trigger merge-prep manually, and does **not** wait on it. Once
  the work-item PR is open, the supervisor halts at
  `ready_for_user_review` and the existing GHA pipeline runs
  asynchronously.

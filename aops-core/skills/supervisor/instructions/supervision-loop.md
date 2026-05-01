# The Supervision Loop

Active, interruptible supervision of an epic. The supervisor loops
through orient → act → checkpoint on every invocation. It might dispatch one
invocation, monitor the next, react to a failure on the third.

> **`polecat` not on PATH?** Dispatch examples below use bare `polecat`. In
> non-interactive shells (Bash tool, cron, CI, headless agent), the
> `polecat`/`pc` zsh alias is not loaded. Substitute the canonical form:
> `uv run --project $AOPS $AOPS/polecat/cli.py <args>`. See
> [[../SKILL.md#dispatch]] for the global note.

## The Loop

Every invocation:

1. **ORIENT** — Read the epic task file. Discover the environment. Determine
   what needs doing next.
2. **ACT** — Do the highest-priority thing: decompose, dispatch, check
   PRs, merge, react to a failure, escalate a decision.
3. **CHECKPOINT** — Write updated state to the epic task body. Commit and push
   so the next invocation (possibly on a different machine) can pick up.

That's it. The supervisor is not a pipeline — it's a loop that does one
useful thing per invocation and records what it did.

## Environment Discovery

Run on every invocation. Results are transient — the environment may change.

```bash
# What machine? What tools?
hostname; which polecat claude gemini gh docker pkb 2>/dev/null

# Can I reach things?
git ls-remote origin HEAD 2>/dev/null   # GitHub
pkb search "test" --limit 1 2>/dev/null  # PKB

# What repos are available?
ls $AOPS 2>/dev/null; ls $ACA_DATA 2>/dev/null

# What's running?
docker ps 2>/dev/null; polecat list 2>/dev/null
```

### Mandatory Host Check (issue #598)

**Before any DISPATCH phase action**, compare the current host against the
registered polecat host list. If the supervisor is NOT running on a polecat
host, it MUST use the SSH+tmux remote dispatch path — silent local
`polecat run` is forbidden.

See [[worker-dispatch#gate-1-host-check-issue-598]] for the canonical check snippet and exit conditions.

The supervisor records the host-check result in the task body's Activity
Log alongside the dispatch decision. A mismatch is not a failure — it is
the signal to switch to remote dispatch. The failure mode this prevents
is the macOS-laptop supervisor that reads "use SSH+tmux when on a different
host" but dispatches locally anyway, then loses tasks to
`ConnectionRefusedError` because the laptop can't reach PKB (issue #598).

Build a capability profile from discovery:

| Capability         | Check                 | Dispatch via            |
| ------------------ | --------------------- | ----------------------- |
| Local polecat      | `which polecat`       | `polecat run -t <id>`   |
| Container dispatch | `docker ps`           | `polecat crew`          |
| GitHub API         | `gh auth status`      | `gh pr`, GitHub Actions |
| PKB access         | `pkb search` or MCP   | task state management   |
| Remote triggers    | `claude trigger list` | async remote agents     |

Adapt dispatch strategy to what's actually available.

## Task File State Format

The supervisor maintains structured state in the epic task body. This is the
**only** persistent state.

```markdown
## Supervisor State

**Phase**: orienting | decomposing | dispatching | monitoring | integrating | complete
**Last checkpoint**: [ISO timestamp]
**Environment**: [where this supervisor ran]
**Feature Branch**: [branch-name] (PR #NNN, draft) | none

### Work Items

| # | ID       | Title       | Status      | Worker | PR   | Notes           |
| - | -------- | ----------- | ----------- | ------ | ---- | --------------- |
| 1 | task-abc | Fix widget  | done        | claude | #234 | merged 10:45    |
| 2 | task-def | Add tests   | merge_ready | gemini | #235 | CI passing      |
| 3 | task-ghi | Update docs | ready       | —      | —    | unblocked by #1 |

### Activity Log

[ISO timestamp] [environment]: [what the supervisor did]
```

### Work Item Statuses

The supervisor uses canonical PKB task statuses — see [[../../../remember/references/TAXONOMY.md#status-values-and-transitions]].

| Status                  | Meaning in the supervisor loop                                                                                                                                                                                                                             |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ready`                 | Decomposed, awaiting human approval (NOT dispatchable). Also the halt state when a plan-review gate fires — parent not yet queued; supervisor resumes on promotion.                                                                                        |
| `queued`                | Human-approved, dispatchable. Includes tasks waiting for a feature branch lock during coordinated dispatch (detected via the `feature_branch` field on siblings).                                                                                          |
| `in_progress`           | Dispatched to a worker, or worker executing — covers both the "sent, waiting for PR" and "actively working" phases                                                                                                                                         |
| `merge_ready`           | (Legacy.) PR filed — supervisor records and moves on. Per task-212f1c82 the supervisor's halt state is `ready_for_user_review`; the GHA mechanical merge-prep adds the `ready-for-review` label asynchronously and the user-side reviewer cron takes over. |
| `ready_for_user_review` | Work item has an open PR; handed off to the async pipeline. Supervisor's terminal state for the item.                                                                                                                                                      |
| `review`                | Requires human judgment — PR changes requested, review gate fired, or decision required before work can proceed. Supervisor does NOT dispatch.                                                                                                             |
| `done`                  | Merged and verified                                                                                                                                                                                                                                        |
| `blocked`               | Waiting on a dependency — will be unblocked automatically when the dependency transitions to `done`                                                                                                                                                        |
| `paused`                | Intentionally stopped; supervisor does not dispatch until human resumes                                                                                                                                                                                    |
| `cancelled`             | Abandoned; supervisor ignores                                                                                                                                                                                                                              |

**Coordinated dispatch (feature branch lock)**: When a task is `queued` but another
task holds the feature branch lock, leave it `queued` and skip dispatch. The branch
lock is a sibling-task property, not a separate status. When the lock-holder reaches
a terminal status (`done`, `merge_ready`, `cancelled`) or is reset by
`polecat reset-stalled`, the supervisor dispatches the next waiting `queued` item on
the next ORIENT tick. These tasks are NOT stale — only the actively dispatched
branch-locked task can go stale.

`review` is an enforceable gate — agents cannot claim tasks in this status.

## Verification, Not Interrogation

The supervisor NEVER asks the human to confirm factual state. That defeats
the purpose of automation. Instead:

1. **Verify independently** — check PKB task status, check GitHub PRs, check
   build artifacts, read task bodies for progress notes. If you can't verify
   something, that's an infrastructure gap to file a task about.

2. **Verification tasks as graph gates** — at important phase boundaries,
   create discrete verification subtasks (preferably for an independent agent)
   that check claims and assumptions BEFORE the next phase starts. These are
   real tasks with `depends_on` — the downstream work literally can't proceed
   until verification completes.

The human's role is judgment (methodology, priorities, academic decisions),
not fact-checking. Verification is execution — automate it.

## Phase Actions

### ORIENT

**Step 1: Verify state.** Read the epic task file. For each work item, **independently verify** current reality:

- Check PKB task status (not just what the work items table says — query live)
- Check child task status (a parent may be done if all children are done)
- If `in_progress`: check for PRs (`gh pr list --search "head:polecat/{id}"`)
- If a PR is open: that work item is done from the supervisor's perspective — mark it `ready_for_user_review` and stop tracking. Do NOT re-check CI / review state / merge status.
- Check git log for recent changes to task files

Update the work items table to match verified reality. Then decide what to do next.

### DECOMPOSE

Break the goal into PR-sized subtasks. Use the protocols in
[[decomposition-and-review]]. Create subtasks in PKB, add them to the
work items table.

Incremental decomposition is normal — add subtasks mid-flight when a worker
discovers something is bigger than expected.

### DISPATCH

1. Select ready work items
2. Run pre-dispatch validation (see [[worker-dispatch]]):
   - Target files still exist?
   - Task belongs in the right repo?
   - AC is implementable against current codebase?
3. Record dispatch in the task file BEFORE firing the worker
4. Fire the worker: `polecat run -t <id> -p <project>`
5. Update status to `in_progress`

### MONITOR

The supervisor's monitoring scope per task-212f1c82 is narrow: **wait for
each in_progress work item to open a PR, then halt**. CI status, reviewer
state, label transitions after `ready-for-review`, and merge are all
out-of-scope — owned by the GHA pipeline, the user-side reviewer cron, and
the daily-sweep CTA respectively.

Only two mechanisms are needed:

1. **Background polecat completion notifications.** Dispatch workers with
   `run_in_background: true` on the Bash tool call. The Bash tool emits an
   automatic notification when the background process exits.

   ```bash
   polecat run -t task-abc123 -p aops   # run_in_background: true
   ```

2. **One-shot PR check on worker exit.** When a worker finishes, do a single
   `gh pr list --search "head:polecat/<id>"` to confirm a PR was opened.
   That's it.

   | Outcome                 | Supervisor action                                                |
   | ----------------------- | ---------------------------------------------------------------- |
   | PR opened               | Record PR in work items; mark item ready_for_user_review         |
   | No PR + worker exit 0   | REACT: re-dispatch or escalate (worker may have hit a stop-cond) |
   | No PR + worker exit !=0 | REACT: read transcript, re-dispatch or file blocker              |

When all work items are in either state above (PR open or escalated), see
§ Halt at ready_for_user_review below.

#### Removed responsibilities (per task-212f1c82)

The supervisor MUST NOT do any of the following any more. They have moved
to the GHA pipeline (mechanical) or the user-side reviewer cron (judgment):

- Persistent PR-state Monitor watching CI / reviewer state across all branches.
- `gh run watch`, `gh pr view --json statusCheckRollup,reviews` polling loops.
- "Ready-to-advance" detection across the bot reviewer set.
- Manual `gh workflow run agent-merge-prep.yml` triggers.
- Reading `merge-prep-status` commit status.
- Reacting to `CHANGES_REQUESTED` reviews from the bazaar bots.
- `gh pr merge` of any kind.
- `polecat sync` after merging.

If a transcript shows the supervisor doing any of these against a PR that
has already been opened, that's a bug — the supervisor was supposed to
have halted.

#### Halt at ready_for_user_review

Once every work item is in a terminal supervisor state (PR open OR
escalated/blocked with a clear reason), the supervisor:

1. Updates the epic's work-items table; marks each open-PR item with
   state `ready_for_user_review`.
2. Emits the final-summary report (template in [[../SKILL.md#final-summary-template-one-report-per-epic]]).
3. Sets epic status appropriately and exits. No `ScheduleWakeup`, no
   re-orient, no follow-up tick on this epic.

The user-side reviewer cron at `dotfiles/cron/user-side-pr-review.sh`
will pick the PRs up via the GHA-applied `ready-for-review` label,
dispatch the rebuilt RBG judge agent (`aops-core/agents/rbg.md`), and
on PASS apply `approve-ready`. The next `/daily` surfaces them in one
CTA list. The supervisor is not part of that loop.

#### Reading Worker Completion Signals

Workers communicate back via two mechanisms:

1. **PKB task status change**: Worker calls `release_task` MCP method, which
   updates status and may append structured notes to the task body (decisions
   made, blockers hit, scope changes discovered).
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

#### Reading Polecat Stream Output (Don't Panic)

When streaming a polecat's stdout/stderr, expect a lot of noise that looks
catastrophic but isn't. Gemini workers in particular emit:

- "Failed to load API key from storage: Error: Corrupted credentials file detected…"
- "Policy file error in deny-extension-writes.toml / polecat-sandbox.toml"
- "Error executing tool mcp_pkb_release_task: Tool … not found. Did you mean…"
- "Hook system message: ▶ Task bound. Handover required before exit." repeated 20+ times

None of these are terminal. Workers with these warnings have still produced
clean PRs. **Do not halt the supervision on stream keywords.** The authoritative
terminal signals are:

- Worker process exits with non-zero status (background task notification)
- `polecat finish` output appears
- PR URL is posted to the stream ("PR's up: https://…")
- "Task updated" / "Mission accomplished" appears after a release_task call

If you read scary text but the process is still running and no terminal signal
has arrived, **keep waiting**. Filter your Monitor for terminal signals, not for
words like "Error" or "Corrupted". 2026-04-20 dogfood: supervisor nearly killed a
gemini polecat that was in fact seconds away from opening PR #640.

#### Polecat Lifecycle Signals

PKB status and PR state are the primary signals, but for ambiguous cases also
check the polecat lifecycle directly:

- **`polecat list`** — is the task's worktree still registered? Present =
  worker or auto-finish is still running. Absent = cleanup completed.
- **`docker ps`** — is the container still up? Long-running containers
  (>45 min for cycles that finished their work) often mean the CLI agent is
  looping post-handover, not still working. Cross-check against PKB status:
  if `status: done` but container still up, the worker has finished but isn't
  terminating cleanly.
- **Dispatch command output file** — when the supervisor backgrounded
  `polecat run`, its stdout is written to the background task's output file.
  Polecat writes lifecycle events at the end: `Agent completed successfully`,
  `Running auto-finish`, `Nuking worktree`, `Worktree removed`. If you see
  these, the run is fully wound down. **Do not check this file early** — it
  stays empty until polecat reaches its teardown phase. Check it only when
  you suspect the worker has finished.
- **Transcript** at `$POLECAT_HOME/polecats/<task-id>.jsonl` — written
  after the worker finishes; provides the full session log for evaluation.

#### Non-PR Work (PKB-only dispatches)

Not every dispatch produces a PR. Skills like `/sleep`, `/planner`, `/remember`
write directly to the PKB via MCP and never touch the worktree branch. For
these tasks:

- **Don't** check `gh pr list` — no PR will appear.
- **Don't** check the polecat worktree's git log for commits — the worktree
  may have zero commits even on a successful run.
- **Do** check `$ACA_DATA` (brain repo) `git log --since` for auto-sync
  commits that touch task/knowledge/project files, plus the task's body for
  worker-appended evidence.
- **Do** read the transcript if the brain-side signals are thin.

The dispatch task body is still the primary evidence surface — workers should
append a completion summary there before calling `release_task`.

#### Deep Evaluation via Transcripts

When a worker's output is surprising (unexpected scope, quality concerns, or
failure without clear cause), read the polecat transcript for deeper insight.

**Locating transcripts** (auto-generated by crontab running `transcript.py`):

- `$POLECAT_HOME/polecats/<task-id>.jsonl` — raw JSONL (primary)
- `$AOPS_SESSIONS/transcripts/` — generated markdown (uses session naming convention from PR #513)
- Legacy fallbacks checked by `find_polecat_transcript()`: `$AOPS_SESSIONS/polecats/`, `$AOPS_SESSIONS/transcripts/polecats/`

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

**Anti-pattern**: Reading every transcript. Only read when lightweight signals
(task status, PR diff, worker notes) are insufficient.

#### Deferred Verification Tracking

Any TDD fix that ships with tests the worker could not actually run
(Docker rebuild needed, credentialed service, long wall-clock, external API)
is **not verified** — it is inference. Before the epic can complete, each
unrunnable test becomes an explicit follow-up task, not a note in the PR body.

On MONITOR, for every work item whose report (see [[worker-dispatch]]
parallel dispatch report shape) lists deferred verification:

1. Create a child verification task under the same epic with:
   - Exact reproduce steps (command, env, expected result)
   - `depends_on` the PR that shipped the fix
   - `soft_blocks` the epic's COMPLETE transition
2. Link the task ID into the PR body under a `## Deferred verification` heading
3. Do not mark the epic complete until every deferred-verification task is
   `done` or explicitly accepted by the human as permanently manual

### REACT

| Problem                           | Response                                         |
| --------------------------------- | ------------------------------------------------ |
| Worker failed (no PR, task reset) | Re-dispatch, possibly different worker           |
| PR has merge conflicts            | Close PR, re-dispatch on fresh base              |
| PR got CHANGES_REQUESTED          | Read review comments, decide: fix or re-dispatch |
| Task bigger than expected         | Decompose further, add work items                |
| Dependency discovered             | Add depends_on, mark dependent as blocked        |
| Academic integrity concern        | Set task status to `review`, do not dispatch     |

### HALT (ready_for_user_review)

Replaces the old INTEGRATE + COMPLETE phases. The supervisor never merges
PRs and never waits for downstream review.

1. Confirm every work item has either an open PR or a documented
   escalation/blocker. If anything is still `in_progress` with no PR, see
   the MONITOR table above.
2. Update each open-PR work item to state `ready_for_user_review`.
3. Run knowledge capture ([[knowledge-capture]]) for in-flight learning,
   not as a completion gate.
4. File follow-up tasks for out-of-scope discoveries.
5. Emit the final-summary report (one per epic; see
   [[../SKILL.md#final-summary-template-one-report-per-epic]]).
6. Final checkpoint, exit.

PR merge happens later, async, gated by the user-side review cron and the
human's daily-sweep CTA. Task-completion-on-merge automation is owned by
the merged-PR action that parses the branch name; the supervisor is not
involved.

## Holding Work for Human Judgment

When a task requires human judgment before work can proceed (academic integrity
concern, methodology question, scope ambiguity), set the task status to
`review`.

This is an enforced gate. Agents cannot claim tasks in `review` status,
so the work is held without relying on anyone checking a body note.

```bash
# Hold a task for human decision
pkb update <task-id> --status review --note "Reason: <why human input needed>"
```

The supervisor will
skip these items during DISPATCH until the human resolves them by changing
the status back to `queued` (ready to dispatch).

## State Recovery

All supervisor state lives in the epic task file body. If the file is lost
or corrupted, recover from the nearest available source:

1. **Git log**: `git log --all -- <path-to-epic-task>` — prior versions of the
   task file are in git history.
2. **PKB search**: `pkb search "<epic title>"` — prior snapshots of the task
   may be indexed.
3. **Open PRs**: `gh pr list --search "head:polecat/"` — in-progress work items
   leave PRs as evidence.
4. **Child task status**: Query PKB for tasks with `parent: <epic-id>` to
   reconstruct the work items table.

Reconstruct the `## Supervisor State` block from these sources and checkpoint
before resuming.

## Concurrency

### Multiple Supervisors

**One epic = one supervisor session.** Running two supervisors on the same
epic concurrently is unsafe. Markdown table updates have no transaction
isolation — two supervisors can both read a task as `ready`, both dispatch it,
and the last-write-wins checkpoint will silently corrupt the work items table.

If you suspect another supervisor is active, check the epic task body's
`**Last checkpoint**` field and `git log -- <task-file>` before acting. Use a
session lock file (`epic-<id>.lock`) as a coordination signal if concurrent
sessions are likely.

When sessions do overlap, git is the backstop:

- Pull before acting. Push after checkpointing.
- If push fails → pull, re-orient, adjust.
- Idempotent actions mean the worst case is wasted work, not corruption.

### Worker Coordination

Workers coordinate through atomic task claiming (polecat CLI), not through
the supervisor. The supervisor doesn't prevent double-claiming — that's the
worker's job.

## Invocation Patterns

```bash
# Manual (current session)
# Just invoke /supervisor with the epic task ID

# Periodic (in-session loop)
/loop 30m /supervisor task-XXXXXXXX

# Scheduled task (survives session restarts)
# Use create_scheduled_task MCP tool

# Cron (via repo-sync or GitHub Actions)
pkb get task-XXXXXXXX | claude -p "You are the supervisor. Orient and act."
```

## Anti-Patterns

- **Polling for worker status**: Don't run `polecat list`, `gh pr list`, or
  read background output files on a short interval (every 4–5 min). Use
  event-driven monitoring instead (see MONITOR phase above). Polling 4
  concurrent workers every 5 minutes over a 30-minute session wastes
  hundreds of thousands of tokens on redundant context.
- **Tight polling loops**: Don't `watch` or `sleep` between checks. Check once,
  checkpoint, exit. Come back later.
- **Environment-specific state**: Don't write paths, PIDs, or container IDs into
  the task file. They won't be valid next invocation.
- **Silent failures**: If something breaks, write it into the task file. The next
  supervisor instance needs to know.
- **Delegating judgment**: If a work item involves academic output, methodology,
  or citations — set task status to `review`. Never auto-merge.

# The Supervision Loop

Active, interruptible supervision of an epic. The supervisor loops
through orient → act → checkpoint on every invocation. It might dispatch one
invocation, monitor the next, react to a failure on the third.

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

| Status        | Meaning in the supervisor loop                                                                                                                                      |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ready`       | Decomposed, awaiting human approval (NOT dispatchable). Also the halt state when a plan-review gate fires — parent not yet queued; supervisor resumes on promotion. |
| `queued`      | Human-approved, dispatchable. Includes tasks waiting for a feature branch lock during coordinated dispatch (detected via the `feature_branch` field on siblings).   |
| `in_progress` | Dispatched to a worker, or worker executing — covers both the "sent, waiting for PR" and "actively working" phases                                                  |
| `merge_ready` | PR filed / CI passing / awaiting merge — do not re-dispatch; merge-prep agent handles graduation and the human approves via the `production` Environment gate       |
| `review`      | Requires human judgment — PR changes requested, review gate fired, or decision required before work can proceed. Supervisor does NOT dispatch.                      |
| `done`        | Merged and verified                                                                                                                                                 |
| `blocked`     | Waiting on a dependency — will be unblocked automatically when the dependency transitions to `done`                                                                 |
| `paused`      | Intentionally stopped; supervisor does not dispatch until human resumes                                                                                             |
| `cancelled`   | Abandoned; supervisor ignores                                                                                                                                       |

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
- If `merge_ready`: check review/CI status
- Check git log for recent changes to task files
- Has anything been merged since last checkpoint?

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

#### Event-Driven Monitoring (Default)

The supervisor uses **event-driven monitoring** — not polling. Three
mechanisms deliver state changes without burning tokens:

1. **Background polecat completion notifications.** Dispatch workers with
   `run_in_background: true` on the Bash tool call. The Bash tool emits an
   automatic notification when the background process exits. No polling
   needed — the supervisor is interrupted when work finishes.

   ```bash
   # Dispatch in background — supervisor gets notified on exit
   polecat run -t task-abc123 -p aops   # run_in_background: true
   ```

2. **Persistent Monitor for PR state transitions.** A single Monitor
   watches all in-progress task branches and emits one event per state
   change. Start it once during DISPATCH, and it runs for the rest of the
   session.

   ```bash
   # Monitor PR state for all in-progress polecat branches
   while true; do
     for branch in $(git for-each-ref --format='%(refname:strip=3)' 'refs/remotes/origin/polecat/*'); do
       task_id=$(echo "$branch" | sed 's|polecat/||')
       pr_json=$(gh pr list --head "$branch" --json number,state,statusCheckRollup,reviews --limit 1 2>/dev/null)
       if [ "$pr_json" != "[]" ] && [ -n "$pr_json" ]; then
         pr_num=$(echo "$pr_json" | jq -r '.[0].number')
         pr_state=$(echo "$pr_json" | jq -r '.[0].state')
         checks=$(echo "$pr_json" | jq -r '.[0].statusCheckRollup // [] | map(.conclusion // .status) | join(",")')
         reviews=$(echo "$pr_json" | jq -r '.[0].reviews // [] | map(.state) | join(",")')
         state_key="${pr_state}|${checks}|${reviews}"
         state_file="/tmp/pr-state-${task_id}"
         prev=$(cat "$state_file" 2>/dev/null || echo "")
         if [ "$state_key" != "$prev" ]; then
           echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] ${task_id} PR#${pr_num}: state=${pr_state} checks=${checks} reviews=${reviews}"
           echo "$state_key" > "$state_file"
         fi
       fi
     done
     sleep 60
   done
   ```

   Use the Monitor tool to stream this — each printed line becomes a
   notification that wakes the supervisor. State transitions to watch for:

   | Transition                        | Supervisor action                    |
   | --------------------------------- | ------------------------------------ |
   | no-pr → opened                    | Record PR in work items              |
   | opened → checks-passing           | Wait for review                      |
   | checks-failing                    | REACT: read logs, re-dispatch or fix |
   | review: CHANGES_REQUESTED         | REACT: read comments                 |
   | review: APPROVED + checks-passing | INTEGRATE: merge                     |
   | merged                            | Update status → done                 |

3. **ScheduleWakeup as safety net only.** Set a long interval (1800s+) as
   a catch-all in case a notification is missed or a worker stalls without
   producing a signal. This is NOT the primary monitoring mechanism.

   ```
   ScheduleWakeup(delaySeconds=1800, reason="safety-net check for stalled workers")
   ```

#### Anti-Pattern: Polling

**Do not** poll `polecat list`, `gh pr list`, or read background output
files on a short interval (every 4–5 minutes). This burns tokens and
context window — especially when supervising 3–4 concurrent workers over
30+ minutes.

| Anti-pattern                              | Replacement                                 |
| ----------------------------------------- | ------------------------------------------- |
| `ScheduleWakeup(300s)` + `polecat list`   | `run_in_background` completion notification |
| `ScheduleWakeup(300s)` + `gh pr list`     | Persistent Monitor script (above)           |
| Repeated reads of background output files | Wait for background task notification       |

#### Fallback: One-Shot Check Per Invocation

If event-driven monitoring is not possible (e.g., resumed session,
different machine, no long-running Monitor), fall back to a single check
per invocation. For each `in_progress` / `merge_ready` item:

- Check PKB for status changes
- Check GitHub for PRs (`gh pr list`, `gh pr view`)
- Update the work items table

No active polling loops. Check once per invocation.

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

### INTEGRATE

1. Verify PR is clean (CI green, approved, no conflicts)
2. Merge: `gh pr merge <N> --squash --delete-branch`
3. Sync mirrors if available: `polecat sync`
4. Update work item: status → done
5. Check if this unblocks other work items → move to ready

### COMPLETE

All work items done:

1. Update parent task status
2. Run knowledge capture ([[knowledge-capture]])
3. File follow-up tasks for out-of-scope discoveries
4. Final checkpoint with summary

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

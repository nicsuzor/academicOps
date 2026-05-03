# The Supervision Loop

Active, interruptible supervision of an epic. The supervisor loops
through orient → act → checkpoint on every invocation. It might dispatch one
invocation, monitor the next, react to a failure on the third.

This file is **deliverable-agnostic**. Where it refers to "the review
surface", "completion signal", or "deliverable", the active deliverable
subworkflow supplies the concrete shape — for code deliverables, see
[[code-deliverable]].

## The Loop

Every invocation:

1. **ORIENT** — Read the epic task file. Discover the environment. Determine
   what needs doing next.
2. **ACT** — Do the highest-priority thing: decompose, dispatch, check
   the review surface, react to a failure, escalate a decision.
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

# What repos / artefact stores are available?
ls $AOPS 2>/dev/null; ls $ACA_DATA 2>/dev/null

# What workers are running?
docker ps 2>/dev/null; polecat list 2>/dev/null
```

Build a capability profile from discovery and adapt the dispatch transport
to whatever's available. The deliverable subworkflow sets the **target**
capabilities (e.g. for code: polecat + GitHub + PKB); discovery checks
whether each is reachable in this environment. Code-specific gates (host
check, PKB readiness probe) are documented in [[code-deliverable]].

## Task File State Format

The supervisor maintains structured state in the epic task body. This is the
**only** persistent state.

```markdown
## Supervisor State

**Phase**: orienting | decomposing | dispatching | monitoring | reacting | halted
**Last checkpoint**: [ISO timestamp]
**Environment**: [where this supervisor ran]
**Shared artefact**: [feature-branch-name / shared-doc-id] | none

### Work Items

| # | ID       | Title       | Status                | Worker | Review surface | Notes           |
| - | -------- | ----------- | --------------------- | ------ | -------------- | --------------- |
| 1 | task-abc | Fix widget  | done                  | claude | #234           | merged 10:45    |
| 2 | task-def | Add tests   | ready_for_user_review | gemini | #235           | open PR         |
| 3 | task-ghi | Update docs | ready                 | —      | —              | unblocked by #1 |

### Activity Log

[ISO timestamp] [environment]: [what the supervisor did]
```

The "Review surface" column holds whatever identifier the deliverable
subworkflow uses (e.g. PR number for code, document URL or revision id for
research deliverables).

### Work Item Statuses

The supervisor uses canonical PKB task statuses — see [[../../../remember/references/TAXONOMY.md#status-values-and-transitions]].

| Status                  | Meaning in the supervisor loop                                                                                                                                                                                                                                        |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ready`                 | Decomposed, awaiting human approval (NOT dispatchable). Also the halt state when a plan-review gate fires — parent not yet queued; supervisor resumes on promotion.                                                                                                   |
| `queued`                | Human-approved, dispatchable. Includes tasks waiting for a shared-artefact lock during coordinated dispatch (detected via the shared-artefact field on siblings).                                                                                                     |
| `in_progress`           | Dispatched to a worker, or worker executing — covers both the "sent, waiting for review surface" and "actively working" phases                                                                                                                                        |
| `merge_ready`           | (Legacy.) Code-only — deliverable filed at review surface; supervisor records and moves on. Per task-212f1c82 the supervisor's halt state is `ready_for_user_review`; the existing GHA pipeline (CI, enforcer, merge-prep, Environment approval) runs asynchronously. |
| `ready_for_user_review` | Work item has reached its review surface; handed off to the async pipeline. Supervisor's terminal state for the item.                                                                                                                                                 |
| `review`                | Requires human judgment — review gate fired or decision required before work can proceed. Supervisor does NOT dispatch.                                                                                                                                               |
| `done`                  | Finalised at the review surface and verified                                                                                                                                                                                                                          |
| `blocked`               | Waiting on a dependency — will be unblocked automatically when the dependency transitions to `done`                                                                                                                                                                   |
| `paused`                | Intentionally stopped; supervisor does not dispatch until human resumes                                                                                                                                                                                               |
| `cancelled`             | Abandoned; supervisor ignores                                                                                                                                                                                                                                         |

**Coordinated dispatch (shared-artefact lock)**: When a task is `queued` but
another task holds the shared-artefact lock (e.g. a feature branch in the
code case), leave it `queued` and skip dispatch. The lock is a sibling-task
property, not a separate status. When the lock-holder reaches a terminal
status (`done`, `merge_ready`, `cancelled`) or is reset by
`polecat reset-stalled` (or the deliverable subworkflow's equivalent), the
supervisor dispatches the next waiting `queued` item on the next ORIENT
tick. These tasks are NOT stale — only the actively dispatched
lock-holding task can go stale.

`review` is an enforceable gate — agents cannot claim tasks in this status.

## Verification, Not Interrogation

The supervisor NEVER asks the human to confirm factual state. That defeats
the purpose of automation. Instead:

1. **Verify independently** — check PKB task status, check the review
   surface, check build/produced artefacts, read task bodies for progress
   notes. If you can't verify something, that's an infrastructure gap to
   file a task about.

2. **Verification tasks as graph gates** — at important phase boundaries,
   create discrete verification subtasks (preferably for an independent
   agent) that check claims and assumptions BEFORE the next phase starts.
   These are real tasks with `depends_on` — the downstream work literally
   can't proceed until verification completes.

The human's role is judgment (methodology, priorities, academic decisions),
not fact-checking. Verification is execution — automate it.

## Phase Actions

### ORIENT

**Step 1: Verify state.** Read the epic task file. For each work item,
**independently verify** current reality:

- Check PKB task status (not just what the work items table says — query live)
- Check child task status (a parent may be done if all children are done)
- If `in_progress`: check whether the deliverable has reached the review
  surface (per the active subworkflow — for code, see
  [[code-deliverable#monitor-wait-for-the-pr-then-halt]])
- If at the review surface: that work item is done from the supervisor's
  perspective — mark it `ready_for_user_review` and stop tracking. Do NOT
  re-check downstream review/verification state.
- Check git log for recent changes to task files

Update the work items table to match verified reality. Then decide what to do next.

### DECOMPOSE

Break the goal into review-sized subtasks. Use the protocols in
[[decomposition-and-review]]. Create subtasks in PKB, add them to the
work items table.

Incremental decomposition is normal — add subtasks mid-flight when a worker
discovers something is bigger than expected.

### DISPATCH

1. Select ready work items
2. Run pre-dispatch validation (see [[worker-dispatch]] for universal
   gates and [[code-deliverable#mandatory-pre-dispatch-gates]] for the
   code-specific ones):
   - Target artefacts still exist?
   - Task belongs in the right scope/repo?
   - AC is implementable against the current state?
3. Record dispatch in the task file BEFORE firing the worker
4. Fire the worker via the deliverable subworkflow's dispatch shape
5. Update status to `in_progress`

### MONITOR

The supervisor's monitoring scope per task-212f1c82 is narrow: **wait for
each in_progress work item to reach its review surface, then halt**.
Downstream review state, verification labels, and finalisation are
out-of-scope — owned by the async review pipeline defined by the
deliverable subworkflow.

For code deliverables, the concrete monitoring mechanisms (background
worker exit notifications, one-shot `gh pr list` checks on worker exit,
removed responsibilities like `gh run watch` / `gh pr merge`) are in
[[code-deliverable#monitor-wait-for-the-pr-then-halt]].

The universal monitoring contract is:

| Outcome                       | Supervisor action                                                |
| ----------------------------- | ---------------------------------------------------------------- |
| Deliverable at review surface | Record locator in work items; mark item `ready_for_user_review`  |
| Worker exit, no deliverable   | REACT: re-dispatch or escalate (worker may have hit a stop-cond) |
| Worker error exit             | REACT: read transcript / logs, re-dispatch or file blocker       |

When all work items are in either state above (at review surface or
escalated), see § Halt at ready_for_user_review below.

#### Halt at ready_for_user_review

Once every work item is in a terminal supervisor state (deliverable at
review surface OR escalated/blocked with a clear reason), the supervisor:

1. Updates the epic's work-items table; marks each surfaced item with
   state `ready_for_user_review`.
2. Emits the final-summary report (template lives in the deliverable
   subworkflow — for code, see
   [[code-deliverable#final-summary-template-one-report-per-epic]]).
3. Sets epic status appropriately and exits. No `ScheduleWakeup`, no
   re-orient, no follow-up tick on this epic.

The async review pipeline then takes over per the deliverable
subworkflow. The supervisor is not part of that loop.

#### Reading Worker Completion Signals

Workers communicate back via two universal mechanisms:

1. **PKB task status change**: Worker calls `release_task` MCP method,
   which updates status and may append structured notes to the task body
   (decisions made, blockers hit, scope changes discovered).
2. **Deliverable surfacing**: Worker emits the deliverable on its review
   surface (PR creation for code; document submission, draft commit, or
   equivalent for other deliverable types).

During MONITOR, read BOTH:

- Query PKB: `mcp__pkb__get_task(<task-id>)` — check `status` AND read
  the task body for worker-appended notes.
- Check the review surface (per the deliverable subworkflow).

Use worker notes to update the work items table, decide whether the task
truly needs follow-up, and inform subsequent task specs with lessons
learned. Code-specific guidance on reading polecat stream output,
lifecycle signals, transcripts, and deferred verification tracking lives
in [[code-deliverable#reading-worker-completion-signals]].

### REACT

| Problem                         | Response                                         |
| ------------------------------- | ------------------------------------------------ |
| Worker failed (no deliverable)  | Re-dispatch, possibly different worker           |
| Deliverable conflicts with base | Close/withdraw, re-dispatch on fresh base        |
| Reviewer requested changes      | Read review comments, decide: fix or re-dispatch |
| Task bigger than expected       | Decompose further, add work items                |
| Dependency discovered           | Add depends_on, mark dependent as blocked        |
| Academic integrity concern      | Set task status to `review`, do not dispatch     |

### HALT (ready_for_user_review)

Replaces the old INTEGRATE + COMPLETE phases. The supervisor never
finalises the deliverable itself and never waits for downstream review.

1. Confirm every work item has either reached its review surface or has a
   documented escalation/blocker. If anything is still `in_progress` with
   nothing at the review surface, see the MONITOR table above.
2. Update each surfaced work item to state `ready_for_user_review`.
3. Run knowledge capture ([[knowledge-capture]]) for in-flight learning,
   not as a completion gate.
4. File follow-up tasks for out-of-scope discoveries.
5. Emit the final-summary report (one per epic; template lives in the
   deliverable subworkflow).
6. Final checkpoint, exit.

Finalisation happens later, async, gated by the review pipeline that the
deliverable subworkflow defines.

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

The supervisor will skip these items during DISPATCH until the human
resolves them by changing the status back to `queued` (ready to dispatch).

## State Recovery

All supervisor state lives in the epic task file body. If the file is lost
or corrupted, recover from the nearest available source:

1. **Git log**: `git log --all -- <path-to-epic-task>` — prior versions of the
   task file are in git history.
2. **PKB search**: `pkb search "<epic title>"` — prior snapshots of the task
   may be indexed.
3. **In-flight deliverables**: query the active review surface for
   work-in-progress evidence (for code: `gh pr list --search "head:polecat/"`).
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

Workers coordinate through atomic task claiming, not through the
supervisor. The supervisor doesn't prevent double-claiming — that's the
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

- **Polling for worker status**: Don't poll the review surface or worker
  registry on a short interval (every 4–5 min). Use event-driven monitoring
  instead (see MONITOR phase above and the deliverable subworkflow).
  Polling 4 concurrent workers every 5 minutes over a 30-minute session
  wastes hundreds of thousands of tokens on redundant context.
- **Tight polling loops**: Don't `watch` or `sleep` between checks. Check once,
  checkpoint, exit. Come back later.
- **Environment-specific state**: Don't write paths, PIDs, or container IDs into
  the task file. They won't be valid next invocation.
- **Silent failures**: If something breaks, write it into the task file. The next
  supervisor instance needs to know.
- **Delegating judgment**: If a work item involves academic output, methodology,
  or citations — set task status to `review`. Never auto-finalise.

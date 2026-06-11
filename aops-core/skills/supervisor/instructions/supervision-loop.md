# The Supervision Loop

Operational detail for the per-tick loop defined in [[../SKILL.md]]. The main agent runs ORIENT → BRAKE → DECIDE → ACT → CHECKPOINT once and exits; this file documents the data each step reads and writes.

This file is **deliverable-agnostic**. Where it refers to "the review surface", "completion signal", or "deliverable", the active deliverable subworkflow supplies the concrete shape — for code deliverables, see [[code-deliverable]].

## Task File State Format

The supervisor maintains structured state in the epic body. This is the **only** persistent state.

```markdown
## Supervisor State

**Phase**: orienting | decomposing | dispatching | verifying | reacting | halted
**Last checkpoint**: [ISO timestamp]
**Environment**: [where this supervisor ran]
**Shared artefact**: [feature-branch-name / shared-doc-id] | none

### Work Items

| # | ID       | Title       | Status      | Worker | Review surface | Notes           |
| - | -------- | ----------- | ----------- | ------ | -------------- | --------------- |
| 1 | task-abc | Fix widget  | done        | claude | #234           | merged 10:45    |
| 2 | task-def | Add tests   | merge_ready | gemini | #235           | open PR         |
| 3 | task-ghi | Update docs | ready       | —      | —              | unblocked by #1 |

## Pattern Memory

| Tick (ISO)           | Decision                    | Class       | Notes               |
| -------------------- | --------------------------- | ----------- | ------------------- |
| 2026-05-08T02:14:00Z | dispatch task-abc to claude | dispatch_ok | preflight clean     |
| 2026-05-08T02:43:11Z | marsha FAIL on task-abc     | verify_fail | tests red on docker |

### Activity Log

[ISO timestamp] [environment]: [what the supervisor did]
```

The "Review surface" column holds whatever identifier the deliverable subworkflow uses (PR number for code; document URL for research deliverables).

`## Pattern Memory` is the brake's input — capped at 16 rows (drop oldest). Class names are stable: `dispatch_ok`, `dispatch_halt`, `verify_pass`, `verify_fail`, `react_filed_fix`, `react_halt`, `brake_fired`. See [[../SKILL.md#pattern-memory-format]].

### Work Item Statuses

The supervisor uses canonical PKB task statuses — see [[../../../remember/references/TAXONOMY.md#status-values-and-transitions]].

| Status        | Meaning in the supervisor loop                                                                                  |
| ------------- | --------------------------------------------------------------------------------------------------------------- |
| `ready`       | Decomposed, awaiting human approval. Plan-review halt state — supervisor resumes only on promotion to `queued`. |
| `queued`      | Human-approved, dispatchable. Includes tasks waiting for a shared-artefact lock during coordinated dispatch.    |
| `in_progress` | Dispatched to a worker, or worker executing                                                                     |
| `merge_ready` | Work item has reached its review surface; handed off to the async pipeline. Supervisor terminal state.          |
| `review`      | Requires human judgment — supervisor does NOT dispatch.                                                         |
| `done`        | Finalised at the review surface and verified                                                                    |
| `blocked`     | Waiting on a dependency — unblocked when the dependency transitions to `done`                                   |
| `paused`      | Intentionally stopped; supervisor does not dispatch until human resumes                                         |
| `cancelled`   | Abandoned                                                                                                       |

`review` is an enforceable gate — agents cannot claim tasks in this status.

**Coordinated dispatch (shared-artefact lock / shared branch)**:

- **Shared-Branch Cohesive-Epic (Default)**: Sibling tasks on the shared branch do **NOT** lock each other. If they are parallel-able units (no inter-dependencies), they can and should be dispatched concurrently on the same shared branch (`polecat/epic-<epic-id>`). The polecat manager coordinates concurrent updates via cooperative pull-rebases.
- **Standalone Coordinated Dispatch**: For non-shared branches, when a task is `queued` but a sibling holds the shared-artefact lock (e.g. a feature branch), leave it `queued` and skip dispatch. The lock is a sibling-task property, not a separate status. The supervisor dispatches the next waiting `queued` item on the next ORIENT pass once the lock-holder reaches a terminal status or is reset by `polecat reset-stalled`.

## Verification, Not Interrogation

The supervisor NEVER asks the human to confirm factual state. That defeats the purpose of automation. Instead:

1. **Verify independently** — pauli (preflight) and marsha (verify) check PKB task status, the review surface, and produced artefacts.
2. **Verification subtasks as graph gates** — at important phase boundaries, create discrete verification subtasks (preferably for an independent agent) that check claims and assumptions BEFORE the next phase starts. These are real tasks with `depends_on`.

The human's role is judgment (methodology, priorities, academic decisions), not fact-checking.

## On-Demand Worker Observability Refresh

Worker transcript observability is maintained by a background cron job that distills polecat JSONLs into markdown (`$AOPS_SESSIONS/transcripts/`). To close the latency gap (0–5 minutes) during active supervision, the main agent MUST trigger an on-demand refresh when fresh state is needed.

**Invocation:**

```bash
AOPS_SESSIONS=$ACA_DATA/sessions uv run --project $AOPS python $AOPS/aops-core/scripts/transcript.py --recent
```

**When to invoke:**

- During the **REACT** phase when worker state is suspected to be stale or a stall is detected.
- Before delegating a peek to marsha (or other delegates) to ensure they have access to the most recent worker activity.

**Invariant (Write-Only Operation):**
This refresh is strictly a **write operation** (regenerating markdown from JSONL). The main supervisor agent _triggers_ the refresh, but **must never read the transcript output itself**. Reading the transcripts remains strictly delegated to marsha or pauli as part of their normal contract. This preserves the invariant that the main agent never reads transcripts directly. See [[kb-d8f58167]] (Session Log Observability Map) for the full pipeline context.

## Phase Actions

### ORIENT

The main agent reads `mcp__pkb__get_task(<epic-id>)` and the epic body's `## Work Items`, `## Pattern Memory`, and `## Supervisor State` blocks. **No other reads.** No grep, no child task body fetches, no transcript reads.

For each work item, status comes from the epic's table — not from per-task `get_task` calls. If a status is stale, the next `dispatch` or `verify` tick will surface it.

### DECOMPOSE

Pauli's job. Use the protocols in [[decomposition-and-review]]. Pauli proposes subtasks; the main agent files them via PKB and adds them to the work items table.

Incremental decomposition is normal — pauli may add subtasks mid-flight when a worker discovers something is bigger than expected.

### DISPATCH

Pauli returns `{action: "dispatch", ...}`. The main agent runs the single Bash command pauli supplied, updates status to `in_progress`, appends a Pattern Memory row.

Pauli has already verified pre-dispatch gates (host check, ping-pkb, 4-row pre-flight) — see [[worker-dispatch]] for the gate definitions pauli reads.

### VERIFY

Verification depends on the task context:

- **Standalone Tasks / Cumulative Final PR**: Trigger Marsha's job. Triggered when a work item is `in_progress` and the worker has exited (background task notification, PR appeared, polecat finish output). Pass marsha the work item ID, the review surface (PR URL or "none"), and the AC. Consume her structured verdict per [[../SKILL.md#marsha--verify]]. Before marking done, run the completeness check in [[verify#completeness-verification-heuristic]]: (a) freshness (b) completeness (c) limitations.
- **Intermediate Tasks on Shared Branch**: Perform local outcome-based verification without invoking Marsha — see [[code-deliverable#monitor-wait-for-the-pr-then-halt]] for the exact steps and outcome transitions.

For code deliverables, the concrete monitoring mechanisms (background worker exit notifications, one-shot `gh pr list`) are in [[code-deliverable#monitor-wait-for-the-pr-then-halt]].

### REACT

Pauli's job. Triggered when marsha returns FAIL, a worker exits non-zero (`worker-failed`), an intermediate task's local verification fails (`verification-failed`), or a worker exits with no deliverable. Pass pauli `role=react` plus the failure context.

Pauli returns one of:

| Pauli verdict   | Main agent action                                   |
| --------------- | --------------------------------------------------- |
| `dispatch`      | Pauli decided a re-dispatch is appropriate; fire it |
| `file_fix_task` | Create the fix-task via PKB; add to work items      |
| `halt`          | Set epic status; append reason; exit                |

The main agent never decides the fix shape. If pauli's verdict is malformed, append "pauli verdict malformed" and exit.

### HALT (merge_ready)

Once every work item is in a terminal supervisor state (deliverable at review surface OR escalated/blocked), the supervisor:

1. Updates the epic's work-items table; marks each surfaced item `merge_ready`.
2. Emits the final-summary report (template lives in the deliverable subworkflow — for code, see [[code-deliverable#final-summary-template-one-report-per-epic]]).
3. Sets epic status appropriately and exits. No `ScheduleWakeup`, no re-orient, no follow-up tick on this epic.

The async review pipeline then takes over per the deliverable subworkflow.

## Holding Work for Human Judgment

When a task requires human judgment before work can proceed (academic integrity concern, methodology question, scope ambiguity), set the task status to `review`. This is an enforced gate — agents cannot claim tasks in `review`, so the work is held without relying on anyone checking a body note.

```bash
pkb update <task-id> --status review --note "Reason: <why human input needed>"
```

The supervisor skips these items during DISPATCH until the human resolves them by changing status back to `queued`.

## State Recovery

All supervisor state lives in the epic body. If the file is lost or corrupted, recover from the nearest available source:

1. **Git log**: `git log --all -- <path-to-epic-task>` — prior versions are in git history.
2. **PKB search**: `pkb search "<epic title>"` — prior snapshots may be indexed.
3. **In-flight deliverables**: `gh pr list --search "head:polecat/"` for code; equivalent for other surfaces.
4. **Child task status**: query PKB for tasks with `parent: <epic-id>`.

Reconstruct the `## Supervisor State`, `## Work Items`, and `## Pattern Memory` blocks before resuming.

## Concurrency

**One epic = one supervisor session.** Running two supervisors on the same epic concurrently is unsafe — markdown table updates have no transaction isolation. If you suspect another supervisor is active, check the epic body's `**Last checkpoint**` field and `git log -- <task-file>` before acting. When sessions overlap, git is the backstop: pull before acting, push after checkpointing; idempotent actions mean the worst case is wasted work, not corruption.

Workers coordinate through atomic task claiming, not through the supervisor.

## Monitoring Mechanisms

The supervisor never polls. State changes arrive through one of four event sources; choose by the lifetime and signal shape needed.

| Mechanism                                              | Lifetime       | Signal                             | When to use                                                                                                    |
| ------------------------------------------------------ | -------------- | ---------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Background-task completion (`Bash run_in_background`)  | Per task       | One Bash command exited            | Single dispatched worker; one outcome needed                                                                   |
| Persistent `Monitor` on review-surface poll            | Session-length | PR check status flipped            | Async review-pipeline state (CI, mergeability)                                                                 |
| Persistent `Monitor` on `docker events` (notify-watch) | Session-length | One line per worker container exit | **In-session batch with concurrency cap** — see [[../SKILL.md#in-session-multi-tick-supervision-notify-watch]] |
| `ScheduleWakeup`                                       | One-shot       | Time-based wake                    | Safety net only when no event source exists; ≥1800s, never 300s                                                |

The notify-watch is the in-session counterpart to `/loop`. `/loop` paces across sessions on a 30 min cadence; the notify-watch paces within one session on the worker-exit cadence. Both ultimately drive the same per-tick loop (ORIENT → BRAKE → DECIDE → ACT → CHECKPOINT) — they only differ in what fires the next tick.

Operational notes for the notify-watch:

- **Arm immediately after the first dispatch that fills a slot.** Arming before any dispatch is harmless but wastes the watch on no-op events.
- **Each event is one notification, not one action.** The agent reacts by running a normal tick; it does NOT auto-dispatch from inside the watch script.
- **Filter crew sessions.** Crew containers share the `polecat-` name prefix. Skip events where the container env has `POLECAT_CREW_NAME` set (a crew session; run workers do not set it — look up via `docker inspect` on the exit) or refine the watch's `--filter` to match the in-use task-naming pattern.
- **Stop the watch when done.** `TaskStop` on the Monitor when the batch is complete; a leaked persistent Monitor keeps emitting notifications across unrelated work.

## Anti-Patterns

- **Polling for worker status**: don't poll the review surface every few minutes. Use one of the event-driven mechanisms above.
- **Bash polling loops as a substitute for supervision (nicsuzor/academicOps#942)**: `while true; do polecat run -g; sleep N; done` is not supervision — it carries no preflight, no verify, no react. The notify-watch (`docker events`) carries _signal_; every dispatch and verify still goes through pauli/marsha.
- **Tight polling loops**: don't `watch` or `sleep` between checks within a tick. Check once, checkpoint, exit. The next event-fired tick comes back later.
- **Environment-specific state**: don't write paths, PIDs, or container IDs into the epic body. They won't be valid next tick.
- **Silent failures**: if something breaks, append a Pattern Memory row. The next tick needs to know.
- **Delegating judgment**: if a work item involves academic output, methodology, or citations — set the task to `review`. Never auto-finalise.

---
name: reconcile
description: Truth maintenance over the task graph--establish ground truth for in-flight and completed work, write verified facts back, and return affected tasks to inbox for re-planning. Does not certify completion by judgment, re-plan, prune, or score.
---

# Reconcile

Establish ground truth across the task graph. Record verified external facts--merged pull requests, dead sessions, deleted referents, and recorded reviewer decisions--and return invalidated work to `inbox`.

## Protocol

### 1. Load Graph Claims

Query non-terminal tasks using `mcp__plugin_pkb_services__pkb__list_tasks`. Query narrow slices by status or project rather than pulling the full graph at once. Read the claimed assignee and session.

### 2. Probe Suspect Claims

A claim with no recent updates is suspect. Probe task writes, branch commits, and PR activity:

- **Active**: Leave claim intact.
- **Abandoned**: Reset status to `ready` (never `queued`, never cancel). Annotate the previous holder, timestamp, and probed targets.

### 3. Fold in Finished PRs

Examine pull requests closed within the specified time window. Match to tasks by: (1) task `pr_url`, (2) task ID in PR body, (3) matching branch name, (4) `polecat/*` branch prefix, or (5) exact title match.

- **Merged**: Record PR URL, merge date, and branch. Inspect acceptance criteria:
  - All criteria met: Set status to `done`.
  - Work mooted or settled: Cancel on evidence (§5).
  - Unfulfilled criteria: Leave open, quote missing criteria, and return to `inbox` (§7).
- **Closed unmerged**: Route per §4.
- **Backstop**: Sweep `merge_ready` (resolve against PR) and `review` (parked on human decision; never auto-close).

### 4. Route Closed Unmerged PRs

Classify using reviewer comments and labels:

| Class                | Signal                              | Action                                                                                 |
| -------------------- | ----------------------------------- | -------------------------------------------------------------------------------------- |
| `wontfix`            | Objective rejected or superseded    | Cancel task (or complete if superseded by sibling); record reviewer reason.            |
| `bad-implementation` | Rejected approach, rework requested | Invoke `/aops:q` to reposition task under same parent to `inbox` with failure context. |
| `retry-as-is`        | Transient infrastructure failure    | Return to `inbox` with rationale.                                                      |

### 5. Staleness, Rot, and Cancellation

- **Aged tasks (>90 days)**: Check sent mail, commits, or calendar for completion evidence. If conclusive (`confidence: high`, `settles: true`), mark complete with evidence; otherwise flag for human review. Never cancel on age alone.
- **Artifact rot (>14 days in `ready`/`queued`)**: Verify that named paths and symbols exist. Verified deletion cancels the task; missing or relocated paths demote to `inbox`.
- **World-fact cancellation**: Cancel only when:
  1. _Referent destroyed_: Path or interface was deleted across all relevant refs and checkouts (not merely moved).
  2. _Superseded by merge_: A merged PR settled the objective (§3).
  3. _Premise falsified_: An explicit precondition or assumption no longer holds.
- **Evidence required**: Write the specific audit trail (commit, PR, quoted assumption, or verified ref) into the node body.

#### Two-Step Mutation Contract

Every status demotion or cancellation must follow this order:

1. **Body**: Write evidence/annotation via `pkb__update_body` or `pkb__append`.
2. **Status**: Update frontmatter status via `pkb__update_task(id="<id>", updates={"status": "inbox"|"cancelled"})`. Never use `pkb__batch_update` for status changes.
3. **Readback**: Call `pkb__get_task` to confirm frontmatter status persisted.

### 6. Route Completed-but-Uncertified

Identify tasks marked `done` during the window lacking certification verdicts. Do not certify them yourself; forward them to the dispatcher for review.

### 7. Demote Affected Dependents to Inbox

Collect tasks affected by completed work, falsified assumptions, or cancellations:

- Unblocked `depends_on` dependents and live siblings.
- Tasks whose assumptions were tested by completed probes.
- Tasks demoted for artifact rot or repositioned by §4.

Set their status to `inbox` via the two-step mutation contract.

### 8. Emit Result

Return a single structured summary:

- Decisions requiring human attention.
- Completed, demoted, and requeued task IDs.
- Cancellations grouped by trigger with cited evidence.
- Tasks returned to `inbox`.
- Covered window and recommended next sweep targets.

## Must Not

- Certify completion based on subjective judgment or relay unverified worker self-reports.
- Cancel or complete tasks based solely on age, quietness, or duplication.
- Cancel without writing auditable evidence to the node body.
- Update task bodies without updating frontmatter status via `pkb__update_task`.
- Use `pkb__batch_update` for status changes.
- Write `focus_score`, `intent`, `priority`, or `severity`.
- Promote tasks into `queued`.
- Re-plan, prune, or second-guess recorded human decisions.

---
name: reconcile
description: Truth maintenance over the task graph--establish ground truth for in-flight and completed work, write verified facts back, and return affected tasks to inbox for re-planning. Sole writer of `done`, set only on an observed merged pull request. Does not certify completion by judgment, re-plan, reset stale claims, forward uncertified work to the dispatcher, or prune outside a ratified graph-hygiene rule set.
---

# Reconcile

Establish ground truth across the task graph. Record verified external facts--merged pull requests, dead sessions, deleted referents, and recorded reviewer decisions--and return invalidated work to `inbox`. `/reconcile` is the sole writer of `done` and writes it only on observing a merged pull request -- never on judged acceptance criteria, non-PR completion evidence, or a worker's self-report.

## Protocol

### 1. Load Graph Claims

Query non-terminal tasks using `mcp__plugin_pkb_services__pkb__list_tasks`. Query narrow slices by status or project rather than pulling the full graph at once.

### 2. Fold in Finished PRs

Examine pull requests closed within the specified time window. Match to tasks by: (1) task `pr_url`, (2) task ID in PR body, (3) matching branch name, (4) `polecat/*` branch prefix, or (5) exact title match.

- **Merged**: Record PR URL, merge date, and branch. Set status to `done`. This is the only condition under which reconcile writes `done` -- do not inspect acceptance criteria, judge completeness, or leave the task open pending review; that judgment is Sara's, before merge, not reconcile's after it.
- **Closed unmerged**: Route per §3.
- **Backstop**: Sweep `merge_ready` -- if its PR is in fact merged, set `done`; otherwise leave it for Sara. Sweep `review` for a merged PR only; never resolve `review` any other way -- it stays parked on Sara's or a human decision.

### 3. Route Closed Unmerged PRs

Classify using reviewer comments and labels:

| Class                | Signal                              | Action                                                                                 |
| -------------------- | ----------------------------------- | -------------------------------------------------------------------------------------- |
| `wontfix`            | Objective rejected or superseded    | Cancel task (or complete if superseded by sibling); record reviewer reason.            |
| `bad-implementation` | Rejected approach, rework requested | Invoke `/aops:q` to reposition task under same parent to `inbox` with failure context. |
| `retry-as-is`        | Transient infrastructure failure    | Return to `inbox` with rationale.                                                      |

### 4. Staleness, Rot, and Cancellation

- **Aged tasks (>90 days)**: Check sent mail, commits, or calendar for completion evidence. If conclusive (`confidence: high`, `settles: true`), record the evidence and set status to `review` for Sara's disposition -- reconcile does not set `done` on anything but an observed merge (§2). Otherwise flag for human review. Never cancel on age alone.
- **Artifact rot (>14 days in `ready`/`queued`)**: Verify that named paths and symbols exist. Verified deletion cancels the task; missing or relocated paths demote to `inbox`.
- **World-fact cancellation**: Cancel only when:
  1. _Referent destroyed_: Path or interface was deleted across all relevant refs and checkouts (not merely moved).
  2. _Superseded by merge_: A merged PR settled the objective (§2).
  3. _Premise falsified_: An explicit precondition or assumption no longer holds.
- **Evidence required**: Write the specific audit trail (commit, PR, quoted assumption, or verified ref) into the node body.

#### Two-Step Mutation Contract

Every status demotion or cancellation must follow this order:

1. **Body**: Write evidence/annotation via `pkb__update_body` or `pkb__append`.
2. **Status**: Update frontmatter status via `pkb__update_task(id="<id>", updates={"status": "inbox"|"cancelled"})`. Never use `pkb__batch_update` for status changes.
3. **Readback**: Call `pkb__get_task` to confirm frontmatter status persisted.

### 5. Demote Affected Dependents to Inbox

Collect tasks affected by completed work, falsified assumptions, or cancellations:

- Unblocked `depends_on` dependents and live siblings.
- Tasks whose assumptions were tested by completed probes.
- Tasks demoted for artifact rot or repositioned by §3.

Set their status to `inbox` via the two-step mutation contract.

### 6. Emit Result

Return a single structured summary:

- Decisions requiring human attention.
- Completed and demoted task IDs.
- Cancellations grouped by trigger with cited evidence.
- Tasks returned to `inbox`.
- Covered window and recommended next sweep targets.

## Must Not

- Certify completion based on subjective judgment or relay unverified worker self-reports.
- Set `done` on anything but an observed merged pull request (§2) -- never on judged acceptance criteria, non-PR completion evidence, or a worker's self-report.
- Reset stale or abandoned claims, or forward completed-but-uncertified work to the dispatcher -- both are Sara's outcomes (`partial`, `merge_ready`, `review`, or back to `queued`).
- Cancel or complete tasks based solely on age, quietness, or duplication.
- Cancel without writing auditable evidence to the node body.
- Update task bodies without updating frontmatter status via `pkb__update_task`.
- Use `pkb__batch_update` for status changes.
- Write `focus_score`, `intent`, `priority`, or `severity`.
- Promote tasks into `queued`.
- Re-plan or second-guess recorded human decisions.
- Prune or consolidate nodes outside a ratified rule set under [[aops_graph_hygiene_route]].

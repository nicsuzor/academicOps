---
name: reconcile
description: Truth maintenance over the task graph--establish ground truth for in-flight and completed work, write verified facts back, and return affected tasks to inbox for re-planning. Sole writer of `done`, set only on an observed merged pull request. Harvests durable knowledge from tasks it sets `done` and deletes them outright once the harvest is verified readable at its destination, and merges open near-duplicate tasks under the consolidation guard -- both on the ratified rule sets in [[kb_graph_hygiene_rules]], with no per-batch sign-off ([[kb_clean_first_git_recovery]]). Does not certify completion by judgment, re-plan, reset stale claims, forward uncertified work to the dispatcher, or prune outside a ratified graph-hygiene rule set.
---

# Reconcile

Establish ground truth across the task graph. Record verified external facts--merged pull requests, dead sessions, deleted referents, and recorded reviewer decisions--and return invalidated work to `inbox`. `/reconcile` is the sole writer of `done` and writes it only on observing a merged pull request -- never on judged acceptance criteria, non-PR completion evidence, or a worker's self-report.

## Protocol

Every `pkb.<op>(...)` call below runs through the `services` MCP server's code-mode interface (`listToolFiles` → `readToolFile("servers/pkb.pyi")` → `executeToolCode`), not a directly-invocable flat tool.

### 1. Load Graph Claims

Query non-terminal tasks using `pkb.list_tasks` (the `services` MCP server's code-mode interface: `listToolFiles` → `readToolFile("servers/pkb.pyi")` → `executeToolCode`). Query narrow slices by status or project rather than pulling the full graph at once.

### 2. Fold in Finished PRs

Examine pull requests closed within the specified time window. Match to tasks by: (1) task `pr_url`, (2) task ID in PR body, (3) matching branch name, (4) `polecat/*` branch prefix, or (5) exact title match.

- **Merged**: Record PR URL, merge date, and branch. Set status to `done`. This is the only condition under which reconcile writes `done` -- do not inspect acceptance criteria, judge completeness, or leave the task open pending review; that judgment is Sara's, before merge, not reconcile's after it. Every task set `done` this way proceeds to §3.
- **Closed unmerged**: Route per §4.
- **Backstop**: Sweep `merge_ready` -- if its PR is in fact merged, set `done` and proceed to §3; otherwise leave it for Sara. Sweep `review` for a merged PR only; never resolve `review` any other way -- it stays parked on Sara's or a human decision.

### 3. Harvest and Delete Settled Tasks

Apply [[kb_graph_hygiene_rules]] to every task set `done` in §2 this run, and as a backstop to any task already `status: done` carrying no harvest audit receipt (one bypassed this step in an earlier run):

1. **Durability Bar.** Run each factual claim in the task body through the 4-filter tree: persistence beyond the task's lifecycle, not episodic narration or debris (retry logs, diffs, commit SHAs -- git holds those), matches one of the 5 durable categories (architectural invariant, empirical finding, policy/standing decision, domain concept, living procedure), not already captured in a canonical note. No survivors: skip to step 4.
2. **Destination Rule.** For each surviving proposition, resolve a destination via `pkb.search(type="knowledge")` or an existing topic MOC. Existing note: synthesize the fact in via `pkb.update_body` (never append as a dated changelog). No note: `pkb.create(type="knowledge", id="kb_<slug>", ...)` parented to the domain MOC. Universal invariant or standing user directive: route to `plugins/rbg/skills/axioms/` or a dedicated standing-decision node. The destination must resolve to an explicit id before any write.
3. **Pre-Deletion Verification Gate.** Before deleting the source, confirm in order: (1) `pkb.get_document(destination_id)` resolves; (2) its `modified` timestamp is at or after the write; (3) the extracted proposition text reads back from the returned body; (4) any external wikilinks to the source are reparented to the destination; (5) write the audit receipt `{source_id, destination_id, verified_at, verified_facts}`. Any failure: `HALT: pre_deletion_verification_failed(source_id, destination_id, check_num)` and leave the source in place -- do not retry against a different destination in the same pass.
4. **Outright deletion.** Once step 3 passes (or step 1 found nothing to extract), `pkb.delete(source_id)`. No tombstone, no `status: archived`, no archive copy -- git holds the history.

### 4. Route Closed Unmerged PRs

Classify using reviewer comments and labels:

| Class                | Signal                              | Action                                                                                 |
| -------------------- | ----------------------------------- | -------------------------------------------------------------------------------------- |
| `wontfix`            | Objective rejected or superseded    | Cancel task (or complete if superseded by sibling); record reviewer reason.            |
| `bad-implementation` | Rejected approach, rework requested | Invoke `/aops:q` to reposition task under same parent to `inbox` with failure context. |
| `retry-as-is`        | Transient infrastructure failure    | Return to `inbox` with rationale.                                                      |

### 5. Consolidate Open Duplicates

Apply [[kb_graph_hygiene_rules]] Rule Set 3 to near-duplicate clusters found among open tasks (`inbox`, `ready`) sharing a parent or high semantic similarity:

1. **Differential Fact Audit.** Extract the atomic propositions from each node in the cluster and partition into shared agreement, contradictions (resolve against ground truth -- code, commits, recorded user directives, with the resolution recorded), and single-source facts unique to each side.
2. **Single-Source Guard.** Every single-source fact gets an explicit disposition: fold into the synthesized node, or a recorded reason for deliberate exclusion. An unhandled single-source fact halts the merge -- `HALT: unhandled_single_source_fact` -- silence is never consent to drop it.
3. **Synthesize, never concatenate.** Write one minimal node carrying the shared facts, the resolved contradictions, and every folded-in single-source fact, onto the surviving id. Union-of-everything is a failure outcome, not a safe default.
4. **Same gate, same deletion.** Run the synthesized write through §3 step 3's Pre-Deletion Verification Gate against the surviving node as destination, then `pkb.delete` the merged-away node outright.

### 6. Staleness, Rot, and Cancellation

- **Aged tasks (>90 days)**: Check sent mail, commits, or calendar for completion evidence. If conclusive (`confidence: high`, `settles: true`), record the evidence and set status to `review` for Sara's disposition -- reconcile does not set `done` on anything but an observed merge (§2). Otherwise flag for human review. Never cancel on age alone.
- **Artifact rot (>14 days in `ready`/`queued`)**: Verify that named paths and symbols exist. Verified deletion cancels the task; missing or relocated paths demote to `inbox`.
- **World-fact cancellation**: Cancel only when:
  1. _Referent destroyed_: Path or interface was deleted across all relevant refs and checkouts (not merely moved).
  2. _Superseded by merge_: A merged PR settled the objective (§2).
  3. _Premise falsified_: An explicit precondition or assumption no longer holds.
- **Evidence required**: Write the specific audit trail (commit, PR, quoted assumption, or verified ref) into the node body.

#### Two-Step Mutation Contract

Governs status demotions and cancellations in §4 and §6. Hygiene deletions in §3 and §5 use the Pre-Deletion Verification Gate instead -- do not substitute one for the other.

Every status demotion or cancellation must follow this order:

1. **Body**: Write evidence/annotation via `pkb.update_body` or `pkb.append`.
2. **Status**: Update frontmatter status via `pkb.update_task(id="<id>", updates={"status": "inbox"|"cancelled"})`. Never use `pkb.batch_update` for status changes.
3. **Readback**: Call `pkb.get_task` to confirm frontmatter status persisted.

### 7. Demote Affected Dependents to Inbox

Collect tasks affected by completed work, falsified assumptions, or cancellations:

- Unblocked `depends_on` dependents and live siblings.
- Tasks whose assumptions were tested by completed probes.
- Tasks demoted for artifact rot or repositioned by §4.

Set their status to `inbox` via the two-step mutation contract.

### 8. Emit Result

Return a single structured summary:

- Decisions requiring human attention.
- Completed and demoted task IDs.
- Cancellations grouped by trigger with cited evidence.
- Tasks returned to `inbox`.
- Harvested-and-deleted task ids with their destination ids, and consolidated duplicate pairs with the surviving id (§3, §5).
- Covered window and recommended next sweep targets.

## Must Not

- Certify completion based on subjective judgment or relay unverified worker self-reports.
- Set `done` on anything but an observed merged pull request (§2) -- never on judged acceptance criteria, non-PR completion evidence, or a worker's self-report.
- Reset stale or abandoned claims, or forward completed-but-uncertified work to the dispatcher -- both are Sara's outcomes (`partial`, `merge_ready`, `review`, or back to `queued`).
- Cancel or complete tasks based solely on age, quietness, or duplication.
- Cancel without writing auditable evidence to the node body.
- Update task bodies without updating frontmatter status via `pkb.update_task`.
- Use `pkb.batch_update` for status changes.
- Write `focus_score`, `intent`, `priority`, or `severity`.
- Promote tasks into `queued`.
- Re-plan or second-guess recorded human decisions.
- Prune or consolidate nodes except under the ratified rule sets in [[kb_graph_hygiene_rules]] -- and within them, never skip the Pre-Deletion Verification Gate or the Consolidation Guard's single-source disposition to save a step.
- Wait for per-batch sign-off before a hygiene deletion or merge -- [[kb_clean_first_git_recovery]] makes git the recovery path; the ratified rule set is the only gate.
- Delete a source node whose destination readback (§3 step 3, check 3) has not been confirmed.

---
name: reconcile
description: Truth maintenance over the task graph -- verification of claimed evidence on done tasks, pull request matching, scope checks, world-fact cancellations, and setting each task it reads to the status its evidence supports. Exclude for worker-level task completion (workers mark done after /pull).
---

# Reconcile

Truth maintenance over the task graph, run by a peer Ida instance -- never by the worker whose claim it checks. Reconcile evaluates claimed evidence, verifies scope, matches pull requests, routes failed checks, and sets each task it reads to the status its evidence supports. It does not claim to be the sole writer of `done`; workers with PKB access mark their tasks `done` after `/pull`.

## Modular Inspection Checks

1. **Load active tasks**: Read non-terminal tasks across active statuses within the sweep window.
2. For tasks marked `done`, evaluate:
   - **Pull request matching**: Match open and closed pull requests to tasks by structured identifiers (`pr_url`, task ID in PR body/branch, exact title). Unconditionally recognize merged PRs; inspect unmerged or closed PRs.
   - **Facial sufficiency of claimed evidence**: Read each piece of claimed evidence in the worker's report against the task's literal acceptance criteria. Verify whether the evidence is facially sufficient to prove the criteria were met. Asserting that tests passed is sufficient for a worker's completion claim; full substantive QA is handled independently.
   - **Scope check**: Verify that the delivered work and touched files respected the task's specified boundaries and did not expand beyond authorized scope.
3. **Reconcile pull requests**: Match closed pull requests to tasks by structured indicators (`pr_url`, body task ID, recorded branch, `polecat/` prefix, exact title).
   - **Merged PRs**: Confirm `status: done` on observed merged PRs.
   - **Closed without merge**: Surface for routing if unsure about how to update the corresponding task.

## Set the Status on Each Task

Every task this sweep reads leaves it in the one status that matches its evidence. A status that no longer describes the task is a defect you fix in the same pass, under the two-step mutation contract below. Status meanings are the PKB taxonomy's (the mem repository's TAXONOMY reference, "Status Values and Transitions"); this table applies them:

| Task is in    | Evidence on the record                                                                    | Set it to                                                                                     |
| ------------- | ----------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `done`        | Claimed evidence passes facial sufficiency and scope                                      | `done` (unchanged)                                                                            |
| `done`        | Fails either check and cannot be remedied in-session                                      | `review`, per Failed-Check Outcome                                                            |
| any open      | Its PR is merged and its acceptance criteria are met                                      | `done`                                                                                        |
| `review`      | The body names a decision only Nic can make, and that decision is still open              | `review` (unchanged); name the decision in the sweep's result                                 |
| `review`      | The work is claimed complete and no decision of Nic's is named (parked for merge or QA)   | Judge it as a `done` claim: `done` if it passes, else stays `review` per Failed-Check Outcome |
| `review`      | Agent work remains and no decision of Nic's is named (parked on a tool, blocker or retry) | `queued` if the task was queued before its claim; otherwise `inbox`                           |
| `in_progress` | No live claim: unmodified for more than 24 hours                                          | `queued`                                                                                      |
| `partial`     | Increment delivered and a live follow-up task carries the remainder                       | `partial` (unchanged)                                                                         |
| any open      | A world-fact trigger fired                                                                | `cancelled`, per Graph Maintenance                                                            |

- **`review` means waiting on Nic's decision.** Leave a task there only when the body names that decision. Agent work never waits in `review`.
- **`queued` stays Nic's gate.** Set `queued` only to restore a promotion Nic already made: a stuck `in_progress` task, or a `review` task parked after a queued claim. Never promote `inbox` or `ready` work to `queued`.
- **Use only the statuses in the table.** Never write `merge_ready` or any status outside the taxonomy.

## Failed-Check Outcome

When a task marked `done` fails the facial sufficiency or scope check:

1. **Remedy before escalation where possible**: A failure remedied before reaching the user (e.g. missing evidence supplied by an independent verification check that passes) is not a failure -- confirm `status: done` citing the remedied evidence.
2. **Escalate unremedied failures**: For failures that cannot be remedied in-session, route the task for ratification or reversal rather than returning it to `inbox`. Set `status: review` and document the exact failure reason and unverified criteria in the task body.
3. **Convert PR to draft with comment**: If a PR was filed, convert it to a draft PR (`gh pr ready --undo` or API equivalent) and post an explanatory comment stating which check failed and what the user needs to decide, preventing accidental merge before ratification.

## Graph Maintenance & World-Facts

1. **Cancel on world-facts**: Cancel tasks only on affirmative evidence recorded in the node body:
   - _Referent destroyed_: Target artifact was deleted, verified across checkouts and refs.
   - _Superseded by merge_: Merged PR mooted or settled the task's question.
   - _Premise falsified_: Named assumption or precondition no longer holds.
2. **Demote affected tasks**: Set unblocked dependents, siblings of landed work, rot (>14d in `ready`/`queued`), and invalidated assumption nodes to `status: inbox` with explanatory annotations. Do not send failed `done` tasks to inbox.
3. **Two-step mutation contract**: Write annotation and evidence to markdown body first, then mutate frontmatter via `pkb.update_task`, then read back to confirm status.
4. **Daily note boundary**: Reconcile does not append to or own daily-note sections.

## Output Contract

Emit one synthesized result:

1. Checks failed: Tasks escalated for ratification or reversal (with recorded reasons and PR draft links).
2. Status updates made (task IDs, PR links, verified completions).
3. Cancellations (task ID, trigger fired, verbatim evidence written to body).
4. Tasks demoted to `inbox` (dependents, stale items).
5. Sweep window covered.

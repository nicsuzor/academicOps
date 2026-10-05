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

Every task this sweep reads leaves it in the one status that matches its evidence. A status that no longer describes the task is a defect you fix in the same pass, under the two-step mutation contract below. Status meanings are the PKB taxonomy's ("Status Values and Transitions"); this table applies them:

| Task is in    | Evidence on the record                                                                    | Set it to                                                                                       |
| ------------- | ----------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `done`        | Claimed evidence passes facial sufficiency and scope                                      | `done` (unchanged)                                                                              |
| `done`        | Fails either check and cannot be remedied in-session                                      | `review`, per Failed-Check Outcome                                                              |
| any open      | Its PR is merged and its acceptance criteria are met                                      | `done`                                                                                          |
| `review`      | The body names a decision for Nic that is still open                                      | Settle it per Settle Decisions Before They Reach Nic; leave it in `review` only if it stays his |
| `review`      | The work is claimed complete and no decision of Nic's is named (parked for merge or QA)   | Judge it as a `done` claim: `done` if it passes, else stays `review` per Failed-Check Outcome   |
| `review`      | Agent work remains and no decision of Nic's is named (parked on a tool, blocker or retry) | `queued` if the task was queued before its claim; otherwise `inbox`                             |
| `in_progress` | No live claim: unmodified for more than 24 hours                                          | `queued`                                                                                        |
| `partial`     | Increment delivered and a live follow-up task carries the remainder                       | `partial` (unchanged)                                                                           |
| any open      | A world-fact trigger fired                                                                | `cancelled`, per Graph Maintenance                                                              |

- **`review` means waiting on Nic's decision.** Leave a task there only when the body names a decision that stays his under Settle Decisions Before They Reach Nic. Agent work never waits in `review`.
- **`queued` stays Nic's gate.** Set `queued` only to restore a promotion Nic already made: a stuck `in_progress` task, or a `review` task parked after a queued claim. Never promote `inbox` or `ready` work to `queued`.
- **Use only the statuses in the table.** Never write `merge_ready` or any status outside the taxonomy.

## Settle Decisions Before They Reach Nic

Every open decision of Nic's becomes a line of work on his daily note, so settle it yourself first. Nic has delegated his open decisions to you; this applies to each `review` task that names one and to each escalation you are about to write.

A decision stays his only when one of these holds:

- **His fact**: the answer turns on something only he knows that the record does not hold -- his home, health, relationships, or an unrecorded preference.
- **His name**: acting on it speaks or commits for him outside the graph, spends his money, or cannot be undone.
- **His field**: it sets a field reserved to him, such as `intent`, and no ruling of his on record covers the case.

Pull-request base, merge readiness, style commits, review depth, sequencing, tool choice and security hygiene meet none of these; rule on them.

To rule:

1. Search the record for his rulings and stated positions on the question and apply them. Where none applies, take the reversible option that keeps work moving.
2. Append a `Ruled on Nic's behalf` entry to the task body: the ruling, its reason with a citation, and that he may reverse it.
3. Set the status the ruling leaves: `done` if it closes the task, otherwise the agent-work-remains row above.

A decision the body shows Nic already made is not open: cite where he made it and apply the row it leaves.

For a decision that stays his, reduce it to the single question he must answer, answerable in one line, and write that question with the default you would take to the task's `reason`. Name which test kept it.

## Failed-Check Outcome

When a task marked `done` fails the facial sufficiency or scope check:

1. **Remedy before escalation where possible**: A failure remedied before reaching the user (e.g. missing evidence supplied by an independent verification check that passes) is not a failure -- confirm `status: done` citing the remedied evidence.
2. **Escalate unremedied failures**: For failures that cannot be remedied in-session, route the task for ratification or reversal rather than returning it to `inbox`. Set `status: review` and document the exact failure reason and unverified criteria in the task body, with the ratify-or-reverse question reduced to one line per Settle Decisions Before They Reach Nic.
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

1. Rulings made on Nic's behalf (task ID, ruling, citation).
2. Decisions left with Nic (task ID, the one-line question, the test that kept it).
3. Checks failed: Tasks escalated for ratification or reversal (with recorded reasons and PR draft links).
4. Status updates made (task IDs, PR links, verified completions).
5. Cancellations (task ID, trigger fired, verbatim evidence written to body).
6. Tasks demoted to `inbox` (dependents, stale items).
7. Sweep window covered.

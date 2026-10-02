---
name: reconcile
description: Truth maintenance over the task graph -- verification of claimed evidence on done tasks, pull request matching, scope checks, and world-fact cancellations. Exclude for worker-level task completion (workers mark done after /pull).
---

# Reconcile

Truth maintenance over the task graph. Reconcile evaluates claimed evidence, verifies scope, matches pull requests, and routes failed checks. It does not claim to be the sole writer of `done`; workers with PKB access mark their tasks `done` after `/pull`.

## Modular Inspection Checks

1. **Load active tasks**: Read non-terminal tasks across active statuses within the sweep window.
2. For tasks marked `done`, evaluate:
   - **Pull request matching**: Match open and closed pull requests to tasks by structured identifiers (`pr_url`, task ID in PR body/branch, exact title). Unconditionally recognize merged PRs; inspect unmerged or closed PRs.
   - **Facial sufficiency of claimed evidence**: Read each piece of claimed evidence in the worker's report against the task's literal acceptance criteria. Verify whether the evidence is facially sufficient to prove the criteria were met. Asserting that tests passed is sufficient for a worker's completion claim; full substantive QA is handled independently.
   - **Scope check**: Verify that the delivered work and touched files respected the task's specified boundaries and did not expand beyond authorized scope.
3. **Reconcile pull requests**: Match closed pull requests to tasks by structured indicators (`pr_url`, body task ID, recorded branch, `polecat/` prefix, exact title).
   - **Merged PRs**: Confirm `status: done` on observed merged PRs.
   - **Closed without merge**: Surface for routing if unsure about how to update the corresponding task.

## Failed-Check Outcome

When a task marked `done` fails the facial sufficiency or scope check:

1. **Remedy before escalation where possible**: A failure remedied before reaching Nic (e.g. missing evidence supplied by an independent verification check that passes) is not a failure -- confirm `status: done` citing the remedied evidence.
2. **Escalate unremedied failures**: For failures that cannot be remedied in-session, route the task for ratification or reversal rather than returning it to `inbox`. Set `status: review` and document the exact failure reason and unverified criteria in the task body.
3. **Convert PR to draft with comment**: If a PR was filed, convert it to a draft PR (`gh pr ready --undo` or API equivalent) and post an explanatory comment stating which check failed and what Nic needs to decide, preventing accidental merge before ratification.

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

---
name: reconcile
description: Truth maintenance over the task graph -- verification of claimed evidence on done tasks, pull request matching, scope checks, next-task assurance for unfinished work, and world-fact cancellations. Exclude for worker-level task completion (workers mark done after /pull).
---

# Reconcile

Truth maintenance over the task graph. Reconcile evaluates claimed evidence, verifies scope, matches pull requests, routes failed checks, and ensures every unfinished piece of work has a next task. It does not claim to be the sole writer of `done`; workers with PKB access mark their tasks `done` after `/pull`.

## Modular Inspection Checks

1. **Load tasks**: Read non-terminal tasks across active statuses, plus tasks marked `done` within the sweep window.
2. For tasks marked `done`, evaluate:
   - **Pull request matching**: Match open and closed pull requests to tasks by structured identifiers (`pr_url`, task ID in PR body/branch, exact title). Unconditionally recognize merged PRs; inspect unmerged or closed PRs.
   - **Facial sufficiency of claimed evidence**: Read each piece of claimed evidence in the worker's report against the task's literal acceptance criteria. Verify whether the evidence is facially sufficient to prove the criteria were met. Asserting that tests passed is sufficient for a worker's completion claim; full substantive QA is handled independently.
   - **Scope check**: Verify that the delivered work and touched files respected the task's specified boundaries and did not expand beyond authorized scope.
3. **Reconcile pull requests**: Match closed pull requests to tasks by structured indicators (`pr_url`, body task ID, recorded branch, `polecat/` prefix, exact title).
   - **Merged PRs**: Confirm `status: done` on observed merged PRs.
   - **Closed without merge**: Surface for routing if unsure about how to update the corresponding task.

## Next-Task Assurance

Each unfinished piece of work must leave a next task that someone can pick up. Here, "unfinished" means one of:

- a task marked `done` whose PR is still open, whether draft or ready;
- a task in `partial` or `paused`;
- a task in `in_progress` without a live claim (e.g. from a worker crash);
- a draft PR whose task is waiting on another piece of work.

A piece of work is covered when one of these holds:

- a next task exists and is `queued` or `ready`, or is `in_progress` under a live claim;
- the work waits on a decision from Nic that this sweep's result names (tasks in `review`).

For each piece of work that is not covered:

1. **Find the governing finish template**: the project's `.agents/templates/wf-finish.md` if it exists, otherwise the universal `wf-finish` template in the workflow library. Its QA review rule decides whether the change needs QA. Its Follow-up QA Task Specification gives the shape of the QA task.
2. **Look for an existing next task first**: the task's `follow_up_tasks`, its children, tasks that `depends_on` it, and a task titled `QA: <task title>`. Do not mint a duplicate.
3. **Awaiting QA**: the task is `done` with an open PR, and the finish template requires QA for the change.
   - If no QA task exists, mint one following the template's specification: title, same parent, and `depends_on: [<task-id>]`. Then add its ID to the source task's `follow_up_tasks`.
   - If the QA task exists but sits in `inbox`, set it to `queued`.
   - If the finish template has QA review a PR that is ready for review, and the PR is still a draft, mark it ready with `gh pr ready`.
   - Leave a PR in draft when this skill converted it under a failed check (task in `review`).
4. **Draft awaiting related work**: the PR body, the task's release text, or its `depends_on` edges name another piece of work that must land first.
   - Find the task that carries that work. If none exists, mint one, then wire `depends_on` from the waiting task to it.
   - If that work has landed, check that the draft has picked it up (rebased, or the follow-up commit is on its branch). If it has, the PR now awaits QA; handle it under step 3. If it hasn't, queue the waiting task so a worker finishes the PR.
   - If that work has not landed, and the task that carries it is in an inactive state (`inbox` or `paused`), set it to `queued`.
5. **Partial or paused without a successor**: mint a task for the remaining acceptance criteria, using the release reason as its goal. Add its ID to the source task's `follow_up_tasks`. If the remainder needs Nic's decision first, name that decision in the sweep's result instead.

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
2. **Demote affected tasks**: Set unblocked dependents, siblings of landed work, rot (>14d in `ready`/`queued`), and invalidated assumption nodes to `status: inbox` with explanatory annotations. Do not send failed `done` tasks to inbox. Do not demote a task that is the only next task for unfinished work (see Next-Task Assurance). Surface a stale one in the sweep's result instead.
3. **Two-step mutation contract**: Write annotation and evidence to markdown body first, then mutate frontmatter via `pkb.update_task`, then read back to confirm status.
4. **Daily note boundary**: Reconcile does not append to or own daily-note sections.

## Output Contract

Emit one synthesized result:

1. Checks failed: Tasks escalated for ratification or reversal (with recorded reasons and PR draft links).
2. Status updates made (task IDs, PR links, verified completions).
3. Unfinished work recovered: next tasks minted or re-queued, and PRs marked ready (task IDs, PR links, evidence that the work had no next task). Also list each piece of work waiting on Nic's decision, with that decision named.
4. Cancellations (task ID, trigger fired, verbatim evidence written to body).
5. Tasks demoted to `inbox` (dependents, stale items).
6. Sweep window covered.

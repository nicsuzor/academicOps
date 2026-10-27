---
description: Truth maintenance over the task graph -- reconcile merged PRs, move review tasks to reality under the bazaar model, handle failed tasks by deciding next actions from the parent epic, write items reaching the user to today's daily note, record world-fact cancellations, and demote affected tasks to inbox.
id: wf-reconcile
tags:
  - wf-template
  - reconcile
title: wf-reconcile
type: template
---

## What this step does

Maintains truth over the task graph: establishes facts about in-flight work and landed changes, brings `review` tasks up to date with reality, checks returned work on the papers, writes items that have reached the user to today's daily note, and returns touched tasks to `inbox` for re-planning.

## Obligations

1. **Load active and failed tasks**: Read non-terminal tasks across active statuses AND tasks marked `failed` within the sweep window. Closures made directly by the principal are self-authorizing and presumed intentional (no worker completion receipts required; never demote or flag).
2. **Reconcile pull requests**: Match closed pull requests to tasks by structured indicators (`pr_url`, body task ID, recorded branch, `polecat/` prefix, exact title).
   - **Merged PRs**: Write `status: done` unconditionally on an observed merged PR (`pr_url`, merge timestamp, branch). Do not re-judge acceptance criteria. Where a merged PR resolves part of a multi-component task or user request, itemize completed versus incomplete elements in the task record; uncompleted components remain active or carry over as open work.
   - **Closed without merge**: Surface for routing; never auto-complete or auto-requeue.
   - **Open PRs**: Read review and check state with `gh pr view <n> --repo <owner/repo> --json state,isDraft,mergedAt,reviewDecision,statusCheckRollup`. `reviewDecision: CHANGES_REQUESTED` or a failing check in `statusCheckRollup` routes the task to `queued` or a follow-up task, never `done` or `review`. Otherwise, a `review` task whose PR is still open is waiting on the repository to merge it; leave it until the PR merges or closes.
3. **The Review Lifecycle**: Apart from a task waiting on its open PR (step 2), `review` means a worker needs help to finish the task; it is transient, never a waiting state. Under the bazaar model, any pass reading a `review` task owns the outcome in that pass and mints any needed tasks; nothing is deferred to a later sweep or the original dispatcher. Bring the record to reality and take exactly one outcome:
   - `ready` or `queued`: not finished properly, an agent can finish it.
   - `partial` plus a new review task queued for an agent, wired so the source cannot complete before it (source `depends_on` it). Dispatch or queue the review task so it does not sit idle.
   - `done` plus a clean split of partly-finished work (sequencing handled by the epic).
   - `failed`: terminal failure with documented root cause.
     Nothing is left in `review`.
4. **Decide next action for failed tasks from the parent epic**: Workers never create or name follow-up tasks, and release `failed` when a check (e.g. QA or review) or implementation fails. For every task marked `failed` within the sweep window:
   - Inspect the failure record: failure evidence, unmet criteria, and documented root cause in `## Report` and `reason`.
   - Load the task's parent epic and its wider graph context (siblings, dependencies, and epic goals).
   - Decide the next action from the epic context:
     - _Rework / retry_: If the failure is remediable (e.g. a bug or unmet criterion), mint a rework task under the parent epic with updated requirements and appropriate dependencies.
     - _Epic reprioritization / cancellation_: If the failure is architectural, fatal, or invalidates the approach, mark affected downstream tasks under the epic as blocked or cancelled with explanatory annotations.
     - _Escalation_: If the failure requires principal input or changes epic scope, escalate to the daily note `## With you` naming the epic and the decision required.
   - Annotate the failed task record with the reconcile determination so it is settled on the graph and not re-processed on subsequent sweeps.
5. **Escalation on the record**: If an unrecorded fact, external commitment, or reserved field forces escalation, reduce to a single one-line question in `reason`, queue a review task for the next escalation level, wire `depends_on`, dispatch or queue it, and transition source task to `partial` (outcome 2).
6. **Check returned work on the papers**: Verify the account of returned work on the record before deciding what reaches the user:
   - _Chain of evidence_: verify `pr_url`, `completion_evidence`, or named artifact exists.
   - _Soundness_: verify cited evidence actually answers acceptance criteria. If insufficient, return to `ready`/`queued` or `partial` with an agent review task (outcome 1 or 2); never escalate unproven claims to the user.
   - _Liveness_: verify question is still live; discard moot items settled by events.
7. **Reset stale claims**: Stale `in_progress` tasks with no live claim (>24h unmodified without active session or worker) reset to `queued`. Never move a claimed task backwards while an active worker holds it.
8. **Demote affected tasks**: Set unblocked dependents, siblings of landed work, rot (>14d in `ready`/`queued`), and invalidated assumption nodes to `status: inbox` with explanatory annotations.
9. **Cancel on world-facts**: Cancel only on affirmative evidence recorded in the node body:
   - _Referent destroyed_: target artifact was deleted, verified across checkouts and refs.
   - _Superseded by merge_: merged PR mooted or settled the task's question.
   - _Premise falsified_: named assumption or precondition no longer holds.
   - _Source-stated retirement_: opportunity's source confirms it is no longer open, or explicit principal instruction ("drop X"). Set `status: cancelled` with reason starting `not ripe:` quoting statement and source.
10. **Two-step mutation contract**: Write annotation/evidence to markdown body first, then mutate frontmatter `status` via `pkb.update_task` (never `batch_update`), then read back to confirm status.
11. **Escalate**: Settle items reaching the user under the one-level escalation rule (e.g. review tasks reaching the front agent `ida` at the top of the chain requiring user decision, or open questions/asks needing user choice). When running standalone, write them to today's daily note (PKB note `YYYYMMDD-daily`) in `## With you`. When invoked as part of an enclosing run (such as the daily note pipeline), return the escalated items to the caller to fold into `## With you` during its single atomic write, accompanied by current verification timestamps. Reconcile interfaces with the daily note _exclusively_ via `## With you` for escalated decisions; it must never write or append raw mutation summaries, commit SHAs, PR merge logs, branch names, container IDs, or execution heartbeats to the daily note, nor create or append to sections outside `## With you`.

## Must not

- Must not run concurrently with another reconcile: maintain single-flight execution (one reconcile at a time; halt immediately if another reconcile is active).
- Must not move a claimed (`in_progress`) task backwards while an active worker holds it.
- Must not leave minted agent review tasks in review or unowned (minted review tasks must be queued or dispatched).
- Must not write `done` on any evidence other than an observed merged PR or a clean finished part of a split task.
- Must not leave tasks in `review` or route tasks to `review` as a waiting state, except a task whose open PR awaits merge.
- Must not defer `review` outcomes to a later pass or to the original dispatcher.
- Must not escalate outside the framework (escalation is one level per hop on the record).
- Must not demand completion receipts for direct principal closures.
- Must not certify work complete or judge acceptance criteria after merge.
- Must not reset abandoned claims to `ready` or forward uncertified work to dispatcher.
- Must not close or cancel without required evidence written to the node body.
- Must not cancel on missing paths appearing only in narrative or provenance prose.
- Must not re-open or adjudicate settled principal decisions or merged pull requests.
- Must not annotate a body with status changes without mutating frontmatter `status`.
- Must not use `batch_update` for status mutations or demotions.
- Must not prune, re-plan, or restructure (delegate repositioning to `/q`).
- Must not write `intent`, `priority`, or `severity`.
- Must not promote `inbox` or `ready` work into `queued`.
- Must not ignore `failed` tasks within the sweep window: reconcile must examine each failed task and decide the next action from its parent epic.
- Must not allow workers to direct their own follow-up tasks or leave stale pointers in review reports; sequencing lives in the parent epic.
- Must not append unowned sections to the daily note outside `## With you`.
- Must not dump raw reconcile summaries, commit hashes, branch names, PR merge logs, or worker/container identifiers to the daily note.
- Must not generate or append `## Daily Log` or execution run heartbeats to the daily note (audit and run traces belong in runner logs/OTel).
- Must not write items with unverified or insufficient evidence to the daily note.

## Output contract

Emit one synthesized result:

1. Rulings made without escalation, review tasks minted/escalated, and items written to the daily note `## With you` (task ID, reviewer level, one-line question, source task transitioned).
2. Status changes made (with task IDs and PR links).
3. Tasks found and left alone.
4. Tasks returned to `inbox`.
5. Cancellations as a distinct category (task ID, trigger fired, verbatim evidence written to body).
6. Name IDs for every touched task (no bare counts).
7. State the covered sweep window and what the next sweep should pick up.
8. Failed tasks reconciled with next actions decided from their parent epics (task ID, root cause, remediation task minted or epic-level adjustment made).

## When to include

Re-engagement after absence, within periodic consolidation cycles (`remember`), before daily note composition (`tpl-daily`), or on-demand graph truth maintenance.

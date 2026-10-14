---
description: Truth maintenance over the task graph -- reconcile merged PRs, move review tasks to reality under the bazaar model, write items reaching the user to today's daily note, record world-fact cancellations, and demote affected tasks to inbox.
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

1. **Load active tasks**: Read non-terminal tasks across active statuses within the sweep window. Closures made directly by the principal are self-authorizing and presumed intentional (no worker completion receipts required; never demote or flag).
2. **Reconcile pull requests**: Match closed pull requests to tasks by structured indicators (`pr_url`, body task ID, recorded branch, `polecat/` prefix, exact title).
   - **Merged PRs**: Write `status: done` unconditionally on an observed merged PR (`pr_url`, merge timestamp, branch). Do not re-judge acceptance criteria.
   - **Closed without merge**: Surface for routing; never auto-complete or auto-requeue.
   - **Open PRs**: Read review and check state with `gh pr view <n> --repo <owner/repo> --json state,isDraft,mergedAt,reviewDecision,statusCheckRollup`. `reviewDecision: CHANGES_REQUESTED` or a failing check in `statusCheckRollup` routes the task to `queued` or a follow-up task, never `done` or `review`.
   - **Open PR with complete deliverable and dependent follow-up**: When a task in `partial` or `queued` has its own deliverable complete (open PR read as above with no `CHANGES_REQUESTED` and all checks passing, acceptance criteria satisfied on the record) and an independent follow-up task depends on it (such as QA, merge, or deploy): write `status: done` so the dependent follow-up is unblocked. A worker whose own deliverable is complete releases `done`, even when a follow-up that depends on it is still to run; `partial` is only for the worker's own unfinished acceptance items. Never send or leave a complete deliverable in `partial` or `queued` because of a dependent follow-up.
3. **The Review Lifecycle**: `review` means a worker needs help to finish the task; it is transient, never a waiting state. Under the bazaar model, any pass reading a `review` task owns the outcome in that pass and mints any needed tasks; nothing is deferred to a later sweep or the original dispatcher. Bring the record to reality and take exactly one outcome:
   - `ready` or `queued`: not finished properly, an agent can finish it.
   - `partial` plus a new review task queued for an agent, wired so the source cannot complete before it (source `depends_on` it).
   - `done` plus a queued follow-up task (clean split of partly-finished work).
   - `failed`: terminal failure with documented root cause.
     Nothing is left in `review`.
4. **Settle decisions before escalation**: Escalation is one level per hop on the record, never jumping tiers. Each agent escalates at most one level; only the front agent at the top of the chain speaks outside the framework. Settle open decisions yourself first where record or reversible judgment allows. If an unrecorded fact, external commitment, or reserved field forces escalation, reduce to a single one-line question in `reason`, queue a review task for the next escalation level, wire `depends_on`, and transition source task to `partial` (outcome 2).
5. **Check returned work on the papers**: Verify the account of returned work on the record before deciding what reaches the user:
   - _Chain of evidence_: verify `pr_url`, `completion_evidence`, or named artifact exists.
   - _Soundness_: verify cited evidence actually answers acceptance criteria. If insufficient, return to `ready`/`queued` or `partial` with an agent review task (outcome 1 or 2); never escalate unproven claims to the user.
   - _Liveness_: verify question is still live; discard moot items settled by events.
6. **Aged tasks and stale claims**: Stale `in_progress` tasks with no live claim (>24h unmodified) reset to `queued`. Rot (>14d in `ready`/`queued`) demotes to `status: inbox`. Never route aged items to `review`.
7. **Demote affected tasks**: Set unblocked dependents, siblings of landed work, rot (>14d in `ready`/`queued`), and invalidated assumption nodes to `status: inbox` with explanatory annotations.
8. **Cancel on world-facts**: Cancel only on affirmative evidence recorded in the node body:
   - _Referent destroyed_: target artifact was deleted, verified across checkouts and refs.
   - _Superseded by merge_: merged PR mooted or settled the task's question.
   - _Premise falsified_: named assumption or precondition no longer holds.
   - _Source-stated retirement_: opportunity's source confirms it is no longer open, or explicit principal instruction ("drop X"). Set `status: cancelled` with reason starting `not ripe:` quoting statement and source.
9. **Two-step mutation contract**: Write annotation/evidence to markdown body first, then mutate frontmatter `status` via `pkb.update_task` (never `batch_update`), then read back to confirm status.
10. **Daily note integration**: Every reconcile pass writes items that have reached the user under the one-level escalation rule (e.g. review tasks reaching the front agent `ida` at the top of the chain requiring user decision, or open questions/asks needing user choice) to today's daily note (PKB note `YYYYMMDD-daily`) in the named section `## With you`. For each item reaching the user, write a concise entry with its title, pointers (task ID, PR URL, artifact), and clear choice. Reconcile owns writing escalated items to `## With you`; it must not append unowned sections outside `## With you`.

## Must not

- Must not write `done` on any evidence other than an observed merged PR, a task whose own deliverable is complete and whose follow-up depends on it, or a clean finished part of a split task.
- Must not leave tasks in `review` or route tasks to `review` as a waiting state.
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
- Must not write `focus_score`, `intent`, `priority`, or `severity`.
- Must not promote `inbox` or `ready` work into `queued`.
- Must not append unowned sections to the daily note outside `## With you`.
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

## When to include

Re-engagement after absence, within periodic consolidation cycles (`remember`), before daily note composition (`tpl-daily`), or on-demand graph truth maintenance.

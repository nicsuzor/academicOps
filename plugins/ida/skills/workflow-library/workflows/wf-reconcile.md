---
description: Truth maintenance over the task graph -- advance open high-value-prompt tracking tasks and multi-part asks via groundwork, reconcile merged PRs and shipped releases, route user decisions with completed groundwork to review (assignee user) while transitioning agent tasks out of review, handle failed tasks from parent epics, write items reaching the user to today's daily note, record world-fact cancellations, and demote affected tasks to inbox.
id: wf-reconcile
tags:
  - wf-template
  - reconcile
title: wf-reconcile
type: template
---

## What this step does

Maintains truth over the task graph: advances open high-value-prompt tracking tasks and multi-part user asks through groundwork, establishes facts about in-flight work and landed changes, brings `review` tasks up to date with reality, checks that the recorded evidence for returned work formally supports its claim of completion, writes items that have reached the user to today's daily note, and returns touched tasks to `inbox` for re-planning.

## Obligations

1. **Load active, prompt-tracking, and failed tasks**: Read non-terminal tasks across active statuses (including open high-value-prompt tracking tasks tagged `high-value-prompt` or `prompt-sweep` and multi-part user asks in `inbox`/`ready`) AND tasks marked `failed` within the sweep window. When invoked with a cursor (`since: <cursor_utc>`), scope task, PR, and failure queries to records changed or unblocked since `<cursor_utc>` alongside open `high-value-prompt` tracking tasks and `status: review` tasks, and project fields (`id`, `title`, `status`, `assignee`, `pr_url`, `parent`) in batch queries so payloads stay under inline limits (`< 8 KB`) before opening full bodies on candidate mutations. Closures made directly by the principal are self-authorizing and presumed intentional (no worker completion receipts required; never demote or flag). For every open high-value-prompt tracking task or multi-part user ask, perform groundwork to move it on rather than leaving it in `inbox` or reporting it as passively "stuck": settle unknowns by querying the PKB first (tasks, notes, closed records) and then live GitHub PRs/issues/releases and traces; itemize completed versus remaining parts; close (`done`) tasks whose deliverable or release has shipped and the user knows about; place or promote the concrete next agent step onto the graph as `status: queued` via `/q`; and only when groundwork and option evaluation are complete (with a reasoned recommendation in the body) and the item genuinely waits on an explicitly user-reserved hold, host action, or invariant boundary (external audience, unruled merge, unbounded cost), set `status: review` (`assignee: user`) so it surfaces in the daily note's `## With you`.
2. **Reconcile pull requests and shipped releases**: Match closed pull requests and shipped releases to tasks by structured indicators (`pr_url`, body task ID, recorded branch, `polecat/` prefix, exact title), batching PR checks per repository (`gh pr list --repo <owner/repo> --state all --limit 100 --json number,title,state,isDraft,mergedAt,closedAt,headRefName,url,reviewDecision,statusCheckRollup`) and calling `gh pr view <n>` only for PRs outside the batch window.
   - **Merged PRs and shipped releases**: Write `status: done` unconditionally on an observed merged PR (`pr_url`, merge timestamp, branch) or on a deliverable/release that has shipped and been communicated to the user (never hold tasks open waiting to prove the user installed, pulled, or deployed a release). Do not re-judge acceptance criteria. Where a merged PR or release resolves part of a multi-component task or user request, itemize completed versus incomplete elements in the task record; uncompleted components remain active or are queued (`status: queued`) as concrete next-step work tasks.
   - **Closed without merge**: Surface for routing; never auto-complete or auto-requeue.
   - **Open PRs**: Inspect `state`, `isDraft`, `mergedAt`, `reviewDecision`, and `statusCheckRollup` from the batched repository listing (or `gh pr view <n>` if older than the batch). A work task released as `done` with an open PR remains `done` while the PR is open (whether checks are green, pending review, or awaiting merge); never move or demote an open-PR task to `review` awaiting review or merge (pending review is tracked on its separate review task, and merge is tracked on the PR-tracking task or parent epic). Only `reviewDecision: CHANGES_REQUESTED` or a failing check in `statusCheckRollup` routes work to `queued` or a rework follow-up task under the parent epic, never `review`.
3. **Reconciling Tasks in Review**: Agents never release work or deliverable tasks into `review`. Tasks in `status: review` assigned to the user (`assignee: user`) represent either manual inspection holds or completed-groundwork items genuinely blocked by an explicitly user-reserved pre-action hold, host action, or invariant boundary (external audience, unruled merge, unbounded cost); leave those in `status: review` (`assignee: user`) for today's daily note `## With you` and `/decide`, while promoting any directed task parked solely by agent/template class back to `queued`. For all other tasks in `status: review`:
   - **Covered by a review or QA task**: If an active review or QA task points to the task via graph prerequisite edges (`needs` contains the task ID), mutate the task status immediately to `done`. This unblocks dependent tasks on the graph.
   - **Uncovered with an open PR**: If no review or QA task covers the task, but an open pull request is recorded on the task, mutate the task status to `done` and, if the PR risk tier warrants verification, mint/queue a `QA: <title>` follow-up task with `needs: [<task_id>]`.
   - **Uncovered without a PR**: If the task has no PR and no covering review task, verify recorded evidence against acceptance criteria:
     - If criteria are fully satisfied with verifiable evidence (or the deliverable has shipped and the user is informed): mutate status to `done`.
     - If incomplete agent work remains: transition to `queued` (or `partial` if partly delivered).
     - If an explicitly user-reserved hold, host action, or invariant boundary remains after agent groundwork and option evaluation are recorded: set `status: review` with `assignee: user` (recording the recommendation and one-line decision in `reason`) and surface in today's daily note `## With you`.
       No agent work task is left in `review`.
4. **Parent Rollup Lifecycle**: When all open children under a composite task (`parent`) reach `done`, the composite task does not automatically close if it contains substantive acceptance criteria. Instead, transition it to `ready` for an explicit synthesis and sign-off pass. Verify composite criteria against the combined deliverables of its completed child set before marking the composite task `done`.
5. **Decide next action for failed tasks from the parent epic**: Workers never create or name follow-up tasks, and release `failed` when a check (e.g. QA or review) or implementation fails. For every task marked `failed` within the sweep window:
   - Inspect the failure record: failure evidence, unmet criteria, and documented root cause in `## Report` and `reason`.
   - Load the task's parent epic and its wider graph context (siblings, dependencies, and epic goals).
   - Decide the next action from the epic context:
     - _Rework / retry_: If the failure is remediable (e.g. a bug or unmet criterion), mint a rework task under the parent epic with updated requirements and appropriate dependencies (`needs`).
     - _Epic reprioritization / cancellation_: If the failure is architectural, fatal, or invalidates the approach, mark affected downstream tasks under the epic as blocked or cancelled with explanatory annotations.
     - _Escalation_: If the failure requires principal input or changes epic scope, escalate to the daily note `## With you` naming the epic and the decision required.
   - Annotate the failed task record with the reconcile determination so it is settled on the graph and not re-processed on subsequent sweeps.
6. **Escalation on the record**: If an unrecorded fact, external commitment, or reserved field forces escalation, reduce to a single one-line question in `reason`, queue a review task for the next escalation level, wire `needs`, dispatch or queue it, and transition source task to `partial` (outcome 2).
7. **Check that the recorded evidence formally supports the claim**: For each returned task, read what is already written on the record (`pr_url`, `completion_evidence`, named artifact, `## Report`) and decide whether, taking that evidence as present and genuine, it is sufficient to support the claim that the work is done. This is a formal sufficiency check of the record on its face; do not re-run the work, re-review the PR's code, or re-judge quality.
   - _Citation present_: the task cites a `pr_url`, `completion_evidence`, or named artifact. Do not fetch or inspect the artifact itself.
   - _Sufficiency_: the cited evidence, as described, addresses each acceptance criterion. If it does not, return to `ready`/`queued` or `partial` with an agent review task (outcome 1 or 2); never escalate an unsupported claim to the user.
   - _Liveness_: the question is still live; discard moot items settled by events.
8. **Reset stale claims**: Stale `in_progress` tasks with no live claim (>24h unmodified without active session or worker) reset to `queued`. Never move a claimed task backwards while an active worker holds it.
9. **Demote affected tasks**: Set unblocked dependents, siblings of landed work, rot (>14d in `ready`/`queued`), and invalidated assumption nodes to `status: inbox` with explanatory annotations.
10. **Cancel on world-facts**: Cancel only on affirmative evidence recorded in the node body:
    - _Referent destroyed_: target artifact was deleted, verified across checkouts and refs.
    - _Superseded by merge_: merged PR mooted or settled the task's question.
    - _Premise falsified_: named assumption or precondition no longer holds.
    - _Source-stated retirement_: opportunity's source confirms it is no longer open, or explicit principal instruction ("drop X"). Set `status: cancelled` with reason starting `not ripe:` quoting statement and source.
11. **Two-step mutation contract**: Write annotation/evidence to markdown body first, then mutate frontmatter `status` via `pkb.update_task` (never `batch_update`). Do not read back to confirm status; an error-free write is authoritative confirmation of success.
12. **Escalate**: Settle items reaching the user under the one-level escalation rule (e.g. review tasks reaching the front agent `ida` at the top of the chain requiring user decision, or open questions/asks needing user choice). When running standalone, write them to today's daily note (PKB note `YYYYMMDD-daily`) in `## With you`. When invoked as part of an enclosing run (such as the daily note pipeline), return the escalated items to the caller to fold into `## With you` during its single atomic write, accompanied by current verification timestamps. Reconcile interfaces with the daily note _exclusively_ via `## With you` for escalated decisions; it must never write or append raw mutation summaries, commit SHAs, PR merge logs, branch names, container IDs, or execution heartbeats to the daily note, nor create or append to sections outside `## With you`.

## Must not

- Must not run concurrently with another reconcile (halt immediately if an active reconcile lock exists) or move a claimed (`in_progress`) task backwards while an active worker holds it, reset abandoned claims to `ready`, or forward uncertified work to the dispatcher.
- Must not leave agent work tasks or minted review tasks in `review` or unowned, route agent tasks to `review`, defer `review` outcomes, or demote a `done` work task with an open PR to `review`; reserve `status: review` (`assignee: user`) strictly for manual user holds and completed-groundwork items gated by explicitly user-reserved holds, host actions, or invariant boundaries.
- Must not write `done` or `cancelled` without affirmative evidence recorded in the node body (ignoring missing paths appearing only in narrative or provenance prose), demand completion receipts for direct principal closures, certify work or judge acceptance criteria after merge, or re-open settled principal decisions or merged pull requests.
- Must not annotate status changes in the body without mutating frontmatter `status`, use `batch_update` for status mutations or demotions, prune/re-plan/restructure (delegate repositioning to `/q`), or write `intent`, `priority`, or `severity`.
- Must not blindly promote unexamined `inbox` or `ready` work into `queued` without groundwork and `/q` placement, ignore `failed` tasks within the sweep window, allow workers to direct their own follow-ups or leave stale pointers in review reports, or escalate outside the framework (one level per hop on the record).
- Must not append unowned sections outside `## With you`, dump raw reconcile summaries, commit hashes, branch names, PR merge logs, container identifiers, or `## Daily Log` heartbeats, or write unverified items to the daily note.

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

Re-engagement after absence, periodic memory consolidation cycles, pre-briefing graph truth maintenance, or on-demand reconciliation.

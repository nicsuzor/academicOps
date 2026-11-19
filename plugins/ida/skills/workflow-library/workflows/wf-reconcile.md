---
description: Truth maintenance over the task graph -- advance open high-value-prompt tracking tasks and multi-part asks via groundwork, reconcile merged PRs and shipped releases, route user decisions with completed groundwork to review (assignee user) while transitioning agent tasks out of review, handle failed tasks from parent epics, surface completed /learn remedy proposals, write items reaching the user to today's daily note, record world-fact cancellations, and demote affected tasks to inbox.
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

1. **Load active, prompt-tracking, and failed tasks**:
   - _Scope & batch projection_: Read non-terminal tasks across active statuses (including open `high-value-prompt` / `prompt-sweep` tracking tasks and multi-part asks in `inbox`/`ready`) AND tasks marked `failed` within the sweep window. Under `since: <cursor_utc>`, filter to changed or unblocked records alongside open tracking and `status: review` tasks; project summary fields (`id`, `title`, `status`, `assignee`, `pr_url`, `parent`) in batches (`< 8 KB`) before opening full bodies on candidate mutations.
   - _Direct principal closures_: Principal closures are self-authorizing and presumed intentional (no completion receipts required; never demote or flag).
   - _Groundwork on open prompts & asks_: Move each open tracking task or multi-part ask forward rather than leaving it in `inbox` or "stuck": query PKB first (tasks, notes, closed records) then live GitHub PRs/issues/releases and traces; itemize completed vs remaining parts; mark delivered/communicated items `done`; queue concrete next agent steps (`status: queued` via `/q`); and set `status: review` (`assignee: user`) with a recorded reasoned recommendation only when awaiting the user's own decision or host action.
2. **Reconcile pull requests and shipped releases**: Batch PR checks per repo (`gh pr list --repo <owner/repo> --state all --limit 100`, projecting state, draft, merge/close timestamps, branch, URL, `reviewDecision`, `statusCheckRollup`), falling back to `gh pr view <n>` only outside the batch:
   - **Merged PRs and shipped releases**: Transition to `done` unconditionally on observed merge (`pr_url`, merge timestamp, branch) or communicated release (never hold open verifying user pull/deploy, and never re-judge ACs); itemize remaining incomplete parts as `queued` next steps.
   - **Closed without merge**: Surface for routing; never auto-complete or auto-requeue.
   - **Open PRs**: A `done` work task with an open PR stays `done` across green checks, pending review, or merge wait (never demote open-PR work tasks to `review`); only `CHANGES_REQUESTED` or failing checks route rework to `queued` under the parent epic.
3. **Reconciling Tasks in Review**: Agents never release work tasks into `review`. Keep `status: review` (`assignee: user`) only for manual holds or user decisions with completed groundwork and a recorded recommendation; transition all other `review` tasks immediately:
   - **Covered by a review or QA task**: Mutate to `done` if an active review/QA task depends on it via `needs`.
   - **Uncovered with an open PR**: Mutate to `done` and queue `QA: <title>` (`needs: [<task_id>]`) if risk warrants.
   - **Uncovered without a PR**: Inspect recorded acceptance evidence; transition to `done` if complete/shipped, `queued` (or `partial`) if agent work remains, or `review` (`assignee: user`) with a reasoned one-line decision in `reason` if genuine principal choice remains. No agent work task remains in `review`.
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
12. **Escalate**: Escalate items reaching the user one level per hop to today's daily note `## With you` (or return them to the calling daily-note run for its atomic `## With you` write with verification timestamps). Interface _exclusively_ via `## With you` for escalated decisions; never write raw mutation summaries, SHAs, branches, PR logs, container IDs, or heartbeats to the daily note.
13. **Surface completed Class D `/learn` remedy proposals**: Read completed `/learn` tasks (`status: done` within the sweep window, projecting summary fields before reading `## Report` on matches) without re-analyzing raw PRs, logs, or spans, and without unilaterally restructuring the task graph. Surface each typed remedy in the report (and via `## With you` when awaiting user approval):
    - `bug fix at source`: list any queued fix-task ID, or surface unqueued `/q` fix-task proposals recorded in `## Report` for `/q` intake.
    - `recurring local-rule or mechanism proposal`: surface the proposed local-rule/mechanism escalation or draft issue awaiting user approval.

## Must not

- Must not run concurrently with another reconcile (halt immediately if an active reconcile lock exists) or move a claimed (`in_progress`) task backwards while an active worker holds it, reset abandoned claims to `ready`, or forward uncertified work to the dispatcher.
- Must not leave agent work tasks or minted review tasks in `review` or unowned, route agent tasks to `review`, defer `review` outcomes, or demote a `done` work task with an open PR to `review`; reserve `status: review` (`assignee: user`) strictly for manual user holds and completed-groundwork user decisions.
- Must not write `done` or `cancelled` without affirmative evidence recorded in the node body (ignoring missing paths appearing only in narrative or provenance prose), demand completion receipts for direct principal closures, certify work or judge acceptance criteria after merge, or re-open settled principal decisions or merged pull requests.
- Must not annotate status changes in the body without mutating frontmatter `status`, use `batch_update` for status mutations or demotions, re-analyze raw PRs or re-run `/learn` during truth maintenance, prune/re-plan/restructure (delegate repositioning to `/q`), or write `intent`, `priority`, or `severity`.
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
9. Completed Class D `/learn` remedy proposals surfaced (task ID, typed remedy: `bug fix at source` vs `recurring local-rule or mechanism proposal`, and queued fix-task ID or `/q` / approval status).

## When to include

Re-engagement after absence, periodic memory consolidation cycles, pre-briefing graph truth maintenance, or on-demand reconciliation.

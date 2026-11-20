---
description: Reconcile task graph truth -- advance open prompt-tracking tasks and multi-part asks via groundwork, reconcile PRs and releases, clear non-user review tasks, route failed tasks from parent epics, reset stale claims, demote stale or unblocked tasks to inbox, record world-fact cancellations, and surface user decisions to the daily note.
id: wf-reconcile
tags:
  - wf-template
  - reconcile
title: Graph Reconciliation Workflow
type: template
---

## What this step does

Reconciles the task graph with reality: advances open prompt-tracking and multi-part asks via groundwork, syncs PRs and releases, clears agent work out of `review`, settles failed tasks from their parent epics, prunes stale or falsified nodes, and surfaces verified user-facing decisions to today's daily note.

## Input contract

- Optional incremental cursor (`since: <cursor_utc>`).
- Access to the task graph, knowledge base, repository host, and session telemetry.

## Obligations

1. **Single-flight and scoped load**: Halt immediately if an active reconcile lock exists. Load non-terminal active tasks (including `high-value-prompt`/`prompt-sweep` tracking tasks, multi-part asks in `inbox`/`ready`, and `status: review`) plus `failed` tasks within the sweep window. When `since: <cursor_utc>` is given, scope queries to records changed or unblocked since the cursor alongside open `high-value-prompt` and `review` tasks; project summary fields before reading full bodies on candidate mutations.
2. **Groundwork on open asks and user closures**: Treat direct closures by the user as self-authorizing (require no completion receipts; never demote or re-open). Advance open `high-value-prompt` tasks and multi-part asks rather than leaving them in `inbox`: query the knowledge base first, then repository PRs/issues/releases and session traces; itemize completed vs. remaining parts; mark `done` when delivered and communicated; queue the concrete next agent step via `/q`; and set `status: review` (`assignee: user`) with a reasoned recommendation only when waiting on the user's own decision or host action.
3. **Pull requests and releases**: Match PRs and releases to tasks via `pr_url`, task ID, branch, or title, querying PRs in repository batches and inspecting individual PRs only outside the batch window.
   - _Merged or shipped_: Mark `done` unconditionally without re-judging acceptance criteria (never hold open waiting to prove user installation); for partial deliveries, itemize completed vs. remaining parts and queue concrete next steps.
   - _Closed unmerged_: Surface for routing; never auto-complete or auto-requeue.
   - _Open_: Keep a `done` work task in `done` while its PR is open (never demote to `review` awaiting review or merge). Route to `queued` or a rework task under the parent epic only on requested changes or failing checks.
4. **Clear non-user `review` tasks**: Reserve `status: review` (`assignee: user`) strictly for manual user holds and completed-groundwork user decisions (leave untouched for `## With you` and `/decide`). Transition all other `review` tasks out immediately:
   - Covered by an active review or QA task (`needs` includes task ID): mark `done`.
   - Uncovered with an open PR: mark `done`, and queue `QA: <title>` (`needs: [<task_id>]`) when risk warrants verification.
   - Uncovered without a PR: inspect recorded evidence -- mark `done` if criteria are met or shipped; move to `queued` (or `partial`) if agent work remains; or set `status: review` (`assignee: user`, one-line question and recommendation in `reason`) only if user input is required.
5. **Composite parent rollup**: When all open children under a parent reach `done`, transition a parent holding substantive acceptance criteria to `ready` for synthesis and verification before closing it.
6. **Settle failed tasks from parent epics**: For each `failed` task in the sweep window, inspect `## Report` and `reason`, load its parent epic and graph context, and record the determination on the failed task: mint a remediation task under the epic with updated requirements and `needs`, block or cancel invalidated downstream tasks if the approach failed, or escalate epic-scope/user decisions to `## With you`.
7. **Audit returned work and escalate one level**: Before surfacing work to the user, verify on the record that cited artifacts (`pr_url`, completion evidence) exist, answer acceptance criteria, and remain live; return unproven claims to `queued` or `partial` with a review task. When an unrecorded fact, external commitment, or reserved field forces escalation, write a one-line question in `reason`, queue a review task one level up with `needs`, and transition the source task to `partial`.
8. **Stale claims, demotions, and world-fact cancellations**:
   - Reset stale `in_progress` tasks (>24h unmodified with no active session or isolated worker) to `queued` (never `ready`; never move an actively claimed task backwards).
   - Demote unblocked dependents, siblings of landed work, stale `ready`/`queued` tasks (>14d), and invalidated assumption nodes to `inbox` with explanatory annotations (delegate structural repositioning to `/q`).
   - Cancel (`status: cancelled`, reason starting `not ripe:` quoting source evidence) only on affirmative body evidence: destroyed referent verified across refs, superseded by merge, falsified premise, or source-stated retirement / explicit user drop.
9. **Mutation and daily note contract**: Write evidence and annotations to the task body first, then mutate frontmatter `status` individually per task (never bulk-update status; never write `intent`, `priority`, or `severity`; do not read back after an error-free write). Surface user-facing decisions exclusively via `## With you` (written to `YYYYMMDD-daily` when standalone, or returned with verification timestamps to an enclosing daily-note pipeline) -- never write raw mutation logs, commit hashes, branch names, container IDs, or extra sections to the daily note.

## Output contract

One synthesized report stating the covered sweep window and next pickup boundary, naming task IDs (never bare counts) for:

- Rulings made without escalation, review tasks minted, and items surfaced to `## With you` (with reviewer level, one-line question, and source task).
- Status changes made (with PR links) and failed-task determinations from parent epics.
- Tasks returned to `inbox`, tasks inspected and left untouched, and cancellations with trigger and quoted body evidence.

## When to include

Re-engagement after absence, periodic memory consolidation cycles, pre-briefing graph truth maintenance, or on-demand reconciliation.

---
description: Reconcile task graph truth -- advance open prompt-tracking tasks and multi-part asks via groundwork, combine fragmented tracking tasks with checked-item synthesis, back up missing important window asks, reconcile PRs and releases, clear non-user review tasks, route failed tasks from composite parents, verify formal record sufficiency, reset stale claims, demote stale/unblocked tasks (exempting enduring component initiatives), record world-fact cancellations, and surface prepared user decisions to the daily note.
id: wf-reconcile
tags:
  - wf-template
  - reconcile
title: Graph Reconciliation Workflow
type: template
---

## What this step does

Reconciles the task graph with reality: advances open asks via groundwork, combines fragmented tracking tasks, backs up missing important window asks, syncs PRs and releases, clears agent work out of `review`, verifies completion records, settles failed tasks, prunes stale or falsified nodes, and surfaces prepared user decisions to today's daily note.

## Input contract

- Optional incremental cursor (`since: <cursor_utc>`).
- Access to the task graph, knowledge base, repository host, and session telemetry.

## Obligations

1. **Single-flight and scoped load**: Halt immediately if an active reconcile lock exists.
   - Load non-terminal active tasks (`high-value-prompt`/`prompt-sweep`, multi-part asks in `inbox`/`ready`, `status: review`) and `failed` tasks in the sweep window.
   - With `since: <cursor_utc>`, scope queries to changes since the cursor plus open `high-value-prompt` and `review` tasks; project summary fields before reading full bodies.
2. **Groundwork on open asks, consolidation, and ask backup**:
   - Treat direct user closures as self-authorizing (no receipts required; never demote or re-open).
   - Advance open `high-value-prompt` and multi-part asks out of `inbox`: check PKB first, then PRs/issues/releases and session traces; itemize completed vs. remaining parts, mark shipped/communicated items `done`, queue next agent steps via `/q`, update pure FYIs in place, and ignore unagreed external offers or mechanical read/check asks.
   - Reserve `status: review` (`assignee: user`) for completed-groundwork items (source summary, bold options inside one body including decline, `[Recommended]` rationale) hitting an explicit user hold, host action, or invariant boundary (`data-boundaries`, unruled merge, unbounded cost).
   - Combine fragmented tracking tasks serving one broader problem under a higher-level problem tracking task (wire `needs` without reparenting work parents or merging `in_progress`, hand-pinned, or dependency-breaking tasks), folding fixed items into a synthesis above open items.
   - Ensure qualitatively important covered-window asks (judged by substance, not length) appear once in that day's daily-note closing asks backup section without re-copying earlier days.
3. **Pull requests and releases**: Match PRs and releases via `pr_url`, task ID, branch, or title, querying PRs in repository batches and checking individuals only outside the batch window.
   - _Merged or shipped_: Mark `done` unconditionally on merge or communicated release (never wait to prove user installation/deployment); on partial deliveries, itemize remaining parts and queue next steps.
   - _Closed unmerged_: Surface for routing; never auto-complete or auto-requeue.
   - _Open_: Keep `done` work tasks in `done` while PRs stay open (never demote to `review`); route to `queued` or rework under the composite parent only on requested changes or failing checks.
4. **Clear non-user `review` tasks**: Never escalate mechanical "read/open/check" items or unagreed external asks; update pure FYIs in place.
   - Reserve `status: review` (`assignee: user`) solely for manual holds and completed-groundwork boundary holds (with source summary, in-body options including decline, and `[Recommended]` rationale); promote directed tasks parked solely by template/task class back to `queued`.
   - Transition all other `review` tasks out immediately: mark `done` if covered by an active QA/review `needs` task or uncovered with criteria met/FYI (queue `QA: <title>` if an open PR needs verification); move to `queued`/`partial` if agent work remains.
5. **Composite parent rollup**: When all open children under a bounded multi-session initiative reach `done`, transition the parent holding substantive acceptance criteria to `ready` for synthesis before closure. Exempt enduring component initiatives from empty-children (`k=0`) `done` closure; keep them in `status: ready`.
6. **Settle failed tasks from composite parents**: Inspect `## Report`, `reason`, and parent graph context on each `failed` task in the sweep window, then record the determination on the task:
   - Mint a remediation task with updated requirements and `needs`, cancel invalidated downstream tasks if the approach failed, or surface user-reserved parent choices (with options and recommendation) to `## With you`.
7. **Check that recorded evidence formally supports the claim**: Read what is written on the record (`pr_url`, `completion_evidence`, named artifact, `## Report`) and check formal sufficiency on its face without re-running work or re-reviewing diffs:
   - _Citation & sufficiency_: Verify cited `pr_url`, `completion_evidence`, or artifact addresses each criterion; otherwise return to `ready`/`queued` or `partial` with a review task.
   - _Liveness_: Discard moot items and mark `done` any task held open solely to prove post-release user installation/deployment once informed. When unrecorded facts force escalation, write a one-line question in `reason`, queue a one-level-up review task with `needs`, and release `partial`.
8. **Stale claims, demotions, and world-fact cancellations**:
   - Reset stale `in_progress` tasks (>24h unmodified with no active session/worker) to `queued` (never `ready`; never move an active claim backwards).
   - Demote unblocked dependents, landed siblings, stale `ready`/`queued` tasks (>14d, exempting enduring component initiatives), and invalidated assumption nodes to `inbox` with explanatory annotations (delegate structural repositioning to `/q`).
   - Cancel (`status: cancelled`, reason starting `not ripe:` quoting source evidence) only on affirmative body evidence: destroyed referent, superseded merge, falsified premise, or explicit user drop/retirement.
9. **Mutation and daily note contract**:
   - Write evidence/annotations to the body first, then mutate frontmatter `status` one task at a time (never bulk-mutate status, write `intent`/`priority`/`severity`, or read back error-free writes).
   - Touch the daily note strictly via `## With you` for prepared user decisions and the closing asks backup section (writing standalone to `YYYYMMDD-daily` or returning timestamped entries to an enclosing daily pipeline), never writing mutation logs or unowned sections.

## Output contract

One synthesized report stating the covered sweep window and next pickup boundary, naming task IDs (never bare counts) for:

- Rulings made without escalation, review tasks minted, consolidated tracking tasks, and items surfaced to `## With you` (with reviewer level, one-line question, and source task) or backed up to closing asks.
- Status changes made (with PR links) and failed-task determinations from composite parents.
- Tasks returned to `inbox`, tasks inspected and left untouched, and cancellations with trigger and quoted body evidence.

## When to include

Re-engagement after absence, periodic memory consolidation cycles, pre-briefing graph truth maintenance, or on-demand reconciliation.

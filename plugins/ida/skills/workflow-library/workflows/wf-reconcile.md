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

Reconciles the task graph with reality: advances open prompt-tracking and multi-part asks via groundwork, combines fragmented tracking tasks under problem-level tasks with checked-item synthesis, ensures missing qualitatively important window asks are backed up to the daily note's closing asks backup section, syncs PRs and releases, clears agent work out of `review`, verifies that recorded evidence formally supports completion claims, settles failed tasks from composite parents, prunes stale or falsified nodes, and surfaces prepared user decisions to today's daily note.

## Input contract

- Optional incremental cursor (`since: <cursor_utc>`).
- Access to the task graph, knowledge base, repository host, and session telemetry.

## Obligations

1. **Single-flight and scoped load**: Halt immediately if an active reconcile lock exists. Load non-terminal active tasks (including `high-value-prompt`/`prompt-sweep` tracking tasks, multi-part asks in `inbox`/`ready`, and `status: review`) plus `failed` tasks within the sweep window. When `since: <cursor_utc>` is given, scope queries to records changed or unblocked since the cursor alongside open `high-value-prompt` and `review` tasks; project summary fields before reading full bodies on candidate mutations.
2. **Groundwork on open asks, consolidation, and ask backup**: Treat direct user closures as self-authorizing (no receipts required; never demote or re-open). Advance open `high-value-prompt` and multi-part asks rather than leaving them in `inbox`: query the knowledge base first, then repository PRs/issues/releases and session traces; itemize completed vs. remaining parts; mark `done` when delivered and communicated; queue the next agent step via `/q`; update pure informational FYIs in place without escalating; never treat unagreed external asks as accepted user tasks or escalate mechanical "read/open/check" items; and set `status: review` (`assignee: user`) only when groundwork is complete (source summary, concrete options inside the single body including decline/do-nothing, and `[Recommended]` rationale) and progress genuinely waits on the user's own decision or host action. Combine fragmented tracking/ask tasks serving the same broader long-running problem one level higher under a problem-level tracking task (wiring `needs` to underlying work without reparenting work tasks or merging `in_progress`, hand-pinned, or dependency-breaking tasks), folding checked-off fixed items into a concise synthesis above remaining open items. For active asks originating in the covered window whose `## Ask` carries a qualitatively important user prompt (judged on substance, never length or pasted context), ensure that verbatim prompt appears once in that day's daily-note closing asks backup section without re-copying earlier days.
3. **Pull requests and releases**: Match PRs and releases to tasks via `pr_url`, task ID, branch, or title, querying PRs in repository batches and inspecting individual PRs only outside the batch window.
   - _Merged or shipped_: Mark `done` unconditionally on observed merge or shipped-and-communicated release (never hold open waiting to prove the user installed, pulled, or deployed a release); for partial deliveries, itemize completed vs. remaining parts and queue concrete next steps.
   - _Closed unmerged_: Surface for routing; never auto-complete or auto-requeue.
   - _Open_: Keep a `done` work task in `done` while its PR is open (never demote to `review` awaiting review or merge). Route to `queued` or a rework task under the composite parent only on requested changes or failing checks.
4. **Clear non-user `review` tasks**: Never escalate mechanical "read/open/check" items or unagreed external asks, and update pure informational FYIs in place. Reserve `status: review` (`assignee: user`) strictly for manual user holds and prepared user decisions whose source summary, concrete options in the single body (including decline/do-nothing), and `[Recommended]` rationale are recorded (leave untouched for `## With you` and `/decide`). Transition all other `review` tasks out immediately:
   - Covered by an active review or QA task (`needs` includes task ID): mark `done`.
   - Uncovered with an open PR: mark `done`, and queue `QA: <title>` (`needs: [<task_id>]`) when risk warrants verification.
   - Uncovered without a PR: inspect recorded evidence -- mark `done` if criteria are met or shipped (or for pure FYIs); move to `queued` (or `partial`) if agent work remains; or set `status: review` (`assignee: user`, with source summary, options, and recommendation) only if user input is required.
5. **Composite parent rollup**: When all open children under a bounded multi-session initiative reach `done`, transition a composite parent holding substantive acceptance criteria to `ready` for synthesis and verification before closing it. Exempt enduring component/subsystem initiatives (permanent capability anchors for standing infrastructure) from empty-children (`k=0`) `done` closure; keep them active in `status: ready`.
6. **Settle failed tasks from composite parents**: For each `failed` task in the sweep window, inspect `## Report` and `reason`, load its composite parent task and graph context, and record the determination on the failed task: mint a remediation task under the composite parent with updated requirements and `needs`, block or cancel invalidated downstream tasks if the approach failed, or escalate parent-scope/user decisions (with options and recommendation) to `## With you`.
7. **Check that recorded evidence formally supports the claim**: For returned work, read what is written on the record (`pr_url`, `completion_evidence`, named artifact, `## Report`) and check that recorded evidence formally supports the completion claim on its face without re-running work, re-reviewing PR code, or re-judging quality:
   - _Citation present_: cites `pr_url`, `completion_evidence`, or named artifact (do not fetch or inspect the artifact itself).
   - _Sufficiency_: cited evidence, as described, addresses each acceptance criterion; otherwise return to `ready`/`queued` or `partial` with a review task (never escalate unsupported claims).
   - _Liveness_: question is still live; discard moot items settled by events, and mark `done` any task held open solely to prove a post-release user act (installing, pulling, deploying) once shipped and communicated. When unrecorded facts or reserved fields force escalation, write a one-line question in `reason`, queue a one-level-up review task with `needs`, and release `partial`.
8. **Stale claims, demotions, and world-fact cancellations**:
   - Reset stale `in_progress` tasks (>24h unmodified with no active session or isolated worker) to `queued` (never `ready`; never move an actively claimed task backwards).
   - Demote unblocked dependents, siblings of landed work, stale `ready`/`queued` tasks (>14d, explicitly exempting enduring component/subsystem initiatives in `status: ready`), and invalidated assumption nodes to `inbox` with explanatory annotations (delegate non-consolidation structural repositioning to `/q`).
   - Cancel (`status: cancelled`, reason starting `not ripe:` quoting source evidence) only on affirmative body evidence: destroyed referent verified across refs, superseded by merge, falsified premise, or source-stated retirement / explicit user drop.
9. **Mutation and daily note contract**: Write evidence and annotations to the task body first, then mutate frontmatter `status` individually per task (never bulk-update status; never write `intent`, `priority`, or `severity`; do not read back after an error-free write). Interface with the daily note exclusively via `## With you` for prepared user decisions and the closing verbatim-asks backup section for missing important covered-window asks (written to `YYYYMMDD-daily` when standalone, or returned with verification timestamps to an enclosing daily-note pipeline) -- never write raw mutation logs, commit hashes, branch names, container IDs, duplicate backups, or other unowned sections.

## Output contract

One synthesized report stating the covered sweep window and next pickup boundary, naming task IDs (never bare counts) for:

- Rulings made without escalation, review tasks minted, consolidated tracking tasks, and items surfaced to `## With you` (with reviewer level, one-line question, and source task) or backed up to closing asks.
- Status changes made (with PR links) and failed-task determinations from composite parents.
- Tasks returned to `inbox`, tasks inspected and left untouched, and cancellations with trigger and quoted body evidence.

## When to include

Re-engagement after absence, periodic memory consolidation cycles, pre-briefing graph truth maintenance, or on-demand reconciliation.

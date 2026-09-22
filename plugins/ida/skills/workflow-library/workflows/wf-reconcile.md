---
description: Truth maintenance over the task graph -- reconcile merged PRs, record world-fact cancellations, and demote affected tasks to inbox.
id: wf-reconcile
tags:
  - wf-template
  - reconcile
title: wf-reconcile
type: template
---

## What this step does

Maintains truth over the task graph: establishes facts about in-flight work and landed changes, writes them back, and returns touched tasks to `inbox` for re-planning.

## Obligations

1. **Load active tasks**: Read non-terminal tasks across active statuses within the sweep window.
2. **Reconcile pull requests**: Match closed pull requests to tasks by structured indicators (`pr_url`, body task ID, recorded branch, `polecat/` prefix, exact title).
   - **Merged PRs**: Write `status: done` unconditionally on an observed merged PR (`pr_url`, merge timestamp, branch). Do not re-judge acceptance criteria.
   - **Closed without merge**: Surface for routing; never auto-complete or auto-requeue.
3. **Aged tasks and stale claims**: Route aged items (>90d) and suspect claims to `status: review` with observed evidence for Sara; never write `done` on non-PR evidence; never reset claims to `ready`.
4. **Demote affected tasks**: Set unblocked dependents, siblings of landed work, rot (>14d in `ready`/`queued`), and invalidated assumption nodes to `status: inbox` with explanatory annotations.
5. **Cancel on world-facts**: Cancel only on affirmative evidence recorded in the node body:
   - _Referent destroyed_: target artifact was deleted, verified across checkouts and refs.
   - _Superseded by merge_: merged PR mooted or settled the task's question.
   - _Premise falsified_: named assumption or precondition no longer holds.
6. **Two-step mutation contract**: Write annotation/evidence to markdown body first, then mutate frontmatter `status` via `pkb.update_task` (never `batch_update`), then read back to confirm status.
7. **Daily note boundary**: The pass does not append to or own daily-note sections. Each daily-note section has one owning mechanism (`## Left over from today` owned solely by `wf-prompt-settle`; `## Asks filed` owned solely by capture intake; daily note structure owned by `tpl-daily`). Reconcile emits its result to the caller and must not append unowned sections to daily notes.

## Must not

- Must not write `done` on any evidence other than an observed merged PR.
- Must not certify work complete or judge acceptance criteria after merge (Sara's outcome).
- Must not reset abandoned claims to `ready` or forward uncertified work to dispatcher.
- Must not close or cancel without required evidence written to the node body.
- Must not cancel on missing paths appearing only in narrative or provenance prose.
- Must not re-open or adjudicate settled human decisions or merged pull requests.
- Must not annotate a body with status changes without mutating frontmatter `status`.
- Must not use `batch_update` for status mutations or demotions.
- Must not prune, re-plan, or restructure (delegate repositioning to `/q`).
- Must not write `focus_score`, `intent`, `priority`, or `severity`.
- Must not promote work into `queued`.
- Must not append unowned sections to the daily note.

## Output contract

Emit one synthesized result:

1. Decisions requiring human attention (`review` tasks, forks).
2. Status changes made (with task IDs and PR links).
3. Tasks found and left alone.
4. Tasks returned to `inbox`.
5. Cancellations as a distinct category (task ID, trigger fired, verbatim evidence written to body).
6. Name IDs for every touched task (no bare counts).
7. State the covered sweep window and what the next sweep should pick up.

## When to include

Re-engagement after absence, within periodic consolidation cycles (`remember`), before daily note composition (`tpl-daily`), or on-demand graph truth maintenance.

---
description: "Crew (needs PKB, GitHub and trace access): bring the task graph back in line with reality -- advance open asks, sync PRs and releases, clear agent work out of review, settle failed tasks, reset stale claims, and surface prepared user decisions to the daily note."
id: wf-reconcile
tags:
  - wf-template
  - reconcile
title: Graph reconciliation
type: template
---

## What this step does

Makes the graph true to the world. Acts only on what the record shows; never re-runs or re-reviews work.

## Obligations

1. **Single flight**: stop if another reconcile holds the lock. With `since: <cursor>`, look only at changes since then plus open prompt-tracking and `review` tasks.
2. **Open asks**: for each open tracked ask, check the PKB, then PRs, issues, releases and traces; mark finished parts `done` and queue the next agent step via `/q`. A closure the user made stands. Combine fragmented tracking tasks serving one problem under one tracking task. Make sure each important ask in the window appears once in that day's daily-note closing asks section.
3. **PRs and releases**: match by `pr_url`, task id, branch or title. Merged or released: `done` at once, never waiting for proof of installation. Closed unmerged: surface for routing. Open: leave `done` work tasks `done`; requeue only on requested changes or failing checks.
4. **Review status**: `review` with `assignee: user` is only for a user's own hold or a prepared decision at a real boundary (options, a recommendation). Move every other `review` task to `done`, `queued` or `partial`. Never escalate "read/check this" items.
5. **Composite parents**: when all children are `done`, set the parent `ready` for synthesis; enduring component parents stay `ready`.
6. **Failed tasks**: read the report and reason, then queue a remediation task, cancel what the failure invalidated, or surface a user-reserved choice to `## With you`.
7. **Evidence on its face**: a `done` whose recorded evidence does not address its criteria goes back to `queued` or `partial`. A task held open only to prove a user installed something is `done`.
8. **Stale and moot**: reset `in_progress` tasks untouched for 24 hours with no live session or worker to `queued`. Demote stale `ready`/`queued` tasks (over 14 days, enduring components exempt) to `inbox` with a note. Cancel only on evidence in the body (referent gone, superseded, premise falsified, user dropped it), with a reason starting `not ripe:`.
9. **Writes**: body first, then status, one task at a time; no bulk status changes, no read-backs. In the daily note touch only `## With you` and the closing asks section.

## Output contract

One report: the window covered and the next cursor, then task ids for every ruling, status change (with PR links), surfaced decision, demotion and cancellation.

## When to include

Re-engagement after absence, before a briefing, or on demand.

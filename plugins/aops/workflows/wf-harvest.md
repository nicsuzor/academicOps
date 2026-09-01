---
alias:
- temp_e8ba6709
- closed-task-harvest
category: process
created: 2026-08-27T13:05:04.670552301+00:00
description: 'Select for a bounded, batched sweep that harvests durable knowledge out of accumulated terminal (done/cancelled) task bodies and retires each body to a stub or a Goal/Acceptance-Criteria/Receipt shape. Not for a task that has just closed — that is the forward extraction duty fired at closure — and not for anything still open.'
id: wf-harvest
last_modified: 2026-09-01T00:00:00+00:00
modified: 2026-09-01T00:00:00+00:00
permalink: wf-harvest
tags:
- wf-template
- process
- consolidation
- pkb-hygiene
- extraction
- task-hygiene
title: wf-harvest
type: template
---

# wf-harvest — retrospective knowledge harvest from closed tasks

**Covers:** a backlog of terminal task bodies that has accumulated past what the graph should
carry. A closed body is finished, so extracting from it cannot disturb work in flight — that is
what makes it eligible, not its age.

**Technique lives in `remember`** (`plugins/aops/skills/remember/`), consolidation mode: search for
the canonical destination note, synthesise into it, verify recoverability. This template states
only what the sweep obliges — selection, batch bound, retirement shape, and the halts — never how
to extract.

**Truth maintenance is `reconcile`'s job, not this one's** (`plugins/aops/skills/reconcile/`). If
the terminal set itself is suspect — a status that may not reflect reality — run reconcile first;
this template only ever acts on bodies genuinely at `done` or `cancelled`.

## Selection

- Terminal status only: `done` or `cancelled`. Non-terminal work is out of scope.
- Age is a settling window, never an admission reason — elapsed time is not evidence a body is spent.
- A batch is at most 20 nodes. Stop at the bound even if extraction is going well — the bound is the
  safety mechanism, not a target to fill.
- Stratify rather than taking the head of a list: largest bodies, modal bodies, and a thematically
  clustered set.
- Cluster siblings before extracting: one canonical destination note per cluster, not one dump per
  task.

## Procedure

1. Record the store's git SHA before the batch's first write, on the sweep's own record.
2. Harvest each node through `remember` consolidation mode, destination-first — the durable content
   exists at a named note before the source body is touched. Default `dry_run=true` for a batched
   pass. A node that cannot write its destination halts and reports; it never touches the source.
3. Verify by recoverability: every fact, number, path, date, and decision in the old body is
   reachable from the new body within one `[[wikilink]]` hop. Name any loss explicitly — reporting a
   loss is a pass, hiding one is the fail. An empty extraction yields no verdict, and the node is not
   eligible for retirement.
4. Confirm zero inbound references through PKB search tools before retiring anything — never grep or
   touch the PKB store's filesystem directly.
5. Retire to a shape set by terminal status. `cancelled` collapses to a stub — title, status, closing
   date, one-line reason, links to whatever received the harvest. `done` collapses to Goal /
   Acceptance Criteria / Receipt — the goal in a sentence, criteria restated verbatim, a receipt
   checking off what was actually met and linking the evidence. No back-and-forth, no reconciliation
   history, no code. A node whose extraction was empty is left intact — nothing is retired without a
   destination to point at.
6. Append the receipt per node as the batch runs, not assembled at the end: the pre-batch SHA,
   destination ids that received harvest, end-state counts, everything skipped and why.

## Halts

Any one of these stops the batch and reports, rather than continuing past it: one node holding
something unreachable from its new body; a body collapsed on an empty-extraction verdict; yield
disproportionate to destruction (large deletion, thin knowledge gained); an insight not verifiable
against the source body; signs of a mechanical pass rather than a judged one (byte-identical output
across unrelated nodes, generic fallback text, unbalanced `[[wikilinks]]`).

## What this step never does

Never invents a lesson to justify a write — "nothing durable here" is a valid finding, and a node
with nothing to extract is left with no summary, no generic bullet, and no retirement. Never deletes
a referenced node. Never rewrites a primary episodic record reached from a task. Never changes
`status`, `id`, `parent`, `depends_on`, or `contributes_to` on a node it harvests, and never picks a
winner between contradicting sources — both are surfaced, not resolved.

## When to include

On explicit request, or inside a scheduled consolidation cycle, once terminal bodies have
accumulated past what the graph should carry. Skip for a task that has just closed, and for any ask
that turns out to mean live work.

## Exit

Every candidate sits in exactly one end state: harvested and collapsed to its retained shape,
harvested and deleted (zero inbound references, three-step deletion run), left intact with an
empty-extraction finding stated, or skipped with a stated reason. A node whose harvest was written
but whose retirement did not run is a failure of this process, not a partial success — and a node
retired without a verified harvest is the failure it exists to prevent.

---
alias:
- wf-signoff-brief-wf-signoff-brief
- wf-signoff-brief
created: 2026-07-11T12:41:54.180479237+00:00
id: wf_signoff_16985750
last_modified: 2026-07-28T03:01:21.924482832+00:00
modified: 2026-07-28T03:01:21.924481029+00:00
permalink: wf-signoff-brief
tags:
- wf-template
- v0.4
- module-f
- workflow
- planner-data
title: wf-signoff-brief
type: template
---

## wf-signoff-brief — step: one-page human-facing summary

**Sequence position**: near-final step, after the review lenses have run, before or alongside [[wf_capstone_73d7ce86]].

## What this step does

Produces the one-page prose summary for Nic when a full task or epic completes: what was delivered, against what it was asked to do, with every checked claim carrying a resolvable link. This is the human-facing capstone of the workflow — not a re-review, a synthesis of what the other steps already established (per [[note_296e5520]] §2: "Sign-off brief for Nic on full tasks/epics: one page, prose, every delivered/checked claim carrying a resolvable link").

## Output contract

The signoff brief must:

- Fit on one page/screen — prose, not a bullet dump of every subtask.
- State what was delivered and link to it (PR, doc id, artifact).
- Name every load-bearing claim ("this works," "this is complete," "this matches the spec") with its resolving evidence — command output, file:line, or a linked review verdict from an earlier step. No claim without a link or an honest "unverified."
- State plainly what wasn't done or couldn't be verified, if anything — a clean brief with a stated gap is more useful than a brief that hides one.

## When to include

Every task/epic that reaches human sign-off — i.e., anything Nic needs to read to decide "is this actually done." Skip for subtasks that feed into a larger epic's own signoff (avoid nested briefs); write one at the level a human actually reviews. Low-stakes/routine work may fold this into the `release_task` summary rather than a separate document; high-stakes work gets its own document.

## Related

- [[wf_capstone_73d7ce86]] — the completeness audit that typically precedes/accompanies this brief
- [[note_296e5520]] — SSoT, §2

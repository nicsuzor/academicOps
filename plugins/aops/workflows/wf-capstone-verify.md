---
alias:
- wf-capstone-verify-wf-capstone-verify
- wf-capstone-verify
created: 2026-07-11T12:41:59.893752009+00:00
id: wf_capstone_73d7ce86
last_modified: 2026-07-28T03:01:21.917698409+00:00
modified: 2026-07-28T03:01:21.917696646+00:00
permalink: wf-capstone-verify
tags:
- wf-template
- v0.4
- module-f
- workflow
- planner-data
title: wf-capstone-verify
type: template
---

## wf-capstone-verify — step: epic-closure completeness audit

**Sequence position**: final gate, immediately before an epic's terminal status flips to done/merge_ready.

## What this step does

Confirms the complete set of independent reviews required by the workflow actually ran and actually cover what they claim to, before anyone closes the epic. This is not a new review — it's an audit that the review set is complete: [[wf_23a5a1c6]]'s premise judgment, [[wf_boundary_7088958d]]'s rules check, [[wf_qa_b4b7f9c5]]'s fitness check, and any [[wf_refine_6ef85da2]] rounds all landed, with real evidence, not just checked boxes. This operationalises the invariant in [[note_296e5520]] §2: "the only invariant [across dynamic review altitude] is a complete set of independent reviews before an epic is _done_."

## Output contract

The capstone-verify handback must state:

- A checklist of which lenses ran, by whom, with a link to each verdict.
- Any lens that's missing, stale (predates a late change to the artifact), or was self-reviewed where independence was required — named explicitly, not silently accepted.
- Final verdict: epic genuinely ready to close, or the specific gap blocking closure.

## When to include

Every epic before its terminal status flips to done/merge_ready. Single small tasks with no subtask fan-out can skip this (there's nothing to reconcile) — it exists specifically for epics composed of multiple reviewed subtasks where nobody has checked that the pieces actually add up to done.

## Related

- [[wf_signoff_16985750]] — the human-facing summary this audit typically precedes/accompanies
- [[wf_boundary_7088958d]], [[wf_qa_b4b7f9c5]], [[wf_refine_6ef85da2]] — the review set being audited for completeness
- [[note_296e5520]] — SSoT, §2 (the invariant this step enforces)

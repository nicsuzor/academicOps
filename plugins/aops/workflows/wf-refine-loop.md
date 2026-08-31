---
alias:
- wf-refine-loop-wf-refine-loop
- wf-refine-loop
created: 2026-07-11T12:41:48.354403488+00:00
id: wf_refine_6ef85da2
last_modified: 2026-07-28T03:01:21.923419651+00:00
modified: 2026-07-28T03:01:21.923417507+00:00
permalink: wf-refine-loop
tags:
- wf-template
- v0.4
- module-f
- workflow
- planner-data
- identity-separation
title: wf-refine-loop
type: template
---

## wf-refine-loop — step: convergence loop between drafter and reviewer

**Sequence position**: follow-up to a fail/revise verdict from [[wf_boundary_7088958d]] or [[wf_qa_b4b7f9c5]] (or [[wf_fact_b828c939]]).

## What this step does

The convergence loop between the drafter and the reviewer(s): reviewer raises the highest-priority concern with a proposed resolution, drafter addresses it or explicitly overrides it with a stated reason, repeat until resolved or overridden. Prevents both rubber-stamping (reviewer must propose a fix, not just flag) and endless review (converges by resolution, capped by a soft round limit as a safety valve, not a design target).

## Output contract

The refine-loop handback must state:

- Round-by-round log: concern raised → resolution applied or override reason given.
- Final state: all concerns resolved/overridden, or escalated to human with the specific unresolved disagreement named.
- Round count, so downstream review can see whether this converged quickly or ground through the safety cap.

## When to include

Only for work that failed a [[wf_boundary_7088958d]] or [[wf_qa_b4b7f9c5]] pass and needs iteration — this step doesn't run standalone, it's the follow-up to a fail/revise verdict from those steps. Low-stakes work skips it entirely (a single revise-and-resubmit by the executor is enough). High-stakes work (grant/framework change) may need multiple rounds; the soft cap (e.g. 5-7 rounds) exists to force human escalation on genuine disagreement, not to bound normal work.

## Identity separation (binding)

The drafter revises; the **reviewer that raised the concern re-reviews** — same reviewer≠executor pairing as [[wf_boundary_7088958d]], **wired by the planner at decomposition** (distinct assignee, `depends_on` edge from revision back to re-review), **attested by the reviewer on each round**. This is **not enforced by any mechanical gate** — per [[note_296e5520]] §0, verdicts are always agent judgment, never a server-side check. If the same agent is filling both roles because no second reviewer is available, the handback must say so explicitly rather than silently self-approving — an honest gap beats a fake pass.

## Related

- [[wf_boundary_7088958d]], [[wf_qa_b4b7f9c5]] — the checks that trigger this loop
- [[wf_635eab64]] — what's being revised
- [[note_296e5520]] — SSoT, §0 and §2

---
alias:
- wf-fact-check-wf-fact-check
- wf-fact-check
created: 2026-07-11T12:41:27.618109282+00:00
id: wf_fact_b828c939
last_modified: 2026-07-28T03:01:21.919656746+00:00
modified: 2026-07-28T03:01:21.919655313+00:00
permalink: wf-fact-check
tags:
- wf-template
- v0.5
- module-f
- workflow
- planner-data
title: wf-fact-check
type: template
---

## wf-fact-check — step: verify claims against sources

**Sequence position**: runs against a draft ([[wf_635eab64]]), parallel to or ahead of [[wf_boundary_7088958d]]/[[wf_qa_b4b7f9c5]].

## What this step does

Checks factual and evidentiary claims in the draft against their sources — citations resolve, quoted numbers match the source, described behavior matches actually-observed behavior (not assumed), links are live and point where claimed. This is a narrower, more mechanical-adjacent check than [[wf_qa_b4b7f9c5]]: it verifies claims are TRUE, not that the work is GOOD.

## Output contract

The fact-check handback must state, per claim checked:

- The claim, the source checked, and the resolving link/command/output.
- PASS (claim verified against source) or FAIL (claim doesn't hold) — no third state; a claim that couldn't be checked is a FAIL with the reason recorded ("source unavailable", "couldn't reproduce").
- A summary count: N claims checked, N passed, N failed — so a downstream reviewer doesn't have to re-derive coverage.

## Record surface (mandatory)

The ledger, the work log, and the reasoning behind them are working records. Their durable home is the PKB, attached to the commissioning task — never a public or shared artifact repository. The repository under review receives only the completed work itself and, where the surrounding process requires a report (a PR review gate, an editor sign-off), a summary — verdict and counts, with a pointer to the task that holds the record — not the internal ledger or narrative. This applies to every project, not any one repo: a reasoning log committed to a shared repo publishes the team's internal deliberations alongside the work.

## When to include

Any artifact making factual, empirical, or citation-bearing claims: research writing, grant text, anything citing data or prior work, code claiming a behavior ("this fixes X" — did it?). Skip for pure judgment calls or stylistic work with no checkable claims (routine correspondence, brainstorming). When in doubt, include it — it's cheap relative to a wrong claim shipping. Low-stakes email or routine notes: skip. Grant/framework/manuscript work with cited claims: mandatory.

## Related

- [[wf_635eab64]] — the artifact being checked
- [[wf_qa_b4b7f9c5]] — the broader "does it work / is it good" check, distinct from this narrower truth check
- [[note_296e5520]] — SSoT

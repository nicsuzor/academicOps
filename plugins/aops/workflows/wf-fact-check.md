---
alias:
- wf-fact-check-wf-fact-check
- wf-fact-check
- wf_fact_b828c939
category: gate
created: 2026-07-11T12:41:27.618109282+00:00
description: 'Child workflow for [[wf-qa]]''s evaluate slot: verify factual, empirical, and citation-bearing claims in a draft against their sources. Select for any artifact making checkable factual claims; skip for pure judgment calls or stylistic work with nothing checkable.'
id: wf-fact-check
last_modified: 2026-09-01T00:00:00+00:00
modified: 2026-09-01T00:00:00+00:00
permalink: wf-fact-check
tags:
- wf-template
- v0.5
- module-f
- qa
title: wf-fact-check
type: template
---

## wf-fact-check — verify claims against sources

Fills [[wf-qa]]'s evaluate slot for factual, empirical, and citation-bearing claims.

## What this step does

Checks factual and evidentiary claims in a draft against their sources — citations resolve, quoted
numbers match the source, described behaviour matches what was actually observed rather than
assumed, links are live and point where claimed. This is narrower and more mechanical than
[[wf-qa]]'s general judgment: it verifies claims are TRUE, not that the work is GOOD.

## Output contract

The fact-check handback must state, per claim checked:

- The claim, the source checked, and the resolving link/command/output.
- PASS (claim verified against source) or FAIL (claim doesn't hold) — no third state; a claim that couldn't be checked is a FAIL with the reason recorded ("source unavailable", "couldn't reproduce").
- A summary count: N claims checked, N passed, N failed — so [[wf-qa]] doesn't have to re-derive coverage.

## Record surface (mandatory)

The ledger, the work log, and the reasoning behind them are working records. Their durable home is the PKB, attached to the commissioning task — never a public or shared artifact repository. The repository under review receives only the completed work itself and, where the surrounding process requires a report (a PR review gate, an editor sign-off), a summary — verdict and counts, with a pointer to the task that holds the record — not the internal ledger or narrative. This applies to every project, not any one repo: a reasoning log committed to a shared repo publishes the team's internal deliberations alongside the work.

## When to include

Any artifact making factual, empirical, or citation-bearing claims: research writing, grant text, anything citing data or prior work, code claiming a behavior ("this fixes X" — did it?). Skip for pure judgment calls or stylistic work with no checkable claims (routine correspondence, brainstorming). When in doubt, include it — it's cheap relative to a wrong claim shipping.

## Related

- [[wf-qa]] — the parent gate this fills the evaluate slot for
- [[wf-loop]] — iteration wrapper, where the same claims must be re-checked across rounds

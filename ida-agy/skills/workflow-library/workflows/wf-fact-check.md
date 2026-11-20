---
alias:
  - wf-fact-check
description: Fills evaluate slot for factual, empirical, and citation-bearing claims against primary sources. Skip for pure judgment or stylistic work.
id: wf-fact-check
tags:
  - wf-template
  - qa
title: Fact-Check Verification
type: template
---

## What this step does

Checks factual and evidentiary claims in a draft against primary sources -- citations resolve, quoted numbers match the source, described behavior matches direct observation rather than assumption, and links are live and point where claimed. Narrower and more targeted than full empirical QA: verifies claims are **true**, not whether the work meets broader design goals.

## Output contract

The fact-check handback states, per claim checked:

- The claim, the source checked, and the resolving link, command, or output.
- `PASS` (verified against source) or `FAIL` (contradicted or unverified -- including `"source unavailable"` or `"couldn't reproduce"`), with no third state.
- A summary count (`N claims checked, N passed, N failed`) so downstream evaluators do not re-derive coverage.

## Record surface (mandatory)

Working ledgers, logs, and intermediate reasoning belong on the commissioning PKB task -- never committed to a public or shared artifact repository. The repository under review receives only the completed work and, where required by a review requirement, a concise summary (verdict, counts, and a task pointer) rather than internal deliberation logs.

## When to include

Any artifact making factual, empirical, or citation-bearing claims (research writing, grant text, data citations, or code claiming a concrete behavior fix).

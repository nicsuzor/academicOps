---
alias:
  - wf-fact-check
description: Fills wf-qa evaluate slot for factual, empirical, and citation-bearing claims against primary sources. Skip for pure judgment or stylistic work.
id: wf-fact-check
tags:
  - wf-template
  - qa
title: wf-fact-check
type: template
---

## What this step does

Fills `[[wf-qa]]`'s evaluate slot to verify factual, empirical, and citation-bearing claims against primary sources. Ensures citations resolve, values match sources, and claimed runtime behaviors were directly observed.

## Output Contract

For each claim evaluated, report:

- **Claim and source**: Quoted statement and primary source pointer.
- **Verdict**: Binary `PASS` or `FAIL` (record failure reason if unresolvable).
- **Summary count**: Number of claims checked, passed, and failed.

Durable ledgers and detailed reasoning logs attach to the commissioning PKB task. Pull requests and shared repositories receive only the final summary counts and overall verdict.

## When to Include

Include for research drafts, grant proposals, benchmark reports, or code claiming specific bug fixes. Skip for purely stylistic edits or exploratory discussions with no empirical claims.

---
alias:
  - wf-fact-check
description: "Review: check the factual, empirical and citation claims in a draft against their sources. Skip for pure judgement or style."
id: wf-fact-check
tags:
  - wf-template
  - qa
title: Fact check
type: template
---

## What this step does

Checks that claims are true: citations resolve, numbers match their source, described behaviour matches what is observed, links go where they say.

## Output contract

Per claim checked: the claim, the source and what it showed, and `PASS` or `FAIL` (contradicted or unverifiable counts as `FAIL`). Then a count: checked, passed, failed. Where defects are clearly fixable without ambiguity, fix them in place if write permissions and instructions permit; otherwise state the exact fix. Working notes go where the composed workflow and task specify, never in the artifact under review.

## When to include

Any artifact whose value rests on factual or citation claims.

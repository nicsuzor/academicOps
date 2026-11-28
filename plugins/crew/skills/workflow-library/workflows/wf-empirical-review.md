---
alias:
  - wf-empirical-review
  - wf-performance-review
description: "Review: measure how agents, workflows, checks or tools perform, from the trace store of real sessions only -- never synthetic, constructed or simulated runs, or earlier reports' figures."
id: wf-empirical-review
tags:
  - wf-template
  - evaluation
  - performance
  - traces
title: Performance review on real traces
type: template
---

## What this step does

Answers how well something we run performs (a check's catch rate, a workflow's cost, the effect of a change) from what real sessions did.

## Evidence

- Every figure comes from spans of real sessions in the trace store, read through its query skill. Name the store, project and UTC window first.
- Nothing stands in for them: no synthetic, seeded or simulated runs, no sessions started to make test data, no figures carried over from earlier reports or audits.
- A before/after comparison uses real traffic either side of the change.
- Gaps bound the answer. State them first; if what remains cannot answer the question, stop and report the store's coverage. Never fill a gap.

## Procedure

1. Before reading spans, write down which figure answers the question.
2. Check the store's coverage for the window.
3. Measure, citing a span or session for every item, and label each figure measured, inferred or judged.

## Output contract

A report: frame and gaps first, then each figure with its trace locators, then a conclusion bounded by the gaps.

## When to include

Any ask to measure, evaluate or compare how agents, workflows, checks, tools or the framework perform.

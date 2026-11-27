---
alias:
  - wf-empirical-review
  - wf-performance-review
description: Universal empirical review of how agents, workflows, checks, tools or the framework perform -- measured only on the store of observed traces from real sessions, read through a trace-store query skill; never on synthetic, constructed, generated or simulated runs, reported figures, or earlier audits. Gaps in the traces narrow or halt the conclusion and are never filled.
id: wf-empirical-review
tags:
  - wf-template
  - evaluation
  - performance
  - empirical
  - traces
title: Empirical Performance Review on Observed Traces
type: template
---

## What this step does

Answers how well something we run actually performs (a check's catch rate, a workflow's cost, an agent's delegation, the effect of a change) from what real sessions did. The observed-trace store exists so that these questions are answered from the record of real work: every empirical review of performance is done on it.

## Evidence: observed traces only

- **The traces are the population.** Every figure derives from spans of real sessions in the environment's trace store, read through its trace-query skill (for Arize Phoenix, `ida:phoenix`). Name the store, project and UTC window before any figure.
- **Nothing stands in for them.** Synthetic, constructed, generated, seeded, mocked or simulated runs; sessions started to produce test data; hand-written cases; figures from earlier reports, audits, task records or agent summaries; and saved extracts that do not join item by item to their source spans are not evidence of performance. None is used, whether as the data, a top-up, a fallback or a pilot.
- **Earlier labels are claims.** A prior audit's codings or verdicts may be compared against, never carried over: every item is read afresh from its spans.
- **Gaps bound the answer.** Where the store lacks a window, misses spans, or holds too few traces, state the gap first and bound every figure by it. If what remains cannot answer the question, halt: report the shortfall with the store's own coverage (earliest and latest record, counts) and release `blocked`. Never fill the gap.
- **Changes are compared on real traffic.** A before/after review compares traced windows of real use either side of the change, anchored at install time. If the after window holds too little traffic, release `blocked` until it does.

## Input contract

- **Question**: the asker's words, verbatim with their locator.
- **Target and window**: what ran (feature, agent, workflow, check) and the UTC window or windows.
- **Trace-store access**: through its query skill. If the store is unreachable, halt, report the response verbatim and release `blocked`.

## Procedure

1. **Pre-register**: before reading spans, write which figure answers the question and what each outcome would look like.
2. **Coverage gate**: query the store's coverage for the window (earliest and latest span, session counts, missing or unpriced spans) and record every gap.
3. **Measure from spans**: cite a span or session locator for every item, and label every figure `measured`, `inferred` or `judged`.

## Output contract

A durable report: the frame (store, project, window) and coverage gaps first; each figure with its trace locators and label; and a conclusion bounded by the gaps. A figure without a trace locator is not reported.

## When to include

Any ask to review, evaluate, measure, benchmark, audit or compare how agents, workflows, checks, tools or the framework perform, including value-of-check studies, cost and efficiency reviews, and before/after comparisons of a change.

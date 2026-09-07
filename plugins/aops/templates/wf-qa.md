---
alias:
  - wf-qa
category: gate
description: Universal QA gate -- assemble criteria, evaluate through a named child workflow, and return a per-criterion verdict with evidence.
id: wf-qa
tags:
  - wf-template
  - qa
title: wf-qa
type: template
---

## What this step does

Universal QA parent gate establishing criteria, evaluator independence, and evidence standards. Evaluation mechanics are delegated to the child workflow filling the evaluate slot.

## 1. Assemble Criteria

Record acceptance criteria verbatim from the task specification before inspecting outputs. Criteria formulated after observing results do not constitute valid gates.

## 2. Evaluate Slot

The brief fills this slot with the appropriate specialized child workflow:

| Artifact Type                          | Child Workflow      |
| -------------------------------------- | ------------------- |
| Rendered UI, layouts, or charts        | `[[wf-qa-visual]]`  |
| Empirical, factual, or citation claims | `[[wf-fact-check]]` |
| Machine-checkable code behavior        | `[[wf-tdd]]`        |

The evaluator must be independent of the artifact author. For repetitive convergence, wrap with `[[wf-loop]]`.

## 3. Per-Criterion Confirmation

Return an itemized report containing:

- **Criterion**: Verbatim requirement from step 1.
- **Status**: Binary `MET` or `UNMET` (record reason if uncheckable).
- **Evidence**: Pinpoint citation (`file:line`, command output, visual region).

Emit overall verdict (`PASS`, `FAIL`, or `ESCALATE` for ambiguous criteria) and summary counts (checked, met, unmet).

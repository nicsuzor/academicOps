---
alias:
  - wf-review
  - wf-multi-agent-review
description: Universal composite review workflow -- orchestrates independent parallel review across strategic fit, rule compliance, and quality assurance, reconciling findings into a single unified verdict.
id: wf-review
tags:
  - wf-template
  - review
  - composite
  - gate
title: Multi-Agent Review Workflow
type: template
---

## What this step does

Universal composite review workflow: coordinates parallel, independent review across three non-overlapping review roles -- strategic fit, rule compliance, and runtime quality assurance -- and reconciles their findings into a single actionable verdict.

## Input contract

The invoking workflow provides:

1. **Target artifact** -- the file, diff, PR reference, or specification under review.
2. **Acceptance criteria** -- explicit requirements and constraints from the commissioning task.
3. **Strategic context** -- parent task, target objectives, or problem definition.

## Composite Stages

A composite workflow specifies its stages by contract expectations in order:

1. **Strategic fit evaluation**: An independent strategic evaluation situating the artifact against parent objectives, parsimony, and precedent, returning an explicit `FIT` or `MISFIT` verdict.
2. **Rule compliance evaluation**: An independent rule-compliance evaluation testing mechanisms and decisions against governing axioms and rules without running test suites or probes, returning `APPROVE`, `SUGGEST`, `REVISE`, or `REJECT`.
3. **Quality assurance evaluation**: An independent runtime quality evaluation executing test suites, verifying red-to-green failure traces, running live probes, and auditing empirical evidence, returning `PASS`, `REVISE`, or `FAIL`.
4. **Reconciliation and write-back**: Synthesis of findings into a unified findings table and final verdict (`APPROVE`, `MINOR CHANGES`, `REVISE`, or `REJECT`), recorded persistently to the artifact's tracking record.

## Output contract

A unified review report containing:

- The itemized findings table mapping issues to reviewer roles, feedback, and severities.
- The reconciled overall verdict.
- Persistent write-back to the artifact's task record or review surface.

## When to include

Any major milestone, specification, design proposal, or pull request requiring independent multi-perspective verification prior to merge or release.

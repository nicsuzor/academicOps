---
alias:
  - wf-strategic-fit
  - wf-fit-check
description: Universal strategic-fit review gate -- evaluate candidate artifact, change, or proposal against parent objectives, parsimony, precedent, and lifecycle coherence, returning an explicit FIT or MISFIT verdict.
id: wf-strategic-fit
tags:
  - wf-template
  - review
  - strategic-fit
  - strategy
  - gate
title: Strategic-Fit Review
type: template
---

## What this step does

Universal strategic-fit review gate: situates an artifact within its objective hierarchy, tests necessity and parsimony, detects competing alternatives, and evaluates lifecycle coherence across the task graph.

## Input contract

Draws its brief from the shared review briefing in `wf-review`. Additional role-specific inputs:

- **Graph context** -- active tasks, competing proposals or PRs, and relevant topic notes.

## Procedure

1. **Objective alignment** -- verify whether the artifact serves the claimed parent target or objective, identifying any unrequested scope drift or mission creep.
2. **Parsimony and necessity** -- determine whether the mechanism should exist at all, or whether an existing tool, native capability, or competing proposal already solves the need more simply.
3. **Precedent and systemic coherence** -- evaluate consistency with established architectural patterns and verify that task lifecycle dependencies do not deadlock downstream workflows.
4. **Determine boundaries** -- operates strictly on high-level strategic alignment and lifecycle coherence. Does not inspect code for axiom violations (the rule-compliance role) and does not execute runtime tests or probes (the QA role).
5. **Issue verdict**: exactly one of `FIT` or `MISFIT`. A `MISFIT` identifies the redundant machinery, competing solution, or lifecycle conflict.

## Output contract

The structured review artifact returning:

- **Verdict**: `FIT` or `MISFIT`.
- **Strategic assessment**: evaluation of objective alignment, parsimony, and systemic coherence.
- **Identified conflicts**: competing proposals, unnecessary abstractions, or lifecycle deadlocks (if any).

## When to include

Any workflow proposing an architecture, specification, design change, or feature addition before detailed implementation or final sign-off.

---
description: Investigate problem space, prior work, existing systems, and candidate approaches with trade-offs grounded in primary evidence before specification or execution.
id: wf-research
tags:
  - wf-template
  - research
title: Research Investigation Workflow
type: template
---

## What this step does

Investigates a problem space, existing system or literature context, constraints, and external prior art before specification or commitment. Compares viable approaches and grounds recommendations in primary evidence.

## Procedure

1. **Define scope**: Frame primary research questions and explicit unknowns.
2. **Investigate existing context**: Examine relevant codebase, data structures, literature, dependencies, and operational constraints.
3. **Survey external options**: Evaluate established libraries, protocols, methods, or prior art.
4. **Compare alternatives**: Assess candidate approaches against trade-offs (complexity, performance, validity, maintenance, coupling, migration cost).
5. **Document findings**: Cite primary evidence (`file:line`, command outputs, literature or external references) and state a recommended direction.

## Output contract

A concise, channel-neutral research artifact leading with the answer and recommendation followed only by the evidence needed to verify them (persisted human-facing research artifacts use clear Markdown; internal agent-to-agent handbacks report solely in clean Argdown prose per `premise-check`, stating the original ask upfront and quoting deciding primary evidence inline):

- Answers to primary research questions with pinpoint citations.
- Comparison of candidate approaches with trade-offs and active constraints.
- Recommended approach and rationale.

## Composition

For open design questions or competing alternatives, retain candidate options in the task body, treat user direction as delegating route selection -- completing groundwork, selecting the recommended route, and unblocking downstream work -- and assign a decision to the user (`assignee: user`) only when the user explicitly reserved that choice prior to execution. Structure follow-up or review work as internal subtasks or as child tasks under a composite parent task, never as loose siblings.

## When to include

Any task where the problem space, method, architecture, or technology choice is uncertain and requires grounded investigation before specification or execution.

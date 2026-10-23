---
alias:
  - wf-research
description: Investigate problem space, prior art, codebase state, and architectural options with trade-offs before specification.
id: wf-research
tags:
  - wf-template
  - research
title: wf-research
type: template
---

## What this step does

Investigate the problem space, relevant codebase areas, dependencies, and external prior art before drafting a specification or making architectural commitments. Discovers constraints, evaluates viable alternatives, and grounds findings in primary evidence.

## Procedure

1. **Define research scope** -- frame primary research questions and unknowns.
2. **Investigate codebase and context** -- examine existing architecture, dependencies, data structures, and operational constraints.
3. **Survey external options** -- investigate established libraries, external APIs, protocols, or algorithmic precedents.
4. **Evaluate alternatives** -- compare candidate designs against trade-offs (complexity, performance, maintenance, coupling, migration cost).
5. **Document findings** -- cite primary evidence (`file:line`, command outputs, external references) and state the recommended architectural direction.

## Output contract

A grounded research artifact providing:

- Answers to primary research questions with pinpoint citations.
- Comparison matrix or breakdown of candidate approaches with pros/cons.
- Clear statement of constraints (e.g. backward compatibility, resource bounds).
- Recommended approach and its justification.

## When to include

Any task where the problem space, architectural pattern, or technology choice is uncertain and requires upfront investigation before specification or implementation.

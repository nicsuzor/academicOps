---
title: Goal Decomposition
type: template
category: gate
description: Expand an ambiguous or high-level objective into an abstract graph of sub-objectives, decision branches, and prerequisites. Select when planning complex work before implementation. Not for writing code or dispatching workers (use `/aops:brief`).
tags: [planning, decomposition, graph, expansion, gate]
---

# Gate: Goal Decomposition

Decomposition pass to structure complex objectives into actionable, dependency-ordered work units.

## 1. Objective and Boundary Clarification

- State the core objective and non-negotiable boundaries for `<goal>`.
- Identify what is fixed versus what remains under genuine uncertainty.

## 2. Abstract Sub-Goal Graph Generation

- Expand the objective into discrete sub-goals.
- Establish dependency links (`depends_on`, `contributes_to`) between nodes.
- Name decision branches and alternative paths where trade-offs exist.

## 3. Gap and Prerequisite Inspection

- Check for unstated prerequisites, missing tooling, or unverified assumptions.
- Ensure research or investigation tasks precede dependent implementation tasks.

## 4. Sizing and Readiness Check

- Ensure each leaf node is sized to a single dispatchable unit (≲ 1 session).
- Verify the graph covers the full scope of the objective without premature micro-implementation detail.

## Exit Condition

Coherent, dependency-wired sub-goal graph ready for brief formulation.

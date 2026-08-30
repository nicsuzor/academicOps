---
id: investigation
type: template
kind: process
category: process
description: Hypothesis-probe-conclude cycle for debugging and exploratory work with an unknown cause
requires: []
pairs-with: [wf-verification]
conflicts: []
version: 1.0.0
permalink: workflows-process-investigation
status: retired
superseded_by: aops_f74b7e6c
tags: [retired]
---

> [!IMPORTANT]
> **RETIRED**: archived off as part of the v0.9 null workflow-template set reset ([[aops_f74b7e6c]]). Do not compose.

# Process: Investigation

Routed to directly for a bug whose cause is unknown, and composable into
decompose spikes and any other exploratory work.

## Pattern

1. **Hypothesis** — state what you believe to be true, in testable form.
2. **Probe** — design the cheapest test that could confirm or refute it.
3. **Execute** — run the probe, capture evidence.
4. **Conclude** — confirmed | refuted | needs more data.
5. **Document** — record the finding; where it is worth preserving beyond this
   task, invoke the `remember` skill.

## Key Principle

**Cheapest probe first.** Don't read the entire codebase to test one
hypothesis — find the minimal evidence that settles it.

| Hypothesis type             | Cheap probe                 |
| --------------------------- | --------------------------- |
| "X causes Y"                | Disable X, check if Y stops |
| "File F contains Z"         | Grep for Z in F             |
| "Function fails on input I" | Call the function with I    |
| "Regression since commit C" | Git bisect from C           |

## When to Skip

- Cause is already known — go straight to the fix.
- Following explicit user instructions — execute, don't investigate.

---
id: investigation
kind: process
category: fragment
description: Hypothesis-probe-conclude cycle for debugging and exploratory work with an unknown cause
requires: []
pairs-with: [memory-capture]
conflicts: []
version: 1.0.0
permalink: workflows-process-investigation
---

# Process fragment: Investigation

**Composable fragment.** Used by debugging, decompose spikes, and any
exploratory work where the cause isn't known yet.

## Pattern

1. **Hypothesis** — state what you believe to be true, in testable form.
2. **Probe** — design the cheapest test that could confirm or refute it.
3. **Execute** — run the probe, capture evidence.
4. **Conclude** — confirmed | refuted | needs more data.
5. **Document** — record the finding (compose [[memory-capture]] if it's worth
   preserving beyond this task).

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

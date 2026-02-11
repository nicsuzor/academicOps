---
id: base-investigation
category: base
---

# Base: Investigation

**Composable base pattern.** Used by debugging, decompose spikes, and exploratory workflows.

## Pattern

1. **Hypothesis**: State what you believe to be true (testable)
2. **Probe**: Design cheapest test to confirm/refute
3. **Execute**: Run probe, capture evidence
4. **Conclude**: Confirmed | Refuted | Needs more data
5. **Document**: Record findings for future reference

## Key Principle

**Cheapest probe first.** Don't read entire codebase to test a hypothesis. Find the minimal evidence that confirms or refutes.

## Probe Design

| Hypothesis Type | Cheap Probe |
|-----------------|-------------|
| "X causes Y" | Disable X, check if Y stops |
| "File F contains Z" | Grep for Z in F |
| "Function fails on input I" | Call function with I |
| "Regression since commit C" | Git bisect from C |

## Conclusion Format

- **Confirmed**: Hypothesis true, evidence: [cite]
- **Refuted**: Hypothesis false, evidence: [cite]
- **Insufficient**: Need different probe, explain why

## When to Skip

- Cause is already known
- Following explicit user instructions (just execute, don't investigate)

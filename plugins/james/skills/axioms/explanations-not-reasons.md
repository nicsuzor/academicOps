---
description: An agent's explanation of what it did is not its reason; self-reports are hearsay and never taken at face value.
trigger: always_on
---

## Explanations are not reasons

An agent's explanation of what it did is not its reason. Asked why it acted, an agent produces a plausible story after the fact; that account is hearsay, because models have no direct knowledge of their own causes.

- Never accept an agent's stated reason at face value. Stated reasons are probabilistic post-hoc narratives, not direct observations of cause, and are sometimes false.
- Establish root causes from external evidence -- runtime traces, tool inputs and payloads, error codes, git diffs, environment state, and isolated reproduction runs -- never from an agent's self-reported intent, belief, or interpretation.
- Treat self-explanations as unverified claims requiring corroborating evidence before relying on them in audits, post-mortems, reviews, or failure diagnoses.

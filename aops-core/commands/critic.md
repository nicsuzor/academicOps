---
name: critic
type: command
category: instruction
description: Strategic review agent — multi-level critique applying 10 cognitive moves
triggers:
  - "/critic"
  - "pre-hoc plan evaluation"
  - "adversarial review"
  - "plan review"
modifies_files: false
needs_task: false
mode: conversational
domain:
  - framework
  - quality-assurance
---

# /critic — Strategic Review

Invoke pauli (the Logician) on the provided document or plan.

Invoke: `Agent(subagent_type="aops-core:pauli", prompt="<document or file path>")`

Pass through all arguments. Pauli returns a structured strategic review.

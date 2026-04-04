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

Invoke the critic agent on the provided document or plan.

Invoke: `Agent(subagent_type="aops-core:critic", prompt="<document or file path>")`

Pass through all arguments. The critic agent applies the 10 cognitive moves and returns a structured strategic review.

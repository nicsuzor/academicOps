---
name: enforcer
type: command
category: instruction
description: Post-hoc axiom compliance check — detects violations, ultra vires actions, workflow discipline issues
triggers:
  - "/enforcer"
  - "axiom compliance"
  - "rules check"
  - "ultra vires"
  - "post-hoc review"
modifies_files: false
needs_task: false
mode: execution
domain:
  - framework
---

# /enforcer — Axiom Compliance Check

Invoke the rbg agent (The Judge) to check for axiom violations, scope explosion, premature termination, and plan-less execution.

Invoke: `Agent(subagent_type="aops-core:rbg", prompt="<session narrative or file path>")`

Pass through all arguments. RBG checks against the universal axioms and workflow discipline rules, returning OK, WARN, or BLOCK.

---
name: rbg-policy-context
title: RBG Policy Context Injection
category: template
description: |
  Full context injection when rbg gate blocks a tool call.
  Variables: {threshold}, {ops_since_open}, {temp_path} - ops_since_open/threshold
  kept parenthetically for audit/debug now that the primary framing matches
  rbg-countdown.md's down-to-zero direction (aops_47d0a754).
---

<academicOps rbg compliance check>
**ERROR:** Compliance check OVERDUE. You need to invoke the **rbg** agent before you can use tools.

**0 remaining — compliance check now required** (threshold {threshold} reached, {ops_since_open} ops since last check). Invoke the **rbg** agent with the file path argument:

- `Agent(subagent_type='aops-pkb:rbg', prompt='{temp_path}')`
  </academicOps rbg compliance check>

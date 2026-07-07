---
name: rbg-policy-context
title: RBG Policy Context Injection
category: template
description: |
  Full context injection when rbg gate blocks a tool call.
  Variables: {ops_since_open}, {temp_path}
---

<academicOps rbg compliance check>
**ERROR:** Compliance check OVERDUE. You need to invoke the **rbg** agent before you can use tools.

**Periodic compliance check required ({ops_since_open} ops since last check).** Invoke the **rbg** agent with the file path argument:

- `Agent(subagent_type='aops-pkb:rbg', model='sonnet', prompt='{temp_path}')`
  </academicOps rbg compliance check>

---
name: custodiet-policy-context
title: Custodiet Policy Context Injection
category: template
description: |
  Full context injection when custodiet gate blocks a tool call.
  Variables: {ops_since_open}, {temp_path}
---

**ERROR:** Compliance check OVERDUE. You need to invoke the **rbg** agent before you can use tools.

**Periodic compliance check required ({ops_since_open} ops since last check).** Invoke the **rbg** agent with the file path argument: `{temp_path}`

- Gemini: `aops_core_rbg(message='{temp_path}')`
- Claude: `Agent(subagent_type='aops-core:custodiet', prompt='{temp_path}')`

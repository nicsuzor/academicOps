---
name: custodiet-policy-context
title: Custodiet Policy Context Injection
category: template
description: |
  Full context injection when custodiet gate blocks a tool call.
  Variables: {ops_since_open}, {temp_path}
---

**ERROR:** Compliance check OVERDUE. You need to invoke the **custodiet** agent before you can use tools.

**Periodic compliance check required ({ops_since_open} ops since last check).** Invoke the **custodiet** agent with the file path argument: `{temp_path}`

- Gemini: `delegate_to_agent(name='custodiet', query='{temp_path}')`
- Claude: `Agent(subagent_type='custodiet', prompt='{temp_path}')`

---
name: enforcer-policy-context
title: Enforcer Policy Context Injection
category: template
description: |
  Full context injection when enforcer gate blocks a tool call.
  Variables: {ops_since_open}, {temp_path}
  WS7 item 4: carries the enforcer-channel sentinel so this is recognised as a
  first-party gate rather than a prompt injection (#1315).
---

<!-- aops:enforcer-channel -->

**ERROR:** Compliance check OVERDUE. You need to invoke the **enforcer** agent before you can use tools.

**Periodic compliance check required ({ops_since_open} ops since last check).** Invoke the **enforcer** agent with the file path argument: `{temp_path}`

- Gemini: `invoke_agent(agent_name='rbg', prompt='{temp_path}')`
- Claude: `Agent(subagent_type='aops-core:rbg', prompt='{temp_path}')`
- agy: `Agent(subagent_type='aops-core:rbg', prompt='{temp_path}')`

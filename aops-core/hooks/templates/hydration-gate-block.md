---
name: hydration-gate-block
title: Hydration Gate Block Message
category: template
description: |
  Message shown when hydration gate blocks a tool call.
  Instructs the agent to invoke the aops-core:prompt-hydrator agent or skill before proceeding.
---

**User prompt hydration required.** Invoke the **prompt-hydrator** agent with the file path argument: `{temp_path}`

Run the hydrator with this command:
- Gemini: `delegate_to_agent(name='aops-core:prompt-hydrator', query='{temp_path}')`
- Claude: `Task(subagent_type='aops-core:prompt-hydrator', prompt='{temp_path}')`

Pass the file path directly to the agent — it will read the file and perform the hydration.

ALL TOOLS ARE BLOCKED until you invoke the prompt-hydrator agent.

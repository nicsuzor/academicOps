---
name: hydration-gate-block
title: Hydration Gate Block Message
category: template
description: |
  Message shown when hydration gate blocks a tool call.
  Instructs the agent to invoke the aops-core:prompt-hydrator agent or skill before proceeding.
---

**User prompt hydration required. You were already told that prompt hydration is required.** Invoke the **prompt-hydrator** agent with the file path argument: `{temp_path}`

Run the hydrator with this command:
- Gemini: `delegate_to_agent(name='aops-core:prompt-hydrator', query='{temp_path}')`
- Claude: `Task(subagent_type='aops-core:prompt-hydrator', prompt='{temp_path}')`

Pass the file path directly to the agent — it will read the file and perform the hydration.

This is a technical requirement. Status: currently BLOCKED, but clearing this is quick and easy -- just execute the command!

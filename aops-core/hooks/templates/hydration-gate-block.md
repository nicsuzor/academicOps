---
name: hydration-gate-block
title: Hydration Gate Block Message
category: template
description: |
  Message shown when hydration gate blocks a tool call.
  Instructs the agent to invoke the aops-core:prompt-hydrator agent or skill before proceeding.
---

✕ HYDRATION REQUIRED: Tool call blocked.

To proceed with file-modifying tools, you must first invoke the **prompt-hydrator** agent with the file path argument: `{temp_path}`

- Gemini: `aops_core_prompt_hydrator(message='{temp_path}')`
- Claude: `Agent(subagent_type='aops-core:prompt-hydrator', prompt='{temp_path}')`

Only always-available tools are not blocked.

---
name: hydration-gate-block
title: Hydration Gate Block Message
category: template
description: |
  Message shown when hydration gate blocks a tool call.
  Instructs the agent to invoke the aops-core:hydrator skill before proceeding.
---

✕ HYDRATION REQUIRED: Tool call blocked.

To proceed with file-modifying tools, you must first invoke the **hydrator** skill:

- Gemini: `activate_skill(name='aops-core:hydrator')`
- Claude: `Skill(skill='aops-core:hydrator')`

Only always-available tools are not blocked.

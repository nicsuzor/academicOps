---
name: hydration-gate-warn
title: Hydration Gate Warn Message
category: template
description: |
  Warning message shown when hydration gate is in warn mode.
  Alerts agent that hydrator should be invoked, but allows proceeding.
---

⚠️ HYDRATION GATE (warn-only): Hydrator not invoked yet.

This session is in WARN mode for testing. In production, this would BLOCK all tools.

To proceed correctly, invoke the **prompt-hydrator** agent with the file path argument: `{temp_path}`

- Gemini: `delegate_to_agent(name='aops-core:prompt-hydrator', query='{temp_path}')`
- Claude: `Task(subagent_type='aops-core:prompt-hydrator', prompt='{temp_path}')`

Pass the file path directly to the agent — it will read the file and perform the hydration.

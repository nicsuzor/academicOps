---
name: hydration-gate-warn
title: Hydration Gate Advisory Message
category: template
description: |
  Advisory message shown when hydration gate is in warn mode.
  Alerts agent that hydrator should be invoked, but allows proceeding.
---

💧 Prompt not yet hydrated.

To ensure alignment with project workflows and axioms, it is recommended to invoke the **task-hydrator** agent with the file path argument: `{temp_path}`

- Gemini: `aops_core_task_hydrator(message='{temp_path}')`
- Claude: `Agent(subagent_type='aops-core:task-hydrator', prompt='{temp_path}')`

You may proceed if the task is trivial, but hydration is recommended for any file-modifying work.

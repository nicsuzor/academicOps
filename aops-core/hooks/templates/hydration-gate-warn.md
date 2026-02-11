---
name: hydration-gate-warn
title: Hydration Gate Advisory Message
category: template
description: |
  Advisory message shown when hydration gate is in warn mode.
  Alerts agent that hydrator should be invoked, but allows proceeding.
---

💧 Prompt not yet hydrated.

To ensure alignment with project workflows and axioms, it is recommended to invoke the **prompt-hydrator** agent with the file path argument: `{temp_path}`

- For Claude Code: `Task(subagent_type="aops-core:prompt-hydrator", prompt="Follow instructions in {temp_path}")`
- For Gemini CLI: `delegate_to_agent(name="prompt-hydrator", query="Follow instructions in {temp_path}")`

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

To proceed correctly, invoke the **aops-core:prompt-hydrator** agent or skill:

- For Claude Code: `Task(subagent_type="aops-core:prompt-hydrator", prompt="Transform user prompt using context in {temp_path}")`
- For Gemini CLI: `spawn_agent(agent_name="prompt-hydrator", user_prompt="Transform user prompt using context in {temp_path}")`

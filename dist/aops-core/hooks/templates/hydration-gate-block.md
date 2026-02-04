---
name: hydration-gate-block
title: Hydration Gate Block Message
category: template
description: |
  Message shown when hydration gate blocks a tool call.
  Instructs the agent to invoke the aops-core:prompt-hydrator agent or skill before proceeding.
---

⛔ **MANDATORY**: HYDRATION GATE

You must invoke the **aops-core:prompt-hydrator** agent or skill FIRST to load context.

**Instruction**:
1. Run the exact command for your client:
   - For Claude Code: `Task(subagent_type="aops-core:prompt-hydrator", prompt="Analyze context in {temp_path}")`
   - For Gemini CLI: `activate_skill(name="prompt-hydrator", prompt="Analyze context in {temp_path}")`
2. **IMMEDIATELY** after it returns, continue with the plan it provides. Do not stop.

The `prompt-hydrator` locates required context and applies crucial defined procedures that you must follow in order to answer the user's request.

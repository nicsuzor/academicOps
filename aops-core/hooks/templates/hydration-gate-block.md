---
name: hydration-gate-block
title: Hydration Gate Block Message
category: template
description: |
  Message shown when hydration gate blocks a tool call.
  Instructs the agent to invoke the prompt-hydrator skill before proceeding.
---

⛔ **MANDATORY**: HYDRATION GATE

You must invoke the **prompt-hydrator** skill FIRST to load context.

**Instruction**:
1. Run `activate_skill` (e.g. prompt-hydrator) to load context.
2. **IMMEDIATELY** after it returns, continue with the plan it provides. Do not stop.

The `prompt-hydrator` locates required context and applies crucial defined procedures that you must follow in order to answer the user's request.

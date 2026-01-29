---
name: hydration-gate-block
title: Hydration Gate Block Message
category: template
description: |
  Message shown when hydration gate blocks a tool call.
  Instructs the agent to invoke the prompt-hydrator skill before proceeding.
---

⛔ **MANDATORY**: HYDRATION GATE: Invoke the prompt-hydrator skill FIRST.

**Override**: If hydrator fails, user can prefix next prompt with `.` to bypass, or use `/` for slash commands.

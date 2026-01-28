---
name: hydration-gate-block
title: Hydration Gate Block Message
category: template
description: |
  Message shown when hydration gate blocks a tool call.
  Instructs the agent to invoke the prompt-hydrator skill before proceeding.
---

⛔ HYDRATION GATE: Invoke prompt-hydrator before proceeding.

**MANDATORY**: Invoke the prompt-hydrator skill FIRST:

```
Invoke the **prompt-hydrator** skill:

"Read {temp_path} and provide workflow guidance."
```

The hydrator provides workflow guidance, context, and guardrails. Follow its output before continuing.

**Override**: If hydrator fails, user can prefix next prompt with `.` to bypass, or use `/` for slash commands.

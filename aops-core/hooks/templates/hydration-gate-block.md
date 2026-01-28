---
name: hydration-gate-block
title: Hydration Gate Block Message
category: template
description: |
  Message shown when hydration gate blocks a tool call.
  Instructs the agent to invoke the prompt-hydrator subagent before proceeding.
---

⛔ HYDRATION GATE: Invoke prompt-hydrator before proceeding.

**MANDATORY**: Spawn the hydrator subagent FIRST:

```
Delegate to **prompt-hydrator**:

"Read {temp_path} and provide workflow guidance."
```

The hydrator provides workflow guidance, context, and guardrails. Follow its output before continuing.

**Override**: If hydrator fails, user can prefix next prompt with `.` to bypass, or use `/` for slash commands.

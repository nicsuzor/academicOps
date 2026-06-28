---
name: qa-policy-context
title: QA Policy Context Injection
category: template
description: |
  Full context injection when QA gate blocks exit.
  Variables: {temp_path}
---

<academicOps QA gate reminder>
🧪 **Verify before you stop.** Invoke the `verify` skill (or marsha subagent) against the requirements at `{temp_path}`, act on what it finds, but keep marsha's raw output out of the chat. Then close with your own user-facing summary.
</academicOps QA gate reminder>

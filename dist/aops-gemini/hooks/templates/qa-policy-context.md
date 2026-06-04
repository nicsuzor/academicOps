---
name: qa-policy-context
title: QA Policy Context Injection
category: template
description: |
  Full context injection when QA gate blocks exit.
  Variables: {temp_path}
---

🧪 **Verify before you stop.** Run `/verify` (marsha) against the requirements at `{temp_path}`, act on what it finds, but keep marsha's raw output out of the chat. Then close with your own user-facing summary.

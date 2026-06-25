---
name: ida-askuserquestion-reminder
title: Ida — Capability Verification Reminder (AskUserQuestion)
category: template
description: |
  Injected into agent context at PreToolUse AskUserQuestion. Nudges the agent
  to verify any capability or infrastructure claim before surfacing a
  human-in-the-loop blocker to the user.
---

<academicOps Ida hook — capability check>
Before you ask the user a question:

- Is there a clear best answer? It's your responsibility to make the decision, we can revert later if needed.
- Can you find out yourself? Don't waste the user's time.
- Are you just confirming? Don't ask permission to do your job.
  </academicOps Ida hook — capability check>

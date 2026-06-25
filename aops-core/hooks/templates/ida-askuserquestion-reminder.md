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
You are about to ask the user a question. If this question asserts or implies a capability limit ("only you can run X", "I can't do X", "needs authentication", "X isn't available"), STOP and verify it live first:

- Is the binary on PATH? `command -v <tool>`
- What version is actually installed? `<tool> --version` (do NOT trust a version anchored in a prose note — notes go stale)
- Is there a valid credential? Check the token path + mtime (a recent mtime means active, refreshed use)
- Does the tool degrade gracefully (skip-if-unavailable) rather than hard-require auth?

Host capability truth is SSoT note `kb-337e2cf5`. A one-time token refresh is NOT a standing human-driver requirement. The interactive-OAuth limit applies only to credential-less polecat containers, NOT the authenticated host.
</academicOps Ida hook — capability check>

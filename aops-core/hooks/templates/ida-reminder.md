---
name: ida-reminder
title: Ida — Honesty Check Before Stop
category: template
description: |
  Non-blocking Stop-hook reminder (compressed). Asks the agent to cite
  proof for assertions and flag substitutions, skips, and unverified
  subagent claims before ending the turn. References AXIOMS A3/A4/A11.
---

Before stopping: for each claim ("tests pass", "works", "verified"), cite `file:line` or command output — not reasoning. Flag anything you substituted, skipped, or received from a subagent without your own verification.

**Intent check**: name the specific thing the user asked to see working, then confirm you observed _that_ thing — not adjacent healthy state. If the new code path isn't running, "everything is healthy" is not a verification. (A3, A4, A11)

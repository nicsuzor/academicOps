---
name: ida-reminder
title: Ida — Honesty Check Before Stop
category: template
description: |
  Non-blocking Stop-hook reminder (compressed). Asks the agent to cite
  proof for assertions and flag substitutions, skips, and unverified
  subagent claims before ending the turn.
---

Watch out, you aren't finished until you:

- Provide evidence and an indicator of your level of certainty for EACH of your major claims
- Give a most-plausible next-best hypothesis for each causal claim you have made
- Flag anything you substituted, skipped, or received from a subagent without your own verification.
- Restate each specific thing the user asked for:
  1. Provide a reference to the artifact that can be used to corroborate your response
  2. Explain ANY deviation or limitation where you were not able to fulfil the entire request.

**Relay hygiene** (if surfacing subagent output or asking user):
- **Filter**: Strip what the user already knows. Don't blindly forward subagent "for your eye" labels.
- **Decode**: Resolve opaque references (`task-...`, timestamps) via PKB, or omit them.
- **Synthesize**: Present *your* position, not just a relay of subagent prose.

**Pre-emit classification** (for questions):
- **DECIDE**: Answerable now via PKB/files. Resolve before emitting.
- **DEFER**: Waiting on evidence. State the block; don't ask.
- **SURFACE**: Genuine binary choice outside your authority. Emit.
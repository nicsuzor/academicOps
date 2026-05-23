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
- If you're about to emit a relay, a menu, or a status callout instead of your own synthesised view, re-emit. (See [[../../agents/junior]] § Coordinator mode.)

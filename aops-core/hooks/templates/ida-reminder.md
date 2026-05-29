---
name: ida-reminder
title: Ida — Honesty Check Before Stop
category: template
description: |
  Non-blocking Stop-hook reminder (compressed). Asks the agent to cite
  proof for assertions and flag substitutions, skips, and unverified
  subagent claims before ending the turn — as an observed-vs-asserted
  verification manifest.
---

Watch out, you aren't finished until you:

- Provide evidence and an indicator of your level of certainty for EACH of your major claims
- Give a most-plausible next-best hypothesis for each causal claim you have made
- Flag anything you substituted, skipped, or received from a subagent without your own verification.
- For any load-bearing quantitative or structural claim (test/file counts, "all green", "N migrated"), tag it OBSERVED — with the `cmd` you ran this session and the output line that supports it — or ASSERTED — derived/recalled, not freshly observed. This is your **verification manifest** (see [[../../skills/aops/references/authoring-discipline#5-worker-completion-summaries-carry-a-verification-manifest-observed-vs-asserted]]). Re-derive your own ASSERTED claims before you rely on them; if you are relaying a subagent's or worker's summary, re-derive _their_ ASSERTED claims first and spot-check the OBSERVED ones against the cited output rather than re-running everything.
- Restate each specific thing the user asked for:
  1. Provide a reference to the artifact that can be used to corroborate your response
  2. Explain ANY deviation or limitation where you were not able to fulfil the entire request.
- If you're about to emit a relay, a menu, or a status callout instead of your own synthesised view, re-emit. (See [[../../agents/junior]] § Coordinator mode.)

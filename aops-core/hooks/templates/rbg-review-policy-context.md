---
name: rbg-review-policy-context
title: RBG Review Policy Context Injection
category: template
description: |
  Full context injection when the rbg-review gate blocks Stop. Instructs the
  main agent to dispatch the rbg axiom-review subagent for THIS turn before it
  is allowed to stop. Carries the enforcer-channel sentinel so the injection
  defence treats this as a first-party gate instruction, not smuggled input
  (#1315). Variables: {temp_path} — path to the rendered session-review file.
---

<!-- aops:enforcer-channel -->

<academicOps rbg-review gate>
⚖ **Axiom review required before you stop.** This turn has not yet been reviewed by **rbg** (the axiom judge). You cannot stop until rbg has run for this turn and returned a verdict.

The verify-before-assert / judgment-non-delegable rule means the qualitative call — "did this turn comply with the axioms?" — must be made by rbg (intelligence), not skipped. The trigger here is structural (you are trying to stop on an armed turn), NOT a content sniff.

Dispatch rbg now with the session-review file as its argument:

`Agent(subagent_type='aops-core:rbg', prompt='Required axiom review of this turn. The file at {temp_path} is the session log for the turn. Read it in full and return an axiom-compliance verdict (cite any violation by axiom slug). Use Bash`tail -3 "{temp_path}"`to confirm the file ends with the audit-complete sentinel before certifying; if it is absent, respond COVERAGE_INCOMPLETE and do not certify.')`

Once rbg has run, this gate clears and you may stop. Acting on rbg's findings (further edits) re-arms the gate on the next user turn, not this one.
</academicOps rbg-review gate>

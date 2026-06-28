---
name: rbg-review-policy-context
title: RBG Review Policy Context Injection
category: template
description: |
  Full context injection when the rbg-review gate blocks Stop. Instructs the
  main agent to dispatch the rbg axiom-review subagent for the SESSION before a
  task-bound (polecat/crew) session is allowed to exit.
  Variables: {temp_path} — path to the rendered session-review file.
---

<academicOps rbg-review gate>
⚖ **Final axiom audit required before this task-bound session exits.** This session has not yet been audited by **rbg** (the axiom judge). This is the end-of-session backstop for autonomous/task-bound (polecat/crew) work — the in-session enforcer cadence already ran; this is the final check. You cannot stop until rbg has run and returned a verdict.

The verify-before-assert / judgment-non-delegable rule means the qualitative call — "did this session comply with the axioms?" — must be made by rbg (intelligence), not skipped. The trigger here is structural (a task-bound session is trying to exit on an armed gate), NOT a content sniff.

Dispatch rbg now with the session-review file as its argument:

`Agent(subagent_type='aops-core:rbg', prompt='Required final axiom audit of this session. The file at {temp_path} is the session log. Read it in full and return an axiom-compliance verdict (cite any violation by axiom slug). Use Bash`tail -3 "{temp_path}"`to confirm the file ends with the audit-complete sentinel before certifying; if it is absent, respond COVERAGE_INCOMPLETE and do not certify.')`

Once rbg has run, this gate clears and you may exit. Acting on rbg's findings (further edits) does NOT re-arm the gate this turn — the rbg discharge is loop-safe.
</academicOps rbg-review gate>

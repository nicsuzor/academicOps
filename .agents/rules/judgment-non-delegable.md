---
trigger: always_on
description: Judgment Is Non-Delegable
---

## Judgment Is Non-Delegable {#judgment-non-delegable}

You may delegate the WORK freely; you may never hand the RESPONSIBILITY to make a qualitative or comprehension-grade call to a mechanical, deterministic rig. Delegating that assessment to another _judging agent_ is fine and encouraged; delegating it to a mechanism is the violation. This axiom deliberately overlaps `exercise-authority` Edge 3 to guarantee coverage of two distinct senses.

- **Read, don't grep.** Substituting keyword, regex, substring, or fuzzy-match against text for a comprehension or semantic call is a violation; legacy-NLP heuristics are forbidden as a stand-in for understanding — we have smart models, use them.
- **Delegate the WORK, never the RESPONSIBILITY to qualitatively assess.** Hand the assessment to another _judging agent_ — never to a mechanical rig that matches. You cannot mechanise a judgment you never exercised: do the qualitative fitness-for-purpose review ("does this serve the person it was made for?") on real output yourself first; metrics are signals that trigger that review, never verdicts.
- **Channel architecture.** Passing a STRUCTURED signal through an UNSTRUCTURED channel and re-parsing it on the far side is a violation regardless of whether today's parse is accurate or deterministic — the channel architecture is wrong, not merely fragile. If the consumer reads the payload as natural language, own it as prose (one body field, no discriminator the consumer does not actually branch on); if it is structured, give it fields a consumer genuinely parses.

_Carve-out:_ deterministic work — counting, aggregation, syntactic validation — stays in code; that is not a judgment call and is not what this forbids.

- _E.g._ a check that asserts specific prose tokens appear in an agent's instructions, making the wording immutable at the token level and the test the de-facto spec, substitutes a mechanism for the judgment "does this instruction still do its job?"

_Review: [[AXIOMS-REVIEW#judgment-non-delegable]]._

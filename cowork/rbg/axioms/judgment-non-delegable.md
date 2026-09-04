---
description: Delegate work freely; never hand a qualitative judgment to a mechanical rig.
trigger: off
---

## Judgment Is Non-Delegable

Delegate the work freely. Never hand the responsibility for a qualitative or comprehension-grade call to a deterministic mechanism. Handing it to another judging agent is correct and encouraged; handing it to a rig is the violation.

- **Read, don't grep.** Keyword, regex, substring, or fuzzy matching against text is not a substitute for comprehension. We have smart models; use them.
- **Where a workflow, skill, hook, or check needs judgment, invoke an agent.** Deterministic code is the default only where the right answer is provably identical every time. The standing failure mode is under-invoking agents and paying forever in script maintenance and false negatives.
- **You cannot mechanise a judgment you never exercised.** Do the fitness-for-purpose review — "does this serve the person it was made for?" — on real output yourself before designing automation for it. Metrics trigger that review; they never replace its verdict.
- **Channel architecture.** Passing a structured signal through an unstructured channel and re-parsing it downstream is wrong even when today's parse succeeds. If the consumer reads the payload as prose, own it as prose; if it is structured, give it fields a consumer actually branches on.

Counting, aggregation, and syntactic validation stay in code. That is not judgment and is not what this forbids.

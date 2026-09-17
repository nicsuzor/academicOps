---
name: premise-check
description: Evaluate the logical integrity of reports and record a reasoned verdict. Mandatory before a claim reaches Nic.
---

# Premise Check

Audit reports before adopting or relaying their claims. Do not accept assertions at face value: evaluate the supporting evidence, verify logical consistency, and require independent sources of record.

This applies to your own claims as much as anyone else's. Intending to be careful is not an audit -- run the same six checks against what you are about to say.

## When

Run at intake, not only before reporting. Anything unevaluated that enters your context is a claim you will otherwise carry forward as fact:

- **Results returned by a subagent or `agy`.** Their conclusions are reported, not observed. Check what they actually ran before you adopt what they concluded.
- **Anything read from the graph** -- retrieved memories, notes, task records, and search results injected into your context. A stored claim is only as good as the evidence recorded with it, and it may have been true when written and false now.
- **Your own conclusions**, before they reach Nic.

Nothing propagates unevaluated. If a claim cannot pass, say so where you use it rather than passing it on unmarked.

## Audit Criteria

1. **Independent record**: confirm the subject's standing against an independent source of record cited by the reporter. Treat unverified claims as unresolved.
2. **Alternative explanations**: test whether the evidence also supports unstated alternative hypotheses.
3. **Sufficiency**: ensure sample size, coverage, and methodology warrant the conclusions drawn.
4. **Fact vs. inference**: distinguish directly observed facts from derived interpretations, and ensure stated confidence matches evidence strength.
5. **Generalisation**: check that findings do not extrapolate beyond the cases actually tested.
6. **Unstated premises**: identify the underlying assumptions and verify they hold.

## Verdict Recording

Synthesise the evaluation into a single reasoned judgment naming any defects, and record it:

```bash
uv run python3 scripts/verdict.py --report <report_id> --verdict "<your reasoned verdict>"
```

Bounce reports lacking independent citations or adequate evidence back to their author. A failing report does not reach Nic hedged or caveated -- it does not reach him until it passes.

---
name: premise-check
description: Evaluate the logical integrity of incoming reports and record a reasoned verdict to satisfy mandatory audit gates.
---

# Premise Check

Audit incoming reports before adopting or relaying their claims. Do not accept assertions at face value: evaluate supporting evidence, verify logical consistency, and require independent sources of record.

## Audit Criteria

Evaluate reports against six diagnostic checks:

1. **Independent record**: Confirm the subject's standing against an independent source of record cited by the reporter. Treat unverified claims as unresolved.
2. **Alternative explanations**: Test whether evidence supports unstated alternative hypotheses.
3. **Sufficiency**: Ensure sample size, coverage, and methodology warrant the conclusions.
4. **Fact vs. inference**: Distinguish directly observed facts from derived interpretations; ensure stated confidence matches evidence strength.
5. **Generalisation**: Check that findings do not extrapolate beyond tested cases.
6. **Unstated premises**: Identify underlying assumptions and verify their validity.

## Verdict Recording

Synthesize your evaluation into a single reasoned judgment naming any defects. Record it using the script:

```bash
uv run python3 scripts/verdict.py --report <report_id> --verdict "<your reasoned verdict>"
```

Bounce reports lacking independent citations or adequate evidence back to the author.

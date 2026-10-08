---
name: premise-check
description: Judge a report's logic against the original ask and record a PASS, REVISE or FAIL verdict with its reason. Use when a peer or worker report arrives, and before any claim goes up the chain. Not a fact check, and not a review that adds requirements.
---

# Premise Check

Check the form of a report, not its facts. Form done properly is the quality of the logic, measured against the original ask:

1. **Can the evidence support the claims?** Each load-bearing claim names checkable evidence (a PR, commit, node id, `file:line`, a quoted output) that, if it is what the report says, would show the claim. The reporter's statement of what it did is evidence of the work; a pointer is evidence of where it was saved.
2. **Do the claims lead to the conclusion?** The steps are valid: no unstated premise, no inference passed off as observation, no conclusion wider than the evidence.
3. **Does the conclusion fully answer the original ask?** Every part of the ask is addressed, in the ask's own terms.

Do not open sources, re-run work or authenticate a reporter's records to confirm the facts. Do not add requirements, gates or standards the original ask did not set: quality assurance and process are set by the workflow, not by this check. Match rigour to the output's purpose.

## When

- A peer or worker report arrives. The user's own messages are asks, not reports.
- Before you pass any claim up the chain, including your own.

## Verdict

| Token  | Meaning                                                                        |
| ------ | ------------------------------------------------------------------------------ |
| PASS   | All three hold.                                                                |
| REVISE | The logic holds in part; name what is missing or does not follow.              |
| FAIL   | The report does not answer the ask, or its conclusion does not follow from it. |

Record it, with the reason in free text:

```bash
uv run python3 scripts/verdict.py --report <report_id> --verdict PASS --reason "<why>"
```

When the reason is long or quotes commands, write it to a file and pass `--reason-file <path>` (or `--reason-file -` to read stdin), so free text stays off the command line.

A REVISE or FAIL goes back to its author. It does not reach the user hedged; it reaches them only once it passes.

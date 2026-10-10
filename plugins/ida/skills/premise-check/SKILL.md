---
name: premise-check
description: Judge a report or relayed direction's logic against the original ask and record a PASS, REVISE or FAIL verdict with its reason. Use when a peer report or relayed direction arrives, and before any claim goes up the chain. Not a fact check, and not a review that adds requirements.
---

# Premise Check

Check the form of a report or relayed direction, not its facts. Form done properly is the quality of the logic, measured against the original ask:

### Reports

1. **Can the evidence support the claims?** Each load-bearing claim names checkable evidence (a PR, commit, node id, `file:line`, a quoted output) that, if it is what the report says, would show the claim. The reporter's statement of what it did is evidence of the work; a pointer is evidence of where it was saved.
2. **Do the claims lead to the conclusion?** The steps are valid: no unstated premise, no inference passed off as observation, no conclusion wider than the evidence.
3. **Does the conclusion fully answer the original ask?** Every part of the ask is addressed, in the ask's own terms.

### Relayed Directions

When receiving an instruction or direction relayed from the user (carrying a citation pointing to the authorizing ask):

1. **Can the direction be logically derived from the cited original ask?** Check that the cited ask authorizes the direction.
2. **Does the direction add unsupported detail?** If the direction adds scope, constraints, or methods the cited ask does not support, flag the unsupported part.

Do not open sources, re-run work or authenticate a reporter's records to confirm the facts. Do not add requirements, gates or standards the original ask did not set: quality assurance and process are set by the workflow, not by this check. Match rigour to the output's purpose.

## When

- A peer or worker report arrives. The user's own messages are asks, not reports.
- An instruction or direction relayed from the user arrives.
- Before you pass any claim up the chain, including your own.

## Verdict

| Token  | Meaning                                                                                                                                               |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| PASS   | All criteria hold: the report's logic holds, or the relayed direction is logically derivable from the cited ask.                                      |
| REVISE | The logic holds in part, or the relayed direction adds detail the cited ask does not support; name what is missing, unsupported, or does not follow.  |
| FAIL   | The report does not answer the ask, its conclusion does not follow, or the relayed direction cannot be derived from the cited ask or lacks authority. |

## Proportionality

Before a REVISE or FAIL sends a report back, weigh the gap against the ask:

- An invalid claim is incidental when the assessment going up the chain does not rest on it and no durable record needs correcting because of it. Note it in the reason; do not send the report back for it.
- A load-bearing gap that the ask's importance does not justify verifying passes with the limitation stated. Record PASS, state the limitation in the reason, and carry it with the claim up the chain: the conclusion, narrowed by that limitation, still answers the ask.

## Gate and Verdict Recording

An incoming peer or worker report (via `<cross-session-message>`, `<teammate-message>`, or `<task-notification>`), or a subagent dispatch, arms the premise-check gate with that specific message or claim. The gate blocks all subagent dispatches, messages, and stop until a verdict is recorded.

Record the verdict using the exact runnable call given in the hook's prompt note or block message:

```bash
python3 <path/to/verdict.py> --report <report_id> --verdict PASS --reason "<why>"
```

From this repository's root, the path is `plugins/ida/skills/premise-check/scripts/verdict.py`. From the skill directory, use `scripts/verdict.py`. If `$AOPS_SESSION_ID` is unset, pass `--session <session_id>`.

When the reason is long or quotes commands, write it to a file and pass `--reason-file <path>` (or `--reason-file -` to read stdin), so free text stays off the command line.

A REVISE or FAIL goes back to its author. It does not reach the user hedged; it reaches them only once it passes.

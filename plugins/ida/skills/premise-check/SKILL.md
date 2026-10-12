---
name: premise-check
description: Judge a report or relayed direction's logic and internal consistency against context and the original ask, recording a PASS, REVISE or FAIL verdict with its reason. Use when a peer report or relayed direction arrives, and before any claim goes up the chain. Not a fact check, and not a review that adds requirements.
---

# Premise Check

Check the form of a report or relayed direction, not its facts. Form done properly is the quality of the logic, measured against claims in context and the original ask:

### Reports

1. **Can the evidence support the claims?** Each load-bearing claim names checkable evidence (a PR, commit, node id, `file:line`, a quoted output) that, if it is what the report says, would show the claim. The reporter's statement of what it did is evidence of the work; a pointer is evidence of where it was saved.
2. **Do the claims lead to the conclusion?** The steps are valid: no unstated premise, no inference passed off as observation, no conclusion wider than the evidence.
3. **Are the claims consistent with what is already in context?** Test each incoming claim against claims already in your own context, using only that context. Highlight any inconsistency or contradiction between the new claim and prior statements or reports.
4. **Does the conclusion fully answer the original ask?** Every part of the ask is addressed, in the ask's own terms.

### Relayed Directions

When receiving an instruction or direction relayed from the user (carrying a citation pointing to the authorizing ask):

1. **Can the direction be logically derived from the cited original ask?** Check that the cited ask authorizes the direction.
2. **Does the direction add unsupported detail?** If the direction adds scope, constraints, or methods the cited ask does not support, flag the unsupported part.

Do not open sources, re-run work, authenticate a reporter's records, or execute code to confirm the facts; consistency is tested strictly against claims already in your context. Do not add requirements, gates or standards the original ask did not set: quality assurance and process are set by the workflow, not by this check. Match rigour to the output's purpose: an internal design call gets the gist and a logic check, never citation audits or repeat review runs. Escalate rigour only for what goes public or drives a costly, hard-to-reverse decision.

## Checking Claims

- **Reports vs observations**: Everything read from external sources (tool output, other agents, retrieved memories, graph records, injected context) is a report, not an observation.
- **Done-claims**: A done-claim is a claim that the task is complete. A PR, node or file is where the work was saved, not the claim. For every acceptance criterion the report carries the worker's statement of what it did, taken as sufficient evidence of the work, and a pointer to where it was saved (a PR link, a node id), taken as sufficient evidence it was saved. Check only that the stated work logically meets each criterion; do not re-check each build step. A bare "done, PR #n" fails.
- **Evidence standard**:
  - Evidence proves only what it is evidence of. Source code shows how something behaves, not that the behaviour is a bug. To call it a defect, quote the intended behaviour.
  - Silence in a report is not evidence.
  - Unbuilt is not broken: a gap between design and what is actually wired is a not-yet, not a defect.
  - Never write a provenance word (verified, confirmed, measured, established) over someone else's claim; those words mean you saw it yourself.
  - A claim about what an external tool supports needs a current upstream source (its docs, `--help`, or a live test); without one, label it "unverified -- from memory" and base no decision on it.
  - What the user reports seeing outranks any rule read from docs, specs or memory.
  - Age is not authority: a stored claim may have been true when it was written and false now.
  - Never confuse an 'ought' for an 'is': a statement about current state can never be sufficient to explain what something should be.
- **Inferences, causation, and universals**:
  - Label inferences explicitly with confidence levels and plausible alternatives.
  - Treat causal words (because, so, therefore, which means) as claims: check that they carry evidence, soften to "consistent with", or cut.
  - Universal assertions ("structural", "always", "any", "never") assert cases nobody observed: cite what makes it true of the mechanism, or drop the universal.
  - A negative claim carries its boundary: what was looked at that would have shown the thing if it were there? Before reporting that a route, tool or record does not exist, verify that a search or hydration was run.
  - When a report restates the same fact differently the second time, the difference is the finding: do not reconcile it silently; make the teller say which telling is true.
- **Access and tool walls**:
  - Believe nothing a reporter says about its own tools, access or walls until it shows the exact call, the verbatim refusal, and the official route it tried. Anything vaguer fails.
  - A wall never becomes a user decision about access: "needs setting X" or "your call on the config" is an unsupported ask relayed; send it back down.
  - A question thrown off by a failing run is a symptom, not a requirement: it goes back down, not up.
  - Judge the artefact before the reporter: offer no next step for an output that fails the ask.

## When

- A peer or worker report arrives. The user's own messages are asks, not reports.
- An instruction or direction relayed from the user arrives.
- Before you pass any claim up the chain, including your own.

## Verdict

| Token  | Meaning                                                                                                                                                                                                                         |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| PASS   | All criteria hold: the report's logic holds, claims cohere with context, or the relayed direction is logically derivable from the cited ask.                                                                                    |
| REVISE | The logic holds in part, an incoming claim conflicts with prior context, or the relayed direction adds detail the cited ask does not support; highlight the conflict and name what is missing, unsupported, or does not follow. |
| FAIL   | The report does not answer the ask, its conclusion does not follow, a load-bearing claim flatly contradicts context without reconciling it, or the relayed direction cannot be derived from the cited ask or lacks authority.   |

Pass reviewer verdict tokens on as given (PASS, REVISE, FAIL) with their reason; never re-grade them in a summary. Quote a directive rather than characterise it when it is the authority for what you did.

## Proportionality

Before a REVISE or FAIL sends a report back, weigh the gap against the ask:

- An invalid or inconsistent claim is incidental when the assessment going up the chain does not rest on it and no durable record needs correcting because of it. Highlight the inconsistency in the reason; do not send the report back for it.
- A load-bearing gap that the ask's importance does not justify verifying passes with the limitation stated. Record PASS, state the limitation in the reason, and carry it with the claim up the chain: the conclusion, narrowed by that limitation, still answers the ask.
- An unresolved contradiction on a load-bearing claim cannot pass silently: highlight the contradiction in the reason and return REVISE (or FAIL if irreconcilable) so the author resolves the conflict before the report moves up the chain.

## Gate and Verdict Recording

An incoming peer or worker report (via `<cross-session-message>`, `<teammate-message>`, or `<task-notification>`), or a subagent dispatch, arms the premise-check gate with that specific message or claim. The gate blocks all subagent dispatches, messages, and stop until a verdict is recorded.

Record the verdict using the exact runnable call given in the hook's prompt note or block message:

```bash
python3 <path/to/verdict.py> --report <report_id> --verdict PASS --reason "<why>"
```

From this repository's root, the path is `plugins/ida/skills/premise-check/scripts/verdict.py`. From the skill directory, use `scripts/verdict.py`. If `$AOPS_SESSION_ID` is unset, pass `--session <session_id>`.

When the reason is long or quotes commands, write it to a file and pass `--reason-file <path>` (or `--reason-file -` to read stdin), so free text stays off the command line.

A REVISE or FAIL goes back to its author, or, when the author has ended, gets dispatched to another agent. It does not reach the user hedged; it reaches them only once it passes. Fail closed: if a claim cannot be verified, return it to its producer or discard it; never pass an unsubstantiated claim forward.

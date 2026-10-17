---
name: premise-check
description: Write or check the argument at the end of an evidence-backed report -- standard-form premises with their basis in words, warrants with their defeaters, the asker's questions answered by id -- and record the checker's verdict with its seven-line reason. Use when handing back a report, receiving one from a subagent, worker or peer, or relaying a checked claim upward. Not a fact check or requirement review, and not for extracting the argument of a text (use argument-extraction).
---

# Premise Check

A report that rests on evidence ends in an argument whose final conclusion answers the asker's questions. The writer lays it out so each step can be judged from the report alone; the checker judges every step and records why.

**Standing rule: a format breach is waivable; an untested inference never passes.**

## Writing the argument

End the report with one `argument` block in the form in [`references/report-form.md`](references/report-form.md).

1. **The ask at the top**, in the asker's own words, one question per `Asked` line, each with an immutable id: `tg-<message id>`, or `<task id>/AC<n>`. Copy the ask you were given; never restate it as your own title.
2. **Numbered premises**, each ending with its basis in words: _rule_ · _I read it_ · _I did it_ · _attempted, failed_ · _worker reported, verdict …_ · _worker reported, unchecked_ · _assumed, not checked here_. A premise about outside state quotes the value that decides it (`state: MERGED`, `0 hits`).
3. **Pointers as lettered endnotes** -- paths, lines, span ids, task ids, PRs. Never inline.
4. **The inference line** states the warrant as a rule that could be false on its own, then `Unless:` naming what would defeat the step and whether it is ruled out by a numbered line, not ruled out, or not tried.
5. **Write in what is missing** as a numbered line marked _assumed, not checked here_, and put the qualifier it buys in the conclusion ("so, most likely, …").
6. **Chain** each conclusion into the next step as a numbered line. Join independent findings only through an explicit "and both" step.
7. **Answer the asks by id** on the `Answers` line. An ask with no answer says so.
8. **Relay upward** only sentences that name the line they restate. A sentence with no line does not go.
9. **No premise count.** Every premise on an inference line is a condition of its rule. Avoid laundry lists: a long run of premises under one rule usually hides several steps, and splitting them makes each rule checkable.
10. **Keep machine vocabulary out of the lines.** Basis terms and Argdown attributes belong to tools; the reader sees words.

Match the conclusion to what the premises can carry: a ranking needs a comparison over the alternatives; a negative or "cannot" needs a failed attempt with its error, or a search with its query, scope and count; a causal or universal claim needs a mechanism or narrows; "should" needs a stated warrant.

Self-check before sending, as the checker will.

## Checking a received report

Take observed premises with a pointer as given: never open a pointer or redo the work. Everything else -- warrants, steps, scope, the fit between rule and case -- you judge. When a ruling turns on a fact the report lacks, send it back naming the missing premise.

Run four tests on every inference line:

| Test           | Passes when                                                                                             | Failure looks like                                                                                                  |
| -------------- | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| **Valid**      | The premises meet every condition of the warrant, and the conclusion is no wider than they are.         | A condition no line supplies; a defeater "not tried" that would change the next action; scope drift.                |
| **Supported**  | Each premise's basis can bear the step's stakes. A conclusion is only as strong as its weakest premise. | A _worker reported, unchecked_ or _assumed_ premise carrying a high-stakes step; "PASS" claimed with no verdict id. |
| **Answered**   | The final conclusion answers each ask id, or says it has no answer.                                     | The conclusion answers a narrower or different question than the `Asked` lines.                                     |
| **Sufficient** | Materiality, sufficiency and necessity settle each step (below).                                        | A complex, unbacked warrant on a high-stakes step accepted without one level of decomposition.                      |

Proportionality, in order:

1. **Materiality** -- examine a step only if changing its conclusion would change what the reader does next.
2. **Sufficiency** -- accept a warrant as stated when it is obvious, backed by a cited rule or verdict, or carries a claim cheap to reverse. Send back for one level of decomposition only when it is complex, unbacked and high-stakes. `worker reported` premises get the same test: a report carries a verdict id or is weighed as unchecked.
3. **Necessity** -- reject only when the objection would change this conclusion; phrasing or a preferred route is not a rejection.

A format breach that leaves the step judgeable is waived and listed; one that hides a step is a REVISE.

## Recording the verdict

- **PASS** -- every inference holds, every ask is answered or honestly unanswered, and the weakest basis can bear the stakes.
- **REVISE** -- name the line, the defect tag (`#missing`, `#scope-drift`, `#conflict`, `#unanswered`, `#undercut`) and what would fix it. Return it to the sender.
- **FAIL** -- the conclusion does not answer the ask.

Write the reason as the seven keyed lines in [`references/checker-reason.md`](references/checker-reason.md) -- Judged · Valid · Supported · Answered · Sufficient · Waived · Relay -- and record it:

```bash
uv run --project <plugin-dir> python3 <plugin-dir>/skills/premise-check/scripts/verdict.py --claim <claim_id> --verdict <PASS|REVISE|FAIL> --reason-file <path>
```

The recorder refuses a PASS whose reason misses a test line or an ask id, or contradicts the block. A harness notice or other message that makes no claim takes the one-line no-claim reason. For a handback read from a task record, the claim id is the task id; after recording, add `## Premise-Check Verdict` to the task with the verification id and verdict.

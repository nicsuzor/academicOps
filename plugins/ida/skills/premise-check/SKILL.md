---
name: premise-check
description: Write or check the argument at the end of an evidence-backed report -- standard-form premises with their basis in words, warrants with their defeaters, the asker's questions answered by id -- and record the checker's verdict with its seven-line reason. Use when handing back a report, receiving one from a subagent, worker or peer, or relaying a checked claim upward. Not a fact check or requirement review, and not for extracting the argument of a text (use argument-extraction).
---

# Premise Check

A report that rests on evidence ends in an argument whose final conclusion answers the asker's questions. The writer lays it out so each step can be judged from the report alone; the checker judges every step and records why.

**Standing rule: a format breach is waivable; an untested inference never passes.**

## Writing the Report Argument

End the report with one fenced `argdown` block formatted per `argdown-toulmin`.

````text
```argdown
===
asks:
  <ask_id>: <the asker's own words, one question>
answers:
  <ask_id>: <number of the line that answers it>
notes:
  a: <path:line, span id, task id, PR>
===

(1) <premise>. -- <basis phrase> ^a
(2) <premise quoting deciding value>. -- <basis phrase>
(3) <missing premise, written in>. -- assumed, not checked here
-- <warrant rule>. Unless: <defeater>; <ruled out by (n) | not ruled out | not tried>. --
(4) So, <qualifier bought by (3)>, <conclusion>.
```
````

Every peer message carries a fenced `argdown` block. A message making no claim (such as automated harness notices, /loop wakeups, or messages making no evidence-backed claims) carries the null form:

````text
```argdown
===
asks: none
===

[no claim]
```
````

The null form clears the premise-check gate with no agent action. When an expected block is absent, the gate does not open: PASS is refused, and the receiver must return it for revision (`REVISE` "no argument supplied").

### Basis Phrases (Closed Vocabulary)

Premise lines end with their basis in words, drawn strictly from this closed vocabulary:

| Phrase | Rank | Meaning |
| - | - | - |
| `I read it` | 3 | Primary record, diff, log, or code read directly |
| `I did it` | 3 | Runtime command executed, test run, or artifact generated directly |
| `attempted, failed` | 3 | Direct reproduction attempt failed with observed error |
| `rule` | 2 | Framework axiom, project rule, or governing specification |
| `worker reported, verdict` | 2 | Another agent's report backed by a recorded verification ID |
| `worker reported, unchecked` | 1 | Peer writing or PKB note without a recorded verdict |
| `assumed, not checked here` | 0 | Unchecked assumption; requires a qualifier in its conclusion |

### Rules for the Block

1. **The ask at the top**: Copy the asker's exact words under its immutable ID (`tg-<msg_id>`, `<task_id>/AC<n>`).
2. **Numbered premises**: Each line ends with `-- <basis phrase>`, with outside values quoted.
3. **Pointers as lettered endnotes**: Pointers live under `notes:` and are cited as `^a` on the line.
4. **The inference line**: Starts `--`, ends `--`, on one line: warrant rule, then `Unless: <defeater>; <status>`.
5. **Chain conclusions**: Each step begins `So` and chains into subsequent steps.
6. **Relay upward**: Relaying a report upward requires its premise-check verdict; name the line each relayed sentence restates. Read claims against their source of record before relaying.

## Checking a Received Report or Direction

### Directions

When an incoming direction arrives from another agent:

1. Verify that every instruction and requirement derives faithfully from `## Ask` (or active user directives).
2. Refuse (`REVISE`) unverified caller method or template prescriptions before logging deliverables. A caller may pass only `## Ask` (verbatim with ID), strategic fit/context, and the objective or skill invocation.
3. Once verified, log deliverables as a frozen `## Acceptance` checklist on a PKB task before work starts.

### Reports

Take observed premises with a pointer as given: never open a pointer or redo the work. A PKB node or peer writing ranks as `worker reported, unchecked`. Run four tests on every inference line:

| Test | Passes when | Failure looks like |
| - | - | - |
| **Valid** | Premises meet every condition of the warrant; conclusion is no wider than premises. | Missing condition; unruled defeater; scope drift. |
| **Supported** | Each premise's basis can bear the step's stakes. Weakest premise bounds conclusion. | `worker reported, unchecked` or `assumed` on high-stakes step. |
| **Answered** | Final conclusion answers what each ask ID needs in substance. | Narrower conclusion; relayer acceptance items substituted for ask needs. |
| **Sufficient** | Proportionality holds: materiality, sufficiency (obvious, authority-backed, low-stakes), and necessity. | Complex unbacked warrant on high-stakes step without decomposition. |

Proportionality: accept warrants as stated when obvious, authority-backed (limited to user words or governing spec), backed by a cited verdict, or cheap to reverse. Send back for decomposition only when complex, unbacked, and high-stakes.

## Recording the Verdict

- **PASS**: Every inference holds, every ask is answered, and the weakest basis bears the stakes.
- **REVISE**: Name the line, defect tag (`#missing`, `#scope-drift`, `#conflict`, `#unanswered`, `#undercut`), and remedy. Return to sender.
- **FAIL**: Conclusion does not answer the ask.

Write the reason as the seven keyed lines:

```text
Judged: <claim id>; asks <ask id>, <ask id>
Valid: (n) holds -- <rule and why it yields (n) here>
Supported: weakest <basis phrase> -- (<premise n>) <reason>
Answered: <ask id> ← (n)
Sufficient: (n) material; <obvious | authority-backed | low-stakes>; no objection
Waived: none | <format item> -- <justification>
Relay: "<sentence to relay>" ← (n) | none
```

Format items: `block`, `numbering`, `endnotes`, `basis wording`, `ask wording`, `layout`.

Record the verdict:

```bash
uv run --project <plugin-dir> python3 <plugin-dir>/skills/premise-check/scripts/verdict.py --claim <claim_id> --verdict <PASS|REVISE|FAIL> --reason-file <path>
```

The recorder refuses a PASS whose reason misses a test line or ask ID, contradicts the block, or fails machine checks (syntax error, orphan statement, misaimed undercut); on refusal, actionable errors are emitted to stderr while keeping the gate armed.

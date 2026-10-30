---
name: premise-check
description: Write or check the argument at the end of an evidence-backed report -- standard-form premises with their basis in words, warrants with their defeaters, the asker's questions answered by id -- and record the checker's verdict with its seven-line reason. Use when handing back a report, receiving one from a subagent, worker or peer, or relaying a checked claim upward. Not a fact check or requirement review, and not for extracting the argument of a text (use argument-extraction).
---

# Premise Check

A report that rests on evidence ends in an argument whose final conclusion answers the asker's questions. The writer lays it out so each step can be judged from the report alone; the checker judges every step and records why.

**Standing rule: a format breach on an argument with at least one inference line is waivable on PASS and rewritten by the receiver; 0 inference lines, substantive defects, or rule violations in delivered work require REVISE or FAIL and cannot pass or relay upward. Rule violations in deliverables are strictly non-waivable.**

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

Per [Human Readability First](../../../rbg/skills/axioms/human-readability-first.md), these basis phrases represent semantic categories rather than rigid mechanical formulas to be parsed by regex; evaluation of basis validity is performed by agentic comprehension. Premise lines end with their basis in words, drawn strictly from this closed vocabulary:

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
2. **Raw empirical observations**: Premises with an `observed` basis (`I did it`, `I read it`, rank = 3) state raw empirical observations quoting deciding values inline (`exit_code = 0`, `rank = 3`, `status: MERGED`). They never state evaluative or generalising conclusions restating an acceptance criterion (such as "AC1 is met" or "behavior is correct"). Evaluative and generalising conclusions must sit below an inference bar as claims derived from those observations.
3. **Numbered premises**: Each line ends with `-- <basis phrase>`, with outside values quoted.
4. **Pointers as lettered endnotes**: Pointers live under `notes:` and are cited as `^a` on the line.
5. **The inference line**: Starts `--`, ends `--`, on one line: warrant rule, then `Unless: <defeater>; <status>`.
6. **Chain conclusions**: Each step begins `So` and chains into subsequent steps.
7. **Relay upward**: Relaying a report upward requires its premise-check verdict; name the line each relayed sentence restates. Relay sentences only from checked argument lines without reading sources. Never relay an argument with 0 inference lines or substantive defects as fact. Disclosed rule violations in a received report must be propagated upward in the relay and never dropped across hops. Relay only premises and conclusions; a struck doubt or an untried defeater is never relayed as a risk.

## Checking a Received Report or Direction

### Directions

When an incoming direction arrives from another agent:

1. Verify that every instruction and requirement derives faithfully from `## Ask` (or active user directives).
2. Refuse (`REVISE`) unverified caller method or template prescriptions before logging deliverables. A caller may pass only `## Ask` (verbatim with ID), strategic fit/context, and the objective or skill invocation.
3. Once verified, log deliverables as a frozen `## Acceptance` checklist on a PKB task before work starts.

### Reports

Take observed premises with a pointer as given: never open a pointer or redo the work. A checker never reads a source to check someone's claim; it reads one only to settle a genuine conflict between two records. When a claim lacks evidence or rests on an unchecked basis, do not inspect the source: record REVISE or FAIL naming the defect. A doubt is a claim. A defeater, risk or "I haven't checked" the writer raises with no basis for thinking it true (`not tried`, with no reason given that the step would fail) is a speculation, not a defect in the argument: it neither undercuts the step nor becomes a finding. Strike it: judge Valid as if it were absent, relay nothing from it, and send nothing back for it. Where the work itself shows the answer on its first run, the doubt is never worth a probe, a trial run or a lookup; asked about it, answer that it had no basis. A PKB node or peer writing ranks as `worker reported, unchecked`.

In addition to the four inference tests, the checker examines the entire report (prose and argument) for rule compliance in the delivered work:

| Test | Passes when | Failure looks like |
| - | - | - |
| **Rule-Consistent** | The actions, omissions, and claims in the delivered work do not contradict standing axioms, project rules, or specifications. Disclosing an out-of-scope breach under Rule 4 is compliant escalation. | Report states or admits leaving a rule breach in place in its own deliverable, waives a rule without a higher rule or direct user directive, or describes an action forbidden by a standing rule. |

Run four tests on every inference line:

| Test | Passes when | Failure looks like |
| - | - | - |
| **Valid** | Premises meet every condition of the warrant; conclusion is no wider than premises; construct matches and sample is adequate. | Missing condition; unruled defeater that has a basis (a baseless one is struck, not ruled on); scope drift; construct mismatch (quantitative rank checks substituted for qualitative evaluation); sample inadequacy (unexplained n=1 or n=2 probes asserted as proof of representative classes). |
| **Supported** | Each premise's basis can bear the step's stakes. Weakest premise bounds conclusion. | `worker reported, unchecked` or `assumed` on high-stakes step. |
| **Answered** | Final conclusion answers what each ask ID needs in substance. | Narrower conclusion; relayer acceptance items substituted for ask needs. |
| **Sufficient** | Proportionality holds: materiality, sufficiency (obvious, authority-backed, low-stakes), and necessity. A task's primary ask or acceptance criterion is never low-stakes or obvious. | Complex unbacked warrant on high-stakes step without decomposition; treating a primary ask or acceptance criterion as low-stakes or obvious. |

Proportionality: accept warrants as stated when obvious, authority-backed (strictly limited to user words or governing spec), backed by a cited verdict, or cheap to reverse. A task's primary ask or acceptance criterion is never low-stakes or obvious. Send back for decomposition only when complex, unbacked, or high-stakes.

## Recording the Verdict

- **PASS**: Every inference holds, every ask is answered, the weakest basis bears the stakes, and at least one inference line is tested (>= 1). Format-only defects on a substantively sound argument with >= 1 inference line are waived under `Waived:` and rewritten into standard form by the receiver before relaying upward. Rule violations in deliverables can never be waived.
- **REVISE**: Name the line, defect tag (`#missing`, `#scope-drift`, `#conflict`, `#unanswered`, `#undercut`), and remedy. Mandatory for substantive defects, rule violations in delivered work (return with `#conflict`), or 0 inference lines (bare assertions); cannot be relayed upward as fact. Return to sender.
- **FAIL**: Conclusion does not answer the ask or contradicts evidence. Mandatory for substantive defects; cannot be relayed upward as fact.

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

For arguments with multiple inference lines, all yielded conclusions must be accounted for under `Valid:`--either via multiple `Valid:` lines, indented continuation lines, semicolon clauses (`(n) holds -- ...; (m) holds -- ...`), or grouped references (`(n), (m) holds -- ...` or `(n) and (m) hold -- ...`).

Format items: `block`, `numbering`, `endnotes`, `basis wording`, `ask wording`, `layout`.

Record the verdict:

```bash
uv run --project <plugin-dir> python <plugin-dir>/skills/premise-check/scripts/verdict.py --claim <claim_id> --verdict <PASS|REVISE|FAIL> --reason-file <path>
```

The recorder refuses a PASS whose reason misses a test line or ask ID, contradicts the block, or fails machine checks (syntax error, orphan statement, misaimed undercut); on refusal, actionable errors are emitted to stderr while keeping the gate armed.

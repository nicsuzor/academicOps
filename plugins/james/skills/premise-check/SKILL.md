---
name: premise-check
description: Write or verify evidence-backed reports in Chained Toulmin Argdown -- numbered premises with inline source attribution, single-line warrant inference bars with defeaters, ask-to-answer frontmatter mapping, and seven-line checker verdicts via verdict.py --judged-file. Use when handing back a report, receiving a report from a subagent or peer, or relaying checked claims upward. Exclude for pure direction validation without claims (verify Turn-1 inputs and return REVISE directly).
---

# Premise Check

A report resting on evidence ends in a parser-valid Chained Toulmin Argdown block whose conclusions answer the asker's questions from the report alone. The writer lays out every step; the receiver inspects the argument explicitly on receipt and records a verdict via `verdict.py --judged-file`.

**Standing rule: a format breach on an argument with at least one inference line is waivable on PASS and rewritten by the receiver; 0 inference lines, substantive defects, or rule violations in delivered work require REVISE or FAIL and cannot pass or relay upward. Rule violations in deliverables are strictly non-waivable. When the sender has exited, the reader rewrites the argument from recorded evidence for a `#format` defect; a `#missing` or `#scope-drift` verdict still routes to a new worker.**

## Writing the Report Argument

End every evidence-backed report or peer message with one fenced `argdown` block in Chained Toulmin Argdown form. Before writing or validating a full argument block, read [references/report-form.md](references/report-form.md) for the complete grammar, `{basis, pointer, source, reason}` metadata vocabulary, diagnostic tags, granularity levels, and parser compliance rules.

````text
```argdown
===
title: <title>
granularity:
  level: micro
  floor: "<one sentence naming what counts as a leaf>"
model:
  mode: strict
asks:
  <ask_id>: <the asker's own words, one question>
answers:
  <ask_id>: <integer line number, statement title, or none>
===

(1) [Label]: <observed ground quoting deciding value inline (path/to/file.py:42)>.
(2) <further ground or bound (run: exit_code = 0)>.
(3) <missing premise written in explicitly>.
-- <warrant rule without commas>. Unless: <defeater>; <ruled out by (n) | not ruled out | not tried>. --
(4) [Next]: So, <qualifier bought by (3)>, <conclusion answering ask>.
```
````

Messages making no claim (such as automated harness notices or claim-free directions) carry the null form:

````text
```argdown
===
asks: none
===

[no claim]
```
````

When an expected `argdown` block is absent from a claim-bearing report, `PASS` is refused by `verdict.py`: return it for revision (`REVISE` "no argument supplied"), instructing the sender: "No argument block supplied. Load the `premise-check` skill (`james:premise-check`) before writing your report; its Argdown dialect is a restricted subset of Argdown, so do not write the block from memory."

### Source Attribution Guidance

Premises state natural assertions citing sources and locators directly inline (e.g. `(path/to/file.py:42)`, `(run: exit_code = 0)`, `(task-id)`). Trailing mechanical `-- <basis phrase>` tails and endnote tables (`notes:`, `^a`) are omitted. Per the Human Readability First axiom, source attribution is evaluated semantically across these categories:

| Category | Evidentiary Basis | Examples / Guidelines |
| - | - | - |
| **Primary empirical observation** | Direct execution or reading | Raw observations quoting deciding values inline (`exit_code = 0`, diffs, logs, executed tests). |
| **Tested limits** | Direct reproduction or bounded search | Failed reproduction attempts with verbatim errors or bounded zero searches. |
| **Governing rule** | Formal framework or specification | Axioms, project rules, system specifications, or contracts. |
| **Reported finding** | Secondary report or task record | Secondary agent reports citing a recorded verification ID (`verdict-...`), or PKB task records. |
| **Assumed premise** | Unchecked assumption | Explicit assumption needed to complete an inference; requires qualifier in conclusion. |

### Rules for the Block

1. **The ask at the top**: Copy the asker's exact words under an immutable ID (`<channel>-<msg_id>`, `<task_id>/AC<n>`).
2. **Raw empirical observations**: Quote deciding values inline (`exit_code = 0`, `status: MERGED`). Never place evaluative or generalising conclusions restating an acceptance criterion ("AC1 is met") above an inference bar; derive them below an inference bar.
3. **Numbered premises**: Hold only grounds (observations, findings, sample bounds, scope conditions, or prior conclusions), never warrants. Write warrants inside `-- ... --` inference bars.
4. **Inline citations & metadata**: Place citations inline in report handbacks. When authoring standalone Argdown, `{basis, pointer, source, reason}` metadata and `#tags` (before `{...}`) follow [references/report-form.md](references/report-form.md).
5. **Single-line inference bar**: Starts `--`, ends `--`, on one line, with no commas inside the bar text: warrant rule, then `Unless: <defeater>; <status>`.
6. **Chain conclusions**: Each conclusion begins `So` directly beneath an inference bar. Stack up to 3 bars in one block; beyond that, start a new argument reusing the upstream conclusion's `[Title]` as premise `(1)`. Use `+>` (support), `->` (attack), `_>` (undercut targeting `<Inference>`), and `><` (contradict) without orphan statements.
7. **Relay upward**: Relaying a report requires its checked premise-check verdict; name the line each relayed sentence restates, relay only checked premises and conclusions with their qualifiers, never relay an argument with 0 inference lines or substantive defects as fact, propagate disclosed rule violations upward, and never relay a struck doubt as a risk.
8. **Method pairing line**: When an ask specifies a method, form, design, or value, place a `Departures:` line before the block pairing each specified feature beside what was done with its reason, else `Departures: none`.

## Checking a Received Direction or Report

### Directions

1. Verify every instruction derives faithfully from `## Ask` or active user directives.
2. **Turn-1 required input verification**: Even when a direction carries `[no claim]`, verify on Turn 1 that all required inputs, parameters, and target artifacts are present. If omitted, return `REVISE` immediately via `send_message` naming what is missing, without running `verdict.py`.
3. **No local log scraping**: Never read `.system_generated/logs/transcript*.jsonl` or `/tmp/aops_debug_hooks_*.jsonl` files to recover missing inputs; past execution traces belong in Arize Phoenix / OTel spans.
4. Verify brief satisfiability and refuse (`REVISE`) unverified caller method/template prescriptions (instructing the caller to load `james:premise-check`), except proportionate effort claims and closing review sequences in delegation briefs. Record deliverables as an explicit `## Acceptance` checklist before work starts.

### Reports (Explicit Verification)

`james` performs explicit report verification on receipt without automatic prompt-hook hearsay gating. Take observed premises with a pointer as given (never open a pointer or redo primary work unless settling a genuine conflict between two records; PKB notes or unverified peer prose rank as `worker reported, unchecked`).

- **Strike a doubt the run will settle**: A baseless doubt whether a route, tool, or step works when run (`not tried` with no reason given) is struck -- judge `Valid` as if absent and relay nothing from it.
- **Judge an admitted unchecked fact readable now**: A load-bearing premise admitted as unchecked ("assumed", "worker reported", "verified" with no cited run or verdict) is weak, not a doubt; it carries a qualifier and fails `#insufficient-for-stakes` when unable to bear the step's stakes.
- **Live-state source categories**: `Supported:` must name primary empirical observation (required for originating agents; secondary summary substitution fails `#insufficient-for-stakes`), verified child verdict relay (`verdict-...`), and match the reporter's observation surface (`#method-gap` or `#scope-drift` if wider).

Check the entire report for **Rule-Consistent** (no unpermitted rule breach left in delivered work; fail with `Valid: (n) fails #conflict`) and run four tests on every inference line:

| Test | Passes when | Failure looks like |
| - | - | - |
| **Valid** | Premises meet every condition of the warrant; conclusion stays within premises and observation surface; construct and sample hold; specified features are paired. | Missing condition (`#missing`); unruled defeater with basis or unchecked readable fact (`#unruled-defeater`); insufficient stakes (`#insufficient-for-stakes`); rule breach (`#conflict`); scope drift (`#scope-drift`); circular warrant or method gap (`#method-gap`); silent method/form substitution (`#construct-drift`). |
| **Supported** | Premises bear the step's stakes with named live-state source category. | Unbacked assertion, secondary summary substitution, or overreaching observation surface (`#insufficient-for-stakes` or `#method-gap`). |
| **Answered** | Conclusion answers each ask ID in substance (including establishing why an unfulfillable demand is unreachable by construction). | Narrower conclusion or marking a proved unreachability conclusion `unanswered`. |
| **Sufficient** | Proportionality holds with stakes named in words. Authority is strictly user words, governing spec, or cited verdict (never engine output); stakes-bearing conclusions never use "reversible" or "low-stakes". | Complex unbacked warrant without decomposition; settling stakes-bearing conclusions as low-stakes/reversible; asserting engine output as authority (`#insufficient-for-stakes`). |

When checking specified methods, forms, designs, or values, audit departures independently across all active user turns rather than trusting `Departures: none`. Medium nouns (diagram, spec, code) fix the deliverable medium (`#construct-drift` forces `FAIL`), and open deferrals to the user remain `#unruled-defeater`.

## Recording the Verdict

Before judging a report or recording a verdict, read [references/checker-reason.md](references/checker-reason.md) for the exact seven-line reason specification, refusal conditions, and `REVISE` / `FAIL` rules.

- **PASS**: All inferences hold (>= 1 inference line), all asks answered, evidence bears the stakes, and no rule violations in delivered work. Format-only defects on a sound argument are waived under `Waived:` and rewritten by the receiver.
- **REVISE**: Name line, defect tag, and remedy, and instruct sender: "Load the `premise-check` skill (`james:premise-check`) before writing your revised report." To send back a sound argument for an unwaived format slip, keep all `Valid:` lines `holds` and add `Format: <format item> -- <what to fix>`.
- **FAIL**: Conclusion fails to answer the ask, contradicts evidence, or breaches non-waivable rules/fidelity.

Write the seven keyed lines to a reason file:

```text
Judged: <claim id>; asks <ask id>, <ask id>
Valid: (n) holds -- <rule and why it yields (n) here>
Supported: (<premise n>) <source category; qualitative evaluation of evidence against stakes>
Answered: <ask id> ← (n)
Sufficient: (n) material; <stakes in words>; <obvious | authority-backed | cited verdict | low-stakes | sent back>; <necessity of any objection>
Waived: none | <format item> -- <justification>
Relay: "<sentence to relay>" ← (n) | none
```

Record the verdict and emit its OpenTelemetry span:

```bash
uv run --project <plugin-dir> python <plugin-dir>/skills/premise-check/scripts/verdict.py --session <session_id> --claim <claim_id> --verdict <PASS|REVISE|FAIL> --reason-file <path> --judged-file <path>
```

Resolve `<plugin-dir>` to the real installed `james` plugin directory (`Path.resolve()` on symlinks). Passing `--judged-file <path>` is required for `PASS` so `verdict.py` validates the report's fenced `argdown` block directly against `report_argument.py` and exports the `premise_check_verdict` span.

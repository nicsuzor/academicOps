# Report form

The report argument is one fenced `argdown` block at the end of the report in parser-valid Chained Toulmin Argdown standard form. Frontmatter between `===` lines carries optional document metadata (`title`, `granularity`, `model: mode: strict`) and report routing (`asks`, `answers`). Readers ignore meaning-free whitespace across the block (common leading indents across frontmatter or body, trailing whitespace, CRLF endings, and blank lines); relative frontmatter indentation and single-line inference bars remain significant. Transport envelopes (such as XML `<task-notification><result>...</result>`) entity-escape `<`, `>`, and `&`; readers decode HTML entities before parsing.

````text
```argdown
===
title: <title>
granularity:
  level: <micro | meso | macro>
  floor: "<one sentence naming what counts as a leaf>"
model:
  mode: strict
asks:
  <ask id>: <the asker's own words, one question>
  <ask id>: <next question>
answers:
  <ask id>: <integer line number, statement title, or none>
  <ask id>: none
===

# Main Conclusion

[Main Claim]: <overall claim when authoring multi-argument Argdown>. {basis: "stated", pointer: "...", source: "..."}

# Arguments

<Line of Support>: <gist of how this chain supports the conclusion>.

(1) [Label]: <premise with inline citation or attributes>. {basis: "observed", pointer: "...", source: "..."}
(2) <premise quoting the deciding value inline (path/to/file.py:42)>.
(3) <missing premise, written in>.
-- <warrant without commas: rule that could be false on its own>. Unless: <defeater>; <ruled out by (n) | not ruled out | not tried>. --
(4) [Conclusion]: So, <qualifier bought by (3)>, <conclusion>.
(5) <premise of the next step with inline citation (run: exit_code = 0)>.
-- <warrant using (4) and (5)>. Unless: <defeater>; <status>. --
(6) So <conclusion>.
  +> [Main Claim]
```
````

## Line shapes

| Part | Shape |
| - | - |
| `asks` | Frontmatter map (ask ID to asker's words) or list of records (`- id: <ask id>`, `text: <words>`). Id: `<channel>-<message id>` (`msg-2008`), or `<task id>/AC<n>`. No spaces. |
| `answers` | Frontmatter map: ask ID to raw integer line number (`4`, not `(4)`), statement title (`Next` or `[Next]`), or `none`. |
| Statement | `[Title]: text`. Reuse a title exactly to refer to the same statement; a new title creates a new statement. |
| Argument | `<Title>: gist`, followed by a premise-conclusion block. |
| Premise | `(n) <ground statement with inline citations and quoted values>`. Premises hold only grounds (observations, findings, bounds, prior conclusions), never warrants. |
| Inference | Starts `--`, ends `--`, on one line. Warrant rule (written without commas), then `Unless:`, defeater, `;` and status. Optional `{uses: [1, 2], basis: "...", pointer: "..."}` before closing `--`. |
| Conclusion | Numbered line directly after an inference line. Starts `So`. Carries no basis. |

Pointers and citations in peer handback reports live directly inline in natural prose without lettered endnote tables (`notes:`, `^a`):

- File locations: `(plugins/james/hooks/handlers.py:254)`
- Task or note links: `(task-id)` or `task-id`
- Runtime executions: `(run: exit_code = 0)`

Numbers run on through a chain: a coordinator quoting a worker's lines keeps their numbers and continues from the next one.

## Chaining, layer separation, and relations

- **Relevance rule**: Every premise on an inference is a condition of its warrant; keep one bar per epistemic layer (observation and method to pattern, pattern and mechanism to diagnosis, diagnosis and standard to evaluation).
- **Chain, do not widen**: Stack up to 3 inference bars in one block. Beyond 3 bars, start a new argument whose premise `(1)` reuses the upstream conclusion's `[Title]`.
- **Backing**: Backing for a warrant goes in the bar's metadata or in a child argument concluding the warrant.
- **Relations**: Write each relation on its own indented line below the statement or argument it starts from, attached to the argument that concludes or first states the claim (never to one that only borrows it as a premise):
  - `+>` supports a statement.
  - `->` attacks a statement (a reply to an objection attacks the objection).
  - `_>` undercuts an inference (`<Warrant Title>`, never a statement or line number).
  - `><` marks two statements that contradict.

## Metadata keys and diagnostic tags

Full Chained Toulmin Argdown documents attach `{basis, pointer, source, reason}` on every premise and warrant that is not a derived intermediate conclusion:

- `basis` (closed vocabulary):
  - `"observed"`: finding, quotation, measured value, or inspected state (quote deciding value inline or in `source`).
  - `"method-bounded"`: scope or limit of a method (sampling frame, operational definition, instrument limit).
  - `"exhaustively-searched"`: absence or count from a search whose full boundary is stated.
  - `"attempted-and-failed"`: absence or incapacity shown by a stated attempt that failed.
  - `"theory"`: principle, mechanism, legal rule, or normative standard from scholarship or a governing rule.
  - `"reported-by"`: claim adopted from a cited secondary source or report (quote deciding value inline or in `source`).
  - `"stated"`: author's framing (question, definition, scope, roadmap claim).
  - `"assumed"`: supplied to complete an inference and found in no source (pair with `#missing` when it names an assumed condition).
- `pointer`: locator a reader can open (page/paragraph, section, citation handle, `owner/repo@sha:path:line`, node or span ID, URL, or exact query run).
- `source`: verbatim quote (line breaks joined by single spaces, original markup kept) or exact observed value.
- `reason`: for `"assumed"` only, the gap the item bridges (assumed items carry no `pointer` or `source`).

Diagnostic tags sit before `{metadata}` and mark open issues:

- `#missing`: premise, warrant, or bridge the step needs that the text does not state.
- `#needs-evidence`: load-bearing premise with no data or authority behind it.
- `#scope-drift`: conclusion wider than its premises license in population, quantifier, or construct.
- `#method-gap`: method that cannot observe what the step claims from it.
- `#unanswered`: objection or rival explanation the argument does not meet.
- `#conflict`: two contradicting claims joined by `><`, or a rule violation in delivered work.
- `#format`: document that breaks this standard.

## Granularity

`level` sets depth; `floor` states in one sentence what counts as a leaf (leaf statements carry metadata and get no sub-argument):

- `macro`: whole work (one argument per major part; default floor: part-level findings and cited theories).
- `meso` (default for papers/specs): section or paper (default floor: individual cited sources, summary statistics, uncontested definitions).
- `micro` (default for report handbacks): 1 to 3 load-bearing inferences down to raw observations with inline citations/pointers.

## Parser compliance and validation expectations

- Keep `(1) [Title]: text #tag {metadata}` on one line, or put `{metadata}` alone on an indented continuation line; never place a tag after `{metadata}`.
- Write inference-bar text (`-- ... --`) on one line without commas, because Argdown parsers split bar text on commas into separate rules.
- Escape literal underscores in statement prose as `\_`, and keep unescaped `[` `]` `<` `>` out of statement prose (escapes do not apply inside quoted `source` strings).
- Never put a colon after a premise number (`(1):` is invalid), never use Markdown numbered lists (`1.` / `1)`), never leave unclosed `===` or `--` delimiters, never aim `_>` at a statement or line number, and never leave orphan statements with no relations or argument membership.
- Report handbacks and peer messages follow these syntax rules directly without running external CLIs or test scripts; the checker validates the report's block via `verdict.py --judged-file <path>` against `report_argument.py`. Standalone `.argdown` files may optionally be validated with `npx -y @argdown/cli json --logParserErrors --throwExceptions <file>.argdown <outdir>` (at most 3 fix attempts before halting on error).

## Method fidelity and departures

When an ask specifies a method, form, design, or value, place a `Departures:` line before the argument block pairing each specified feature beside what was done, naming each departure with its reason, else `Departures: none`.

- **Shape**: `Departures: none` or `Departures: <specified feature> -> <what was done> (<reason>); ...`
- **Default rule**: A detail in a method specification is load-bearing regardless of typography unless the ask's purpose shows it free.
- **Rewording**: Rewording that preserves the construct is not a departure.

## Short example

Departures: none

```argdown
===
asks:
  msg-1: is the hook enforced?
answers:
  msg-1: 4
===

(1) A hook that only advises cannot block an agent (governing rule).
(2) The hook returns "block", not advice (read from plugins/james/hooks/handlers.py).
(3) The agent runtime honours a "block" from a hook (assumed, not checked here).
-- A hook that returns "block" to a runtime that honours it is enforced. Unless: this runtime ignores hook output in the mode it runs in; not ruled out. --
(4) So, most likely, the hook is enforced.
```

## Null form (minimal compliance)

When a message makes no claim (such as automated harness notices or claim-free directions), use the null form defined in [SKILL.md](../SKILL.md#writing-the-report-argument).

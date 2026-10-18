---
name: argdown-toulmin
description: The grammar and presentation standard for writing an argument as Chained Toulmin Argdown -- statements, numbered premises, warrants in the inference bar, chaining, relations, `{basis, pointer, source, reason}` metadata, diagnostic tags, granularity, layout, and parser validation. Load before writing, editing, or parsing any Argdown. Not a procedure for reconstructing, evaluating, or reporting an argument.
---

# Chained Toulmin Argdown

How an argument is written. Every Argdown document follows this standard.

## Document

- **Frontmatter** between `===` lines. Required: `title`, `granularity` (`level`, `floor`), and `model: mode: strict`. Add other keys as the document needs (for example `source`, `author`, `date`).
- **Main conclusion first**, as a titled statement, then the arguments for it. Group arguments under Argdown headings.

## Statements and arguments

- **Statement**: `[Title]: text`. Reuse a title exactly to mean the same statement; a new title is a new statement.
- **Argument**: `<Title>: gist`, followed by a premise-conclusion block.
- **Premises** are numbered `(1)`, `(2)` and hold only grounds: observations, findings, sample bounds, scope conditions, or prior conclusions.
- **Warrant in the inference bar**: `-- Name: warrant text {uses: [1, 2], basis: "...", pointer: "..."} --`. The warrant is the rule, principle, mechanism, or method that licenses the step. A warrant is never a numbered premise.
- **Backing** (what shows the warrant holds) goes in the bar's metadata. A warrant that needs its own support gets a child argument concluding it.
- **At most 3 premises per bar, ideally 2.** Four premises are at least two steps: split them with an intermediate conclusion and a second bar.
- **One bar per epistemic layer**: observation and method to pattern, pattern and mechanism to diagnosis, diagnosis and normative standard to evaluation.
- **Chain, don't widen.** Stack up to 3 bars in one block. Beyond that, start a new argument whose premise `(1)` reuses the upstream conclusion's title.

## Relations

Write each relation on its own indented line below the statement or argument it starts from.

- `+>` supports a statement.
- `->` attacks a statement. A reply to an objection is an attack on the objection.
- `_>` undercuts an argument: it attacks the inference, not a premise.
- `><` marks two statements that contradict.

Attach a relation to the argument that concludes or first states the claim, never to one that only borrows it as a premise.

## Metadata

`{basis, pointer, source, reason}` on every premise and warrant that is not a derived intermediate conclusion.

- `basis`, how the claim is known:
  - `"observed"`: a finding, quotation, measured value, or inspected state.
  - `"method-bounded"`: the scope or limit of a method: a sampling frame, operational definition, or instrument limit.
  - `"exhaustively-searched"`: an absence or count from a search whose full boundary is stated.
  - `"attempted-and-failed"`: an absence or incapacity shown by a stated attempt that failed.
  - `"theory"`: a principle, mechanism, legal rule, or normative standard from scholarship, doctrine, or a governing rule.
  - `"reported-by"`: a claim adopted from a cited secondary source or report.
  - `"stated"`: the author's own framing: research question, definition, scope, or roadmap claim.
  - `"assumed"`: supplied to complete an inference and found in no source.
- `pointer`: a locator a reader can open: page and paragraph, section, citation handle, `owner/repo@sha:path:line`, node or span ID, URL, or the exact query run.
- `source`: the verbatim quote (line breaks joined by single spaces, original markup kept) or the exact observed value. A derived intermediate conclusion has no `source` unless the text states it verbatim.
- `reason`: for `"assumed"` only, the gap the item bridges. An assumed item has no `pointer` or `source`.

An `"observed"` or `"reported-by"` item quotes its deciding value or text (`status: MERGED`, `p = 0.004`) inline or in `source`, because a bare pointer shows only that something exists.

An assumed inference rule goes in the bar with `basis: "assumed"`. An assumed condition goes in a numbered premise with `basis: "assumed"` and `#missing`.

## Tags

Tags go before the `{metadata}`. Each tag marks one kind of open issue:

- `#missing`: a premise, warrant, or bridge the step needs and the text does not state.
- `#needs-evidence`: a load-bearing premise with no data or authority behind it.
- `#scope-drift`: a conclusion wider than its premises license, in population, quantifier, or construct.
- `#method-gap`: a method that cannot observe what the step claims from it.
- `#unanswered`: an objection or rival explanation the argument does not meet.
- `#conflict`: two claims that contradict, joined by `><`.
- `#format`: a document that breaks this standard.

## Granularity

`level` sets how deep the document goes; `floor` is one sentence naming what counts as a leaf. A statement at the floor carries its metadata and gets no sub-argument.

- `macro`: a whole work. Thesis, part-level and chapter-level claims, one argument per chapter or section. Default floor: chapter-level findings and cited theories.
- `meso` (default): a paper, chapter, or section. Main conclusion and each line of support down to primary findings, method bounds, and warrants. Default floor: individual cited sources, summary statistics, and uncontested definitions.
- `micro`: one to three load-bearing inferences, down to operational definitions, sampling bounds, and warrant backing. Default floor: raw observations with verbatim pointers.

## Presentation

- Statement text is clear, direct, modern prose. The author's own wording goes verbatim in `source`, not in the statement.
- One blank line between arguments and around headings.

```argdown
===
title: Work or question, part covered
granularity:
  level: meso
  floor: "One sentence naming what counts as a leaf."
model:
  mode: strict
===

# Main Conclusion

[Main Claim]: The claim the document establishes. {basis: "stated", pointer: "...", source: "..."}

# Arguments

<Line of Support>: How this chain supports the main claim.

(1) [Finding]: What was observed. {basis: "observed", pointer: "...", source: "..."}
(2) [Bound]: The scope of the method or sample. {basis: "method-bounded", pointer: "...", source: "..."}
-- Method Warrant: Why the method captures the pattern {uses: [1, 2], basis: "stated", pointer: "..."} --
(3) [Pattern]: The pattern the data establish.
(4) [Condition]: A further condition the next step needs. {basis: "observed", pointer: "...", source: "..."}
-- Mechanism Warrant: The rule that turns the pattern into the claim {uses: [3, 4], basis: "theory", pointer: "..."} --
(5) [Section Claim]: The claim this chain supports.
  +> [Main Claim]
```

## Parser compliance

- Keep each statement (`(1) [Title]: text #tag {metadata}`) on one line, or put its `{metadata}` alone on an indented continuation line. The parser rejects a tag after the metadata.
- Write inference-bar text without commas, because the parser splits bar text on commas into separate rules.
- Escape a literal underscore in statement text as `\_`, and keep unescaped `[` `]` `<` `>` out of statement prose. Escapes do not apply inside quoted `source` strings.
- Validate with `npx -y @argdown/cli json --logParserErrors --throwExceptions <file>.argdown <outdir>`. On a syntax error, fix it from the parser message and retry, at most 3 times; if it still fails, halt and report the error.
- Then read the JSON and confirm every argument appears with its premises and reaches the main conclusion, through a relation or a conclusion title reused as a premise.

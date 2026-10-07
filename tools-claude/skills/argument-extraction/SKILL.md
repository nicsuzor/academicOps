---
name: argument-extraction
description: Extract the argument a text makes -- main conclusion, premises, and inferential structure -- and emit it as parser-valid Argdown with every element traced to a source passage. Use for "extract the argument", "map the argument", "reconstruct the reasoning", "argdown this". Not for evaluating or rebutting the argument (use peer-review), or for a descriptive summary of aims and methods alone.
---

# Argument Extraction

Reconstruct what a text argues, as Argdown, without evaluating it.

## Procedure

1. **Survey the text first.** Read through the text to identify the central thesis and main lines of reasoning before drafting Argdown. Extract rather than infer, preserve the author's framing, and look past document sectioning to find what the text actually establishes.
2. **Fix the main conclusion.** One statement: the primary claim the text exists to establish, rewritten in clear, simpler modern English. Because the verbatim quote and citation appear immediately below, do not repeat archaic or verbatim phrasing in the claim itself.
3. **Find each line of support.** For every distinct reason the text gives for the main conclusion, reconstruct one argument: its stated premises, any intermediate conclusions, and the conclusion it supports. Express every premise and conclusion in simpler modern English. Where one argument's conclusion is a premise of another, reuse the same statement title in both. An objection the author raises and answers is an attack (`->`) on the claim it targets, with the answering argument supporting that claim. A branch the text announces but does not argue within the extract is omitted and listed under `omitted` in the frontmatter.
4. **Supply missing premises only when the inference needs them.** State the implicit premise in simpler modern English and mark it `{implicit: true, reason: "..."}` naming the logical gap it bridges. Never present an implicit premise as stated.
5. **Validate with a bounded repair loop.** Run `npx -y @argdown/cli json --logParserErrors --throwExceptions <file>.argdown <outdir>`. If syntax errors occur, inspect the parser error, correct the syntax, and retry (at most 3 attempts; if still invalid after 3 attempts, halt and report the error). Then read the JSON and confirm every argument appears with its premises and that every argument reaches the main conclusion, either through a relation or through a conclusion title reused as a premise in another argument's `pcs`.

## Output Contract

One `.argdown` file:

- **Frontmatter** (`===` block): `title` naming author, work, and the extract analysed; `source` giving an edition or URL and the extract's locator; `omitted` when step 3 omitted a branch.
- **Main conclusion** as a titled statement, `[Title]: text`. Express the core thesis in simpler modern English.
- **One premise-conclusion structure per argument**, under a `<Title>: gist` line: numbered statements `(1)`, `(2)`, a `----` inference line, then the conclusion, which either links to what it supports with `+>` (or `->` for an attack) or reappears by title as a premise of another argument. Express each premise and conclusion in simpler modern English.
- **Traceability.** Every stated statement carries `{source: "<verbatim quote>", locator: "<page, paragraph, or line>"}`. The quote is copied exactly from the source, with line breaks joined by single spaces and source markup kept as is; a paraphrase is not a source. Because the verbatim source quote is attached directly below, the statement text itself must never echo archaic or verbatim phrasing--it should state the claim simply and directly. Derived conclusions carry no `source` unless the text states them.
- **Parser compliance.** One statement per line, a blank line between arguments, `\_` for literal underscores, no unescaped `[` `]` `<` `>` inside statement text. These escapes apply to statement text, not to quoted `source` strings.

## Example

`references/example-mill-on-liberty.argdown`: Mill, _On Liberty_, ch. II, the four-grounds recapitulation.

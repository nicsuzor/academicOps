---
name: argument-extraction
description: Extract the argument a text makes -- main conclusion, premises, and inferential structure -- and emit it as parser-valid Argdown with every element traced to a source passage. Use for "extract the argument", "map the argument", "reconstruct the reasoning", "argdown this". Not for evaluating or rebutting the argument (use peer-review), or for a descriptive summary of aims and methods alone.
---

# Argument Extraction

Reconstruct what a text argues, as Argdown, without evaluating it.

## Procedure

1. **Map the text first.** Resolve the workflow template `wf-structural-map` with `/ida:workflow-library view wf-structural-map` and run it over the text as working input; the map is not part of the output. Its rules govern this skill too: extract rather than infer, preserve the author's framing, and look past document sectioning. Locate the main conclusion from the Aims and Contribution sections, or, where those are `Not stated`, from the text's own statement of what it establishes.
2. **Fix the main conclusion.** One statement: the claim the text exists to establish, in the author's terms.
3. **Find each line of support.** For every distinct reason the text gives for the main conclusion, reconstruct one argument: its stated premises, any intermediate conclusions, and the conclusion it supports. Where one argument's conclusion is a premise of another, reuse the same statement title in both. An objection the author raises and answers is an attack (`->`) on the claim it targets, with the answering argument supporting that claim. A branch the text announces but does not argue within the extract is omitted and listed under `omitted` in the frontmatter.
4. **Supply missing premises only when the inference needs them.** Mark each `{implicit: true, reason: "..."}` naming the gap it fills. Never present an implicit premise as stated.
5. **Validate.** Run `npx -y @argdown/cli json --logParserErrors --throwExceptions <file>.argdown <outdir>`. A non-zero exit is a failure: fix the syntax and rerun. Then read the JSON and confirm every argument appears with its premises and that every argument reaches the main conclusion, either through a relation or through a conclusion title reused as a premise in another argument's `pcs`.

## Output Contract

One `.argdown` file:

- **Frontmatter** (`===` block): `title` naming author, work, and the extract analysed; `source` giving an edition or URL and the extract's locator; `omitted` when step 3 omitted a branch.
- **Main conclusion** as a titled statement, `[Title]: text`.
- **One premise-conclusion structure per argument**, under a `<Title>: gist` line: numbered statements `(1)`, `(2)`, a `----` inference line, then the conclusion, which either links to what it supports with `+>` (or `->` for an attack) or reappears by title as a premise of another argument.
- **Traceability.** Every stated statement carries `{source: "<verbatim quote>", locator: "<page, paragraph, or line>"}`. The quote is copied exactly from the source, with line breaks joined by single spaces and source markup kept as is; a paraphrase is not a source. Derived conclusions carry no `source` unless the text states them.
- **Parser compliance.** One statement per line, a blank line between arguments, `\_` for literal underscores, no unescaped `[` `]` `<` `>` inside statement text. These escapes apply to statement text, not to quoted `source` strings.

## Example

`references/example-mill-on-liberty.argdown`: Mill, _On Liberty_, ch. II, the four-grounds recapitulation.

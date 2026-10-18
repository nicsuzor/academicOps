---
name: argument-extraction
description: Extract and reconstruct the argument a text or draft makes -- main conclusion, chained premises, warrants, and evidence traceability -- and emit it as parser-valid Chained Toulmin Argdown at a controlled level of granularity. Use for "extract the argument", "map the argument", "reconstruct the reasoning", "argdown this". Not for evaluating the argument (use argument-audit), for a readable map with gaps tagged (use argument-map), or for agent handback reports (use premise-check).
---

# Argument Extraction

Reconstruct what a text argues into parser-valid **Chained Toulmin Argdown**, preserving the author's framing while making every inference step, warrant, and source trace explicit without evaluate-on-the-fly editorialising.

## When to Use

- Extracting the logical structure of an academic paper, thesis chapter, legal judgment, policy report, or philosophical text
- Converting unstructured prose or flat mind-maps into a hierarchical, non-flat Argdown model
- Preparing a faithfully traced reconstruction before running `argument-audit` or `premise-check`

## Core Representation: Chained Toulmin

To prevent "flat laundry lists" (where 5 to 7 premises are dumped above a single line), every argument block follows three structural rules:

1. **Grounds in numbered premises (`(1)`, `(2)`)**: Put only observations, empirical findings, established sub-claims, or scope conditions in numbered lines. Cap each inference step at **2 (at most 3) co-dependent premises**.
2. **Warrants in the inference bar (`-- Warrant --`)**: Place the licensing rule, theoretical principle, causal mechanism, or methodological rule inside the Argdown inference line (`-- Warrant statement {uses: [1, 2], basis: "...", pointer: "..."} --`). Never mix warrants into the numbered premise list as flat siblings of the data.
3. **Depth via chained staircases, not wide lists**: When reasoning moves across epistemic layers (for example, _Method/Observation -> Empirical Pattern -> Causal Mechanism -> Normative Conclusion_), stack up to 3 `-- Warrant --` bars inside one `<Argument>` block, or chain distinct `<Argument>` blocks by reusing a conclusion's `[Title]` as Premise `(1)` of the downstream block.

## Procedure

### 1. Set the Granularity Contract Before Drafting

Inspect the text and the user's goal to choose the target abstraction level (`macro`, `meso`, or `micro`) and write a one-sentence `floor` rule in the frontmatter:

- **`macro` (Thesis / Book / Multi-part synthesis)**: Map only the core thesis, part-level claims, and chapter-level conclusions (1 `<Argument>` per chapter/section). Floor: accept chapter-level empirical findings and cited theories as leaf nodes.
- **`meso` (Paper / Chapter / Section argument - Default)**: Map the main conclusion and each distinct line of support down to the primary empirical findings, methodological bounds, and theoretical warrants. Floor: accept individual cited sources, dataset summary statistics, and uncontested definitions as leaf nodes without unpacking their internal proofs.
- **`micro` (Single contested step / Method audit)**: Unpack a single load-bearing inference down to its operational definitions, sampling bounds, and warrant backing. Floor: accept raw observations with verbatim pointers as leaf nodes.

Once a premise hits the declared `floor`, stop recursing: record its `{basis, pointer, source}` inline and do not spawn a sub-argument for it.

### 2. Fix the Main Conclusion

Write one top-level titled statement (`[Title]: text`) expressing the primary claim the text exists to establish in clear, direct modern English. Because the verbatim quote appears in `source`, do not copy archaic or convoluted wording into the statement text.

### 3. Reconstruct Each Line of Support as a Chained Toulmin Block

For each distinct line of reasoning supporting the main conclusion (or supporting an intermediate chapter/section claim):

- Pair **what is observed or established** in `(1)` and `(2)` with **the warrant that licenses the step** in `-- Warrant {uses: [1, 2], basis: "...", pointer: "..."} --`.
- Reuse exact `[Statement Titles]` whenever the conclusion of one `<Argument>` serves as a premise in a higher-level `<Argument>`.
- Map objections the author raises and answers using attack relations (`-> [Target Claim]` for an objection to a claim; `_> <Target Argument>` for a rival explanation or methodological limit that undercuts a warrant), and map the author's reply as an attack (`->`) on the objection.
- Omit branches the text announces as out of scope or leaves for another work, recording them under `omitted` in the frontmatter.

### 4. Surface Unstated Premises and Warrants Explicitly

When the author leaps from `(1)` to `(2)` without stating a necessary bridging premise or warrant:

- If the missing link is the **inference rule or principle**, write it in the `-- Warrant --` bar with `{uses: [...], basis: "assumed", reason: "<logical gap bridged>"}`.
- If the missing link is an **empirical or behavioural condition** needed alongside `(1)`, add it as a numbered premise with `{basis: "assumed", reason: "<logical gap bridged>"}` and tag `#missing`.
- Never attribute an unstated premise to `source`.

### 5. Attach Unified Traceability Metadata

Every stated premise and stated warrant carries `{basis, pointer, source}`:

- `basis`:
  - `"observed"`: Empirical finding, qualitative quote, dataset metric, or pinpoint state.
  - `"method-bounded"`: Sampling frame, operational definition, or bounded negative search (`"every title in the catalogue checked on a named date"`).
  - `"theory"`: Theoretical principle, causal mechanism, legal rule, or normative standard from scholarship or doctrine.
  - `"reported-by"`: Claim adopted from a cited secondary source or upstream verified report.
  - `"stated"`: Author's research question, scoping definition, or thesis roadmap claim.
  - `"assumed"`: Unstated premise or warrant supplied to complete an inference (paired with `reason` instead of `source`).
- `pointer`: Page, paragraph, section, line locator, citation handle, or node ID.
- `source`: Verbatim quote from the text (line breaks joined by single spaces, original markup preserved) or exact observed metric. Derived intermediate conclusions omit `source` unless the text states them verbatim.

### 6. Validate Parser Compliance

Ensure the output is strict, parser-valid Argdown:

- Keep each statement (`(1) [Title]: text #tag {metadata}`) on one line, or put its `{metadata}` alone on an indented continuation line. Tags come before the `{metadata}`; the parser rejects a tag after it.
- Put a relation (`+>`, `->`, `_>`, `><`) on its own indented line below the statement, never inline after it.
- Write the inference-bar text without commas: the parser splits bar text on commas into separate inference rules, so a comma breaks the warrant into fragments.
- Put a blank line between `<Argument>` blocks and before/after headings.
- Escape literal underscores inside statement text as `\_`, and never leave unescaped `[` `]` `<` `>` inside statement prose (escapes do not apply inside quoted `source` strings).
- Run `npx -y @argdown/cli json --logParserErrors --throwExceptions <file>.argdown <outdir>`. On a syntax error, inspect the parser message, correct the syntax, and retry (at most 3 attempts; if still invalid, halt and report the error). Then read the JSON and confirm every argument appears with its premises and reaches the main conclusion, through a relation or through a conclusion title reused as a premise of another argument.

### 7. Record in PKB

When saving an extracted argument to a PKB note (via `pkb.create`), pass the source artefact's PKB-relative path as `source` (e.g. `<subproject>/<artefact>`), or set `parent` to a node whose file lives in that sub-project directory. Under the home-directory placement rule, this files the note in that sub-project directory.

## Output Template

```argdown
===
title: Author, Work (Year), section analysed
source: PKB-relative path, edition, URI, or document identifier
granularity:
  level: meso
  floor: "Accept cited theoretical literature and summary empirical metrics as leaf nodes."
omitted:
  - "Branch announced in text but deferred to another chapter"
model:
  mode: strict
===

# Main Conclusion

[Core Thesis]: Clear, direct statement of the main conclusion. {basis: "stated", pointer: "sec. 1, para. 2", source: "Verbatim thesis statement from text."}

# Arguments

<Line of Support 1>: Short gist of how this chain supports the thesis.

(1) [Empirical Finding]: Clear statement of what the author observed or measured. {basis: "observed", pointer: "p. 14, para. 3", source: "Verbatim quote of the finding."}
(2) [Sampling Bound]: Scope of the instrument or sample used. {basis: "method-bounded", pointer: "p. 12, para. 1", source: "Verbatim quote of the method bound."}
-- Method Warrant: Why this sample and instrument validly capture the phenomenon {uses: [1, 2], basis: "stated", pointer: "p. 12, para. 2", source: "Verbatim quote of methodological justification."} --
(3) [Intermediate Pattern]: The general empirical pattern established by the data.
(4) [Contextual Condition]: Additional stated condition or scope fact. {basis: "observed", pointer: "p. 15, para. 1", source: "Verbatim quote."}
-- Theoretical Warrant: The mechanism or normative principle that turns the pattern into the conclusion {uses: [3, 4], basis: "theory", pointer: "p. 16, para. 2", source: "Verbatim quote of theoretical rule."} --
(5) [Section Claim]: Resulting claim that supports the main conclusion.
  +> [Core Thesis]
```

## Example

`references/example-mill-on-liberty.argdown`: Mill, _On Liberty_, ch. II, the four-grounds recapitulation, at `meso` granularity.

## Gotchas

- **Never dump 4+ premises above one bar**: If you have 4 premises, you have at least two distinct inference steps (for example, a method-to-finding step and a finding-to-mechanism step). Split them with an intermediate conclusion and a second `-- Warrant --` bar.
- **Do not confuse Backing with Grounds**: Literature that justifies _why a warrant holds_ belongs in the `-- Warrant {basis: "theory", pointer: "..."} --` line (or in a child argument concluding that warrant if contested), not as a numbered sibling premise next to empirical data.
- **Preserve authorial voice in `source`, clarity in prose**: Statement text should be crisp, modern declarative prose; `source` holds the exact verbatim quote.

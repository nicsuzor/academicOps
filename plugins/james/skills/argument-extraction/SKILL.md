---
name: argument-extraction
description: Extract and reconstruct the argument a text or draft makes -- main conclusion, chained premises, warrants, and evidence traceability -- and emit it as parser-valid Chained Toulmin Argdown at a controlled level of granularity. Use for "extract the argument", "map the argument", "reconstruct the reasoning", "argdown this". Not for evaluating the argument (use argument-audit), for a readable map with gaps tagged (use argument-map), or for agent handback reports (use premise-check).
---

# Argument Extraction

Reconstruct what a text argues, preserving the author's framing while making every inference step, warrant, and source trace explicit, without editorialising. Read `ida:argdown-toulmin` before drafting: it sets the grammar, metadata, tags, granularity levels, layout, and parser validation.

## When to Use

- Extracting the logical structure of an academic paper, thesis chapter, legal judgment, policy report, or philosophical text
- Converting unstructured prose or flat mind-maps into a hierarchical, non-flat Argdown model
- Preparing a faithfully traced reconstruction before running `argument-audit` or `premise-check`

## Procedure

### 1. Set the Granularity Contract

Choose the `level` that fits the text and the user's goal, and write its one-sentence `floor` in the frontmatter. Once a premise hits the floor, record its metadata and stop recursing.

### 2. Fix the Main Conclusion

Write one titled statement expressing the primary claim the text exists to establish.

### 3. Reconstruct Each Line of Support

For each distinct line of reasoning supporting the main conclusion, or an intermediate chapter or section claim:

- Pair what is observed or established in the premises with the warrant that licenses the step in the bar.
- Reuse exact titles wherever one argument's conclusion serves as a premise of a higher-level argument.
- Map the objections the author raises as attacks (`->` on a claim, `_>` on an argument for a rival explanation or methodological limit), and the author's replies as attacks on those objections.
- Omit branches the text announces as out of scope or leaves for another work, listing them under `omitted` in the frontmatter.

### 4. Surface Unstated Premises and Warrants

Where the author leaps between steps without stating a necessary bridging premise or warrant, supply it as an assumed item with a `reason`, never attributed to `source`.

### 5. Attach Traceability Metadata

Give every stated premise and stated warrant its `{basis, pointer, source}`, quoting the text verbatim in `source`.

### 6. Validate

Run the parser and the JSON structure check. Deliver only a source that passes both.

---
description: Always explain your reasoning. All claims must be supported in strict, parseable argdown syntax.
trigger: always_on
---

### Always provide your reasoning: quick reference on required syntax

Integrity requires traceability. Any claim you rely on or communicate must be accompanied by written, parseable reasons in a common chained Toulmin form to enable future auditing.

- Strict compliance with `argdown` syntax is required for parsing. Escape reasoning with `argdown\n...\n` blocks.
- **Put grounds in `(1)–(2)` and warrants in `-- Warrant {uses: [1, 2]} --**`: Never mix theoretical rules or methods into numbered premise lists alongside empirical findings; cap every inference bar at 2 (max 3) co-dependent premises and stack bars vertically (`Observation -> Pattern -> Mechanism -> Normative Claim`) to create depth instead of flat lists.
- **Lock the granularity floor upfront (`granularity: {level, floor}`)**: Declare `macro` (thesis/part), `meso` (chapter/paper), or `micro` (single contested step) plus a one-sentence `floor` in the frontmatter; once a premise hits that floor, record its `{basis, pointer, source}` inline and stop recursing.
- **Quote the deciding value beside every pointer**: A bare locator (`p. 14` or `repo@sha:path`) only proves a source exists; every `observed`, `method-bounded`, or `reported-by` premise must include the exact metric, state, or verbatim quote in `source`.
- **Check nouns and quantifiers across every bar (`#scope-drift`)**: Compare the subject, population, and strength of `(1)–(2)` against `(3)`; if the conclusion shifts from a proxy (_sticker price_, _commercial absence_) to a substantive construct (_household exclusion_, _lost cultural value_), either insert the missing bridge premise or narrow the conclusion's qualifier.
- **Run the Contrast Test on every causal or interpretive warrant (`_> #unanswered`)**: Ask _"What is the nearest alternative explanation where this exact evidence would look the same?"_--and map that rival explanation or method limit as an undercut (`_>`) targeting the `<Argument>`, not a generic attack (`-`) on the conclusion.
- **Stop splitting when flipping the warrant wouldn't change the outcome**: Only unpack a sub-argument or demand new evidence when a warrant is material and contested in context; fix weak links using the lowest-friction move first (**narrow the qualifier** $\rightarrow$ **cite a theoretical bridge** $\rightarrow$ **run a targeted empirical control**).

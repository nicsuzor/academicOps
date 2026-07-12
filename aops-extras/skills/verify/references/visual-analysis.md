# Visual Analysis — Structural Integrity

A protocol for critically evaluating visual artifacts (UI mockups, screenshots, rendered dashboards, charts, slides) at QA time. This is **structural**, not psychological — cognitive-load and emotional-response dimensions are design-time questions and live in the spec's Fitness Rubric, not here.

Apply this during `/verify` when a visual artifact is in scope. Section 1 of the verification report (Concrete observations) is built from this protocol.

## Three structural dimensions

### 1. Legibility

Can the text actually be read? Look beyond presence and evaluate usability.

- Overlapping labels or text running across other elements?
- Text crushed, clipped, or truncated awkwardly?
- Contrast failures between text and background?
- Text rendered at a size that's impossible at the displayed zoom?

### 2. Layout and rendering

Does the artifact render as designed, with elements where they belong?

- Bounding boxes respected, or do elements break out?
- Z-order correct (foreground stays in front, background stays behind)?
- Spacing consistent, or are there orphan whitespace gaps and crashed margins?
- Borders, dividers, and chrome rendering as intended?

### 3. Visual hierarchy

Does emphasis match importance?

- Are primary elements visually dominant?
- Are secondary elements clearly subordinate?
- Are decorative or chrome elements (hints, hover states, debug overlays) recessive?
- If area or position is semantically meaningful (e.g. treemap area = quantity), does the geometry actually encode it, or is the encoding crashed by labels?

## Execution

When applying this protocol, do not state what is present ("there are boxes on a screen"). Critically evaluate against the three dimensions above. Cite specific regions or coordinates. Plain language is preferred over jargon — "the '96 tasks' label is rendered in ~48pt white over the child cells" beats "the aggregate count overlay competes for visual dominance."

If a defect would obscure the artifact's primary semantic encoding (treemap geometry, chart axis, table grid), flag it as a structural failure, not a polish concern.

## Out of scope here

These belong in `/design-rubric`, on the spec's Fitness Rubric, not in this protocol:

- "Does this overwhelm the user?"
- "Does this serve a tired ADHD academic?"
- "Does this land softly or sharply?"
- Cognitive-load assessment generally.
- Emotional-response assessment generally.

Those are design-time questions about whether the _concept_ serves the user. This protocol asks whether the _rendering_ of that concept actually works at the pixel level. Both matter; they belong in different skills.

---
name: prompt-authoring
parent_skill: deep-research
---

# Authoring a deep-research prompt

Deep-research tools (Gemini Deep Research, ChatGPT Pro Deep Research, Perplexity Deep
Research) return long synthesis documents with citations. They repay being asked to
_compare and synthesise_ bodies of practice, and return an encyclopaedia entry when asked
to "explain" or "summarise".

## Shape the prompt around what the output is for

Ask what the reader will _do_ with the result and build backwards. Two shapes recur:

- **Synthesis** — "weigh these approaches and tell me how to design or decide X." The output
  is an argued position or a spec.
- **Enumeration** — "find everything matching these criteria and tabulate it." The output is
  a structured inventory.

A request that mixes them does the enumeration first and synthesises over its results. The
two anatomies below are worked shapes, not a taxonomy to slot a request into.

## Synthesis anatomy

1. **Problem framing** (2–3 sentences). What you are designing and what property it needs,
   grounded in a concrete artefact so the tool knows what "useful" looks like.
2. **A numbered comparison of 4–6 named bodies of practice** — specific traditions,
   frameworks, or schools. Left unnamed, the tool invents a shallow survey.
3. **A structured extract per body of practice**: protocol, failure modes,
   calibration/consistency checks, validation over time. Uniform structure makes the output
   scannable.
4. **Recommendations section** naming the user, the constraints, and the decision this
   feeds — friction budgets ("30 seconds per edge"), whether outputs are hard gates or soft
   signals, and what existing signals they must integrate with. Name the **deliverables**
   (a spec, three guides, a ranking) without dictating their internal format.
5. **Evidence discipline as required sections, never a trailing clause.** A one-line "cite
   sources" instruction gets ignored. Require a **`Works Cited`** section plus inline
   citation anchors on every named claim; a **`Weakest links`** section naming the 3–5
   thinnest points or extrapolations; and, for any cross-domain transfer, an explicit
   instruction to separate what the sources establish from the proposed transfer, marking
   inferences as inferences.

Search the PKB for tasks tagged `deep-research` or typed `spike` and read a few recent
prompts before drafting, to calibrate the level of detail.

## Enumeration anatomy

An inventory lives or dies on its membership predicate and its verifiability. Cover:

1. **Search scope** — where to look, how hard, and the exhaustiveness bar.
2. **Inclusion predicate** — the positive test for what qualifies.
3. **Exclusion predicate** — the negative boundary, stated explicitly. This is what a terse
   request most often leaves implicit, and what keeps the catalogue precise.
4. **A testable threshold** — the fuzzy ask restated as something checkable per candidate
   ("must do X for at least two of {A, B, C}"), so borderline cases resolve consistently.
5. **Per-item schema** — the exact fields each row carries, including source link,
   provenance, and recency.
6. **Ordering or ranking** — with the rubric defined, or an instruction to state its own.

Then require: a **working source link the tool actually consulted** on every row, because an
inventory nobody can click is indistinguishable from an invented one; an **anti-padding**
instruction ("if the search yields only N genuine matches, return N — do not pad with
plausible-but-unverified entries"); and every performance number **cited or labelled as the
subject's own claim**.

## Turning a terse request into a prompt

Close the ambiguity before handing it over, in proportion to how much would otherwise
resolve wrongly — a genuinely simple lookup stays short:

- Turn fuzzy scope into a checkable predicate — "relevant plugins" → "does X via the hooks
  system for ≥2 of {…}".
- State the exclusions the user left implicit.
- Name the deliverable's fields or sections.
- Define any rating axis, or the tool invents an undocumented scale.

## High-leverage additions

- **Ask for 2–3 concrete exemplar artefacts** on any design, architecture, or spec question.
  They ground the abstraction and are the most directly reusable part of the output.
- **Force conflict adjudication** — "where two traditions give conflicting advice, say so and
  adjudicate", or the tool harmonises tensions it should surface.
- **Weight toward the deliverable** — "keep the theory synthesis tight; weight the output
  toward the implementable spec", or the front half becomes a literature review.
- **Ask for a reasoned position, not a menu** — "reach a reasoned position (not just options)
  on X".

## Anti-patterns

- "Tell me about X", and unbounded scope ("survey all prioritisation research").
- No user context, so recommendations cannot be tailored.
- No named deliverables — say what artefacts you want back.
- Over-specified output shape: a rigid section-by-section template suppresses synthesis.
  Prescribe format only where the downstream consumer needs it.
- Evidence discipline as a closing sentence rather than required sections.
- An inventory without a real link per row, without an exclusion predicate, or without a
  padding guard.
- A rating column with no rubric.

## Format for the task

Deep-research prompts live in the body of the sourcing spike task:

````markdown
# Spike: <one-line goal>

**Type**: spike (affordable-loss probe)
**Effort**: 0.5d
**Tool**: Gemini Deep Research

## Problem

<2-3 sentences of framing>

## Deep Research prompt

```
<the prompt, ready to paste>
```

## Acceptance criteria

- [ ] Run the prompt in <tool>
- [ ] Verify the output carries citations and a `Weakest links` section before capture — if
      not, re-run rather than capturing an unsourced doc
- [ ] Capture output via `/deep-research` (produces a note at `knowledge/<topic>/<slug>.md`)
- [ ] Note includes <key artefacts the output should contain>
- [ ] Flag any thin-consensus recommendations
````

## Iteration

A run costs about ten minutes and no tokens, so refine and re-run a shallow first output:
add a tradition the tool missed, sharpen the user-context section with numbers and
constraints, add "distinguish between X and Y" where it conflated two concepts. Missing
citations or thin-consensus flags almost always mean they were not forced — promote them to
required sections and re-run.

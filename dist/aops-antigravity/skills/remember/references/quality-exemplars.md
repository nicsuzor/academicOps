---
title: Quality Exemplars for Knowledge Consolidation
type: reference
category: instruction
description: Real examples of good and bad consolidation output, derived from dogfooding brain PRs #6 and #7.
tags: [consolidation, quality, exemplars]
---

# Quality Exemplars for Knowledge Consolidation

These exemplars are drawn from actual QA review of consolidation output (brain PRs #6 and #7, April 2026). They encode what we learned about quality by doing the review — not from theory.

## What Makes a Good Knowledge Note

The five reliable quality signals, in order of importance:

1. **Source traceability** — memory IDs, dates, PR numbers, or session references for every claim
2. **User voice** — first person, grounded in specific experience. Not agent summaries or generic advice.
3. **Thematic coherence** — one clear topic per note. Stray sections bolted on = quality drop.
4. **Concrete details** — numbers, names, specific incidents. Not vague principles.
5. **Right abstraction** — not implementation minutiae (file paths, env vars), not platitudes. The test: would this help someone working on a DIFFERENT component?

## Exemplar 1: Strong Synthesis (from PR #6)

`agent-interaction-contracts.md` consolidated 5 separate memories about agent behavior rules into a single thesis: **epistemic honesty is the underlying contract**. What made it excellent:

- **Unifying thesis in the opening** — "These aren't preferences or style choices — they're structural requirements" reframes individual rules as instances of one principle
- **User voice throughout** — "I'm a law professor; I understand the difference between a delegate who exercises judgment transparently and one who acts ultra vires"
- **All 5 sources fully covered** — every original memory traceable in the consolidated note, no information lost
- **Right abstraction** — elevates "don't substitute intent" and "respect stop signals" to the shared principle (epistemic honesty) without losing the specific behaviors

### Anti-pattern: Concatenation disguised as synthesis

A weaker consolidation of the same 5 memories would just list the rules:

- Don't substitute intent
- Respect stop signals
- Don't speculate when blocked
- Don't ask "ready?"
- Flag knowledge gaps

This adds no value over the original memories. Synthesis means finding the connection the originals don't state.

## Exemplar 2: Strong Technical Reference (from PR #7)

`gate-system-engineering-lessons.md` captured hard-won operational knowledge. What made it excellent:

- **Grounded in specific debugging** — the chicken-and-egg problem section gives three concrete examples of gates blocking their own satisfaction
- **Named lessons** — "the warn mode trap" is a memorable, reusable concept
- **PR references** — PR #844 for the subagent fix, providing provenance
- **No editorializing** — reports what happened and what was learned, doesn't lecture about what agents should do differently

### Anti-pattern: Vague lessons without grounding

A weaker version: "Gates can create circular dependencies. Care should be taken when designing gate systems to avoid blocking their own satisfaction." This is true but useless — it doesn't tell you WHICH gates, HOW they blocked, or WHAT the fix was.

## Exemplar 3: Quality Issues to Watch For

**Stray sections**: `sessionstart-vs-jit-context-loading.md` had a section about iTerm2 terminal titles bolted onto the end. It didn't relate to context loading. One topic per note.

**Overlap/duplication**: Two polecat notes (`distributed-agent-operations.md` and `operational-lessons.md`) covered overlapping content with different organization. The /sleep cycle should dedup these — merge into the stronger note, delete the weaker.

**Over-abstraction**: `session-state-persistence.md` consolidated only 2 memories and read more like a restated problem than distilled knowledge. The sweet spot is 4-6 source memories. Below 3, there often isn't enough material for genuine synthesis.

**Implementation details that age**: `ensemble-evaluation-framework.md` included specific tool names (BigQuery, Weights & Biases, /conf directory) that will go stale. Prefer the principle over the current tooling unless the tooling IS the point.

**Sensitivity without marking**: Some notes contained sensitive institutional details (board deliberations, financial reserves). In a trusted environment this is fine, but notes with sensitive content should be recognizable — consider a `sensitivity: high` frontmatter field or a callout.

## The Quality Test

When reviewing a consolidation note, ask:

1. Can I trace every claim to a source? (If not → missing provenance)
2. Does it sound like the user, or like an agent writing a report? (Agent-speak → rewrite)
3. Is there ONE clear topic, or did sections get bolted on? (Stray sections → trim)
4. Would this help someone who wasn't there? (If not → wrong abstraction level)
5. Does the synthesis add something the original memories don't say individually? (If not → not worth consolidating)

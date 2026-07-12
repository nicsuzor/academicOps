---
id: session-effectiveness
kind: process
category: meta
description: Qualitative assessment of a session transcript to evaluate framework performance — what worked, what wasted context, what to consolidate
requires: []
pairs-with: [dogfooding]
conflicts: []
version: 1.0.0
permalink: workflows-process-session-effectiveness
---

# Process: Session Effectiveness Audit

**When to use**: after a major session, to assess what worked, what failed,
what context was wasteful, and what patterns could be consolidated.

## Steps

1. **Load transcript** — full transcript for token-waste analysis; abridged
   for workflow review.
2. **Qualitative assessment** — spawn an evaluator with the standard
   evaluation prompt across six dimensions: framework effectiveness, context
   injection utility, process efficiency, consolidation opportunities, token
   waste, and what worked well.
3. **Chunking** — if the transcript exceeds the context window, split at turn
   boundaries and evaluate each chunk separately.
4. **Synthesize** — combine findings, remove duplicates, prioritize.
5. **Present** — the structured effectiveness report, for human review.

## Success Criteria

Substantive findings for each of the six dimensions; every finding cites a
specific turn/quote/example; recommendations are prioritized and actionable;
handles transcripts of varying scale; token-waste analysis always uses the
full transcript, never the abridged one.

## Notes

No mechanical metrics — use semantic judgment. Every finding needs evidence,
not just assertion.

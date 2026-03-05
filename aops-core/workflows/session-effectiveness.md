---
name: session-effectiveness
category: instruction
description: Qualitative LLM assessment of session transcripts to evaluate framework performance.
---

# Session Effectiveness Audit

Qualitative LLM assessment of session transcripts to evaluate framework performance.

**When to Use**: After completing a major session to assess what worked well, what failed, what context was wasteful, and what patterns could be consolidated.

**Detailed procedures and prompts**: See **[[audit-details]]**.

## Invocation

```
Skill(skill="audit", args="session-effectiveness /path/to/transcript.md")
```

## Workflow Steps

1. **Load Transcript**: Use the full transcript for token waste analysis and abridged for workflow review.
2. **Qualitative Assessment**: Spawn an evaluator agent with the transcript and the standard `EVALUATION_PROMPT`. Assess framework effectiveness, context injection utility, process efficiency, consolidation opportunities, token waste, and what worked well.
3. **Chunking Strategy**: If the transcript exceeds the context window, split at `## User (Turn N)` boundaries and evaluate each chunk separately.
4. **Final Synthesis**: Combine findings, remove duplicates, and prioritize recommendations.
5. **Present Report**: Output the structured `Session Effectiveness Report` for human review.

## Success Criteria

1. **Qualitative findings**: Substantive assessments for each of the 6 dimensions.
2. **Evidence-backed**: Each finding cites specific turns, quotes, or examples.
3. **Actionable**: Prioritized recommendations the user can act on.
4. **Handles scale**: Works on transcripts of varying sizes.
5. **Full transcript for waste**: Token waste analysis uses full transcript.

## Notes

- **No mechanical metrics**: Use semantic understanding for qualitative judgments.
- **Evidence required**: Every finding must cite specific transcript content.

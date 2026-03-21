# Session Effectiveness Audit Detailed Procedures

Detailed evaluation prompts, output formats, and chunking strategies for auditing session effectiveness.

## EVALUATION_PROMPT

You are evaluating a session transcript for framework effectiveness. Read the transcript and assess it against these 6 dimensions. For EACH finding, cite specific evidence (turn numbers, quotes).

### 1. Framework Effectiveness

- Did hooks/skills fire at appropriate times?
- Were violations caught or missed?
- Did the framework guide the agent toward good outcomes?

### 2. Context Injection Utility

- Which injected context was actually referenced/used?
- Which injected context appears wasteful (injected but never used)?
- What information was clearly needed but NOT injected (JIT gaps)?

### 3. Process Efficiency

- Where did the agent repeat work unnecessarily?
- Where did verbose context bloat the conversation?
- Where did the agent struggle due to unclear instructions?

### 4. Consolidation Opportunities

- What manual patterns appear repeatedly that could become a script?
- What ad-hoc workflows could become a skill?
- What instructions are scattered that should be consolidated?

### 5. Token Waste Analysis (Full Transcript Required)

- Where does content appear more than once (subagent outputs, retried prompts, duplicated context)?
- What connection errors or retries consumed tokens?
- Which injected content was never referenced?
- What verbose explanations could be condensed?

### 6. What Worked Well

- Which framework components demonstrably helped?
- Where did JIT context arrive at exactly the right time?
- Which skills/workflows were invoked correctly and effectively?

## Output Format: Session Effectiveness Report

```markdown
## Session Effectiveness Report

### Executive Summary

[3-5 sentences on overall framework performance]

### 1. Framework Effectiveness

[Findings with evidence citations]

### 2. Context Injection Utility

**Used effectively**: [list with evidence]
**Wasteful**: [list with evidence]
**Missing (JIT gaps)**: [list with evidence]

### 3. Process Efficiency

[Findings with evidence citations]

### 4. Consolidation Opportunities

[Prioritized list with evidence]

### 5. Token Waste Analysis

**Duplicated content**: [list with locations]
**Connection/retry waste**: [count and locations]
**Unused injected context**: [list with evidence]

### 6. What Worked Well

[List with evidence]

### Prioritized Recommendations

1. [Highest impact recommendation]
2. [...]
```

## Chunking Strategy (if needed)

If the transcript exceeds the context window:

1. Split at `## User (Turn N)` boundaries.
2. Each chunk includes: session metadata header + N turns + evaluation prompt.
3. Evaluate each chunk separately.
4. Final synthesis pass combines chunk findings, removes duplicates, and prioritizes recommendations.

---
name: session-effectiveness
category: instruction
description: Qualitative LLM assessment of session transcripts to evaluate framework performance.
---

# Session Effectiveness Audit

Qualitative LLM assessment of session transcripts to evaluate framework performance.

## When to Use

After completing a major session, to assess:

- What worked well
- What failed or caused friction
- What context was useful vs wasteful
- What patterns could be consolidated

## Invocation

```
Skill(skill="audit", args="session-effectiveness /path/to/transcript.md")
```

## Workflow

### Step 1: Load Transcript

**CRITICAL: Use full transcript for token waste analysis.**

The abridged transcript hides critical duplication patterns:

| Hidden in Abridged          | Visible in Full                                                                                                    |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Subagent output duplication | Each subagent's output appears twice: once summarized in main flow, once in full in "Subagent Transcripts" section |
| Connection error tokens     | API retry messages scattered throughout                                                                            |
| Context injection verbosity | Full skill/hook content injections                                                                                 |
| JIT context gaps            | Subagent sections show what context they lacked                                                                    |

**Transcript selection:**

- For **token waste analysis**: Always use full transcript (chunk if needed)
- For **workflow review**: Abridged is sufficient
- If >100K tokens: chunk by `## User (Turn N)` boundaries

### Step 2: Qualitative Assessment

Spawn an evaluator agent with the transcript and evaluation criteria:

```
Task(subagent_type="general-purpose", model="sonnet",
     description="Session effectiveness evaluation",
     prompt="[EVALUATION_PROMPT below with transcript content]")
```

#### EVALUATION_PROMPT

You are evaluating a Claude Code session transcript for framework effectiveness. Read the transcript and assess it against these 5 dimensions. For EACH finding, cite specific evidence (turn numbers, quotes).

**1. Framework Effectiveness**

- Did hooks/skills fire at appropriate times?
- Were violations caught or missed?
- Did the framework guide the agent toward good outcomes?

**2. Context Injection Utility**

- Which injected context was actually referenced/used?
- Which injected context appears wasteful (injected but never used)?
- What information was clearly needed but NOT injected (JIT gaps)?

**3. Process Efficiency**

- Where did the agent repeat work unnecessarily?
- Where did verbose context bloat the conversation?
- Where did the agent struggle due to unclear instructions?

**4. Consolidation Opportunities**

- What manual patterns appear repeatedly that could become a script?
- What ad-hoc workflows could become a skill?
- What instructions are scattered that should be consolidated?

**5. Token Waste Analysis** (requires full transcript)

- Where does content appear more than once? (subagent outputs, retried prompts, duplicated context)
- What connection errors or retries consumed tokens?
- Which injected content was never referenced?
- What verbose explanations could be condensed?

**6. What Worked Well**

- Which framework components demonstrably helped?
- Where did JIT context arrive at exactly the right time?
- Which skills/workflows were invoked correctly and effectively?

**Output Format**:

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

### Step 3: Chunking Strategy (if needed)

If transcript exceeds context window:

1. Split at `## User (Turn N)` boundaries
2. Each chunk includes: session metadata header + N turns + evaluation prompt
3. Evaluate each chunk separately
4. Final synthesis pass combines chunk findings, removes duplicates, prioritizes

### Step 4: Present Report

Output the structured report for human review. The user decides which recommendations to act on.

## Success Criteria

1. **Qualitative findings**: Substantive assessments for each of the 6 dimensions
2. **Evidence-backed**: Each finding cites specific turns, quotes, or examples
3. **Actionable**: Prioritized recommendations the user can act on
4. **Handles scale**: Works on transcripts of varying sizes
5. **Full transcript for waste**: Token waste analysis uses full transcript (not abridged)

## Notes

- **No mechanical metrics**: Do NOT use tokenizers, word counts, keyword matching, or pattern detection
- **Semantic understanding**: The evaluating LLM makes qualitative judgments based on reading comprehension
- **Evidence required**: Every finding must cite specific transcript content

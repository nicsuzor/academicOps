---
title: Session Effectiveness Audit Workflow
type: spec
category: experiment
permalink: experiments/session-effectiveness-audit
description: Experiment plan for session transcript analysis workflow
tags: [experiment, audit, transcript, effectiveness]
---

# User Story: Session Effectiveness Audit Workflow

**Date**: 2026-01-11
**Status**: Plan Revised (Qualitative Assessment)

## Original Request

> Create a new and separate workflow file within the audit skill, specifically aimed at assessing a whole major session transcript to identify how well the framework is working. I want to see a report not just on faults, but efficiency: what worked, what didn't, what stuff was injected that appears to be useless, what information should ideally have been injected but was not JIT, where do we see repetitive or wasteful token use, what could we replace with a script or a skill, etc.

## Revised Approach: Qualitative LLM Assessment

**Key principle**: Use a capable LLM to read and assess the transcript holistically against criteria. NO tokenizers, word counts, keyword matching, or mechanical pattern detection. The LLM uses semantic understanding to make qualitative judgments.

## Feature Summary

A session effectiveness audit workflow where a capable LLM reads the full session transcript (or chunked sections if too large) and produces a qualitative assessment report covering: what worked well, what failed, what context was useful vs wasteful, what patterns could be consolidated.

## Implementation Approach

### Core Design

1. **LLM-as-evaluator**: A capable model (Opus or Sonnet) reads the transcript and assesses it against evaluation criteria
2. **Chunking strategy**: If transcript exceeds context window, chunk by turn boundaries and synthesize across chunks
3. **Structured prompting**: Provide clear evaluation criteria and output structure to the evaluating LLM
4. **Evidence requirements**: LLM must cite specific examples (turn numbers, quotes) for each finding

### Evaluation Criteria (What the LLM assesses)

The evaluating LLM reads the transcript and makes qualitative judgments on:

**1. Framework Effectiveness**

- Did hooks/skills fire at appropriate times?
- Were violations caught or missed?
- Did the framework guide the agent toward good outcomes?

**2. Context Injection Utility**

- Which injected context was actually referenced/used by the agent?
- Which injected context appears to have been ignored or wasteful?
- What information was clearly needed but NOT injected (JIT gaps)?

**3. Process Efficiency**

- Where did the agent repeat work unnecessarily?
- Where did verbose context bloat the conversation?
- Where did the agent struggle due to unclear instructions?

**4. Consolidation Opportunities**

- What manual patterns appear repeatedly that could become a script?
- What ad-hoc workflows could become a skill?
- What instructions are scattered that should be consolidated?

**5. What Worked Well**

- Which framework components demonstrably helped?
- Where did JIT context arrive at exactly the right time?
- Which skills/workflows were invoked correctly and effectively?

### Technical Constraints to Solve

**Context window limits**:

- Full transcript (130da570) is ~245KB / ~60K tokens
- May exceed single-pass context window
- **Solution options**:
  a. Chunk by user turns, evaluate each chunk, synthesize findings
  b. Use abridged transcript (~39KB) for overview, deep-dive specific sections
  c. Use model with larger context (if available)

**Chunking strategy** (if needed):

- Split at `## User (Turn N)` boundaries
- Each chunk includes: session metadata + N turns + evaluation prompt
- Final synthesis pass combines chunk findings

### Workflow File Structure

Location: `/home/nic/src/academicOps/skills/audit/workflows/session-effectiveness.md`

```markdown
# Session Effectiveness Audit

## When to Use

After completing a major session, to assess framework performance.

## Invocation

Skill(skill="audit", args="session-effectiveness /path/to/transcript.md")

## Workflow

### Step 1: Load Transcript

Read the full transcript file. If >100K tokens, use abridged version or chunk.

### Step 2: Qualitative Assessment

Spawn an evaluator agent (Opus/Sonnet) with:

- The transcript (or chunk)
- Evaluation criteria (5 dimensions above)
- Output structure requirements

### Step 3: Synthesize Report

Combine findings into structured report with:

- Executive summary (3-5 sentences)
- Findings by dimension (with evidence citations)
- Prioritized recommendations

### Step 4: Present to User

Output report for human review and action decisions.
```

## Success Criteria

1. **Qualitative findings**: LLM produces substantive assessments for each of the 5 dimensions
2. **Evidence-backed**: Each finding cites specific turns, quotes, or examples from transcript
3. **Actionable recommendations**: Report includes prioritized suggestions the user can act on
4. **Handles scale**: Works on transcripts of varying sizes (chunking if needed)

**Acceptance**:

- [ ] Run on sample transcript (130da570 audit epic)
- [ ] Report covers all 5 evaluation dimensions
- [ ] Each finding includes evidence from transcript
- [ ] User confirms findings are insightful (qualitative validation)

## Implementation Notes

**Location**: `/home/nic/src/academicOps/skills/audit/workflows/session-effectiveness.md`

**No Python script needed**: This is LLM-driven assessment, not mechanical processing. The workflow file contains instructions for the evaluating agent.

**Integration**: Add workflow reference to main audit SKILL.md

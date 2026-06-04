---
name: verify
type: skill
category: instruction
description: Judgement-based QA pass. Does this artifact meet its goal and serve its user? Demands excellence, not compliance. Owned by marsha; reads the spec's Fitness Rubric (designed upstream via /design-rubric).
triggers:
  - "verify"
  - "QA check"
  - "acceptance test"
  - "quality check"
  - "is it done"
  - "validate work"
modifies_files: true
needs_task: true
mode: execution
domain:
  - quality-assurance
allowed-tools: Task,Read,Glob,Grep
version: 2.0.0
permalink: skills-verify
---

# Judgement-Based Verification Guidelines

Conduct rigorous QA reviews of artifacts to ensure correctness, complete implementation, and fitness for purpose.

## Core Directives

1. **Verify Evidence**: Read files, run code, and inspect actual outputs directly. Do not rely on agent summaries. Cite exact file paths, line numbers, or logs.
2. **Classify the Bar**:
   - **Mechanical Bar**: Verify against Acceptance Criteria (AC). Verdict: `PASS`, `FAIL`, or `REVISE`.
   - **Fitness / Mixed Bar**: Verify against the AC and the spec's `## Fitness Rubric`. (If missing on a fitness task, return `REVISE — fitness rubric missing`).
3. **Completeness check**: Apply the completeness heuristic before signing off:
   - Check freshness of inputs read.
   - Verify changes are complete across all callsites.
   - Acknowledge known limitations or constraints.
4. **Forcing Checks**: Write explicit answers for each in the report before a PASS verdict:
   - **Sentinel / Empty-State Audit**: Count and list empty/sentinel fields (e.g. `DERIVER_MISSING`, `N/A`, `TODO`). Fail if primary value-signals are missing.
   - **Principal's-Eye Top-Line Read**: State verbatim the most prominent headline element and verify correctness for the end-user.
   - **Floor vs Ceiling**: State verbatim: "exceptional, or merely working?". Merely working is not a PASS on fitness tasks.
5. **No Anchoring/Bias**:
   - If you participated in designing or iterating on this artifact, you are disqualified from reviewing it for fitness.
   - Dispatches must be neutral (do not pre-state expected verdicts).

## HALT Triggers (Immediate FAIL)

Stop evaluation immediately and write a FAIL verdict if any of the following occur:

- Primary fields rendering as sentinels/placeholders.
- Headline element is wrong for the end user.
- Repeated or empty section headers.
- Placeholder text (`{variable}`, `TODO`, `FIXME`) in production.
- Overlapping/clipped text in rendered visual output.
- Suspiciously short output for complex operations.
- Silent error swallowing (`try/except` without logging).
- Test suite checking existence instead of content.

## Verdict Format

Output reports exactly in this format:

```markdown
## Verification Report

**Bar:** [mechanical / fitness / mixed]
**Verdict:** [PASS / FAIL / REVISE]

### Concrete observations

[Observed bugs/defects, file paths, line numbers, and log excerpts]

### Forcing checks

1. **Sentinel/empty-state audit:** [count + list of sentinels/placeholders. If primary signals absent -> FAIL]
2. **Principal's-eye top-line read:** [headline element quoted, and whether correct]
3. **Floor vs ceiling:** [verbatim "exceptional, or merely working?"]

### Judgement

[Prose evaluation against AC, Red Flags, and/or Fitness Rubric dimensions]

### Recommendation

[If FAIL/REVISE: specific remediation steps and user impact]
```

## Browser-Driven UI Verification

For web applications:

1. Navigate to the URL and wait for page-ready.
2. Capture screenshots at 1920×1080 resolution.
3. Save screenshots to `$AOPS_SESSIONS/qa-screenshots/YYYY-MM-DD/`.
4. Apply visual analysis checks for layout and legibility defects.

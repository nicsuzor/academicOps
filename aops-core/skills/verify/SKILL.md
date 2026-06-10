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

## Step 0 — Premise Test (forced; runs BEFORE you read the diff)

Before you read a single line of the diff, judge the **premise** from the task + diffstat alone. The first move is the sharp principal's snap reaction — _"was this a good idea?"_ — written verbatim:

> **Premise Test:** Seeing only the task and the diffstat (NOT the code): is this worth doing, and is the shape right — or would a sharp principal bounce it?

This is one free-text sentence of judgement, **never a form or checklist** — a checklist would itself be the deterministic-rig failure this guards against. You **cannot emit a `PASS` verdict without first writing this sentence.** Reading the code first is exactly what lets a clean, well-tested surface launder a bad premise, so premise-first / diffstat-first ordering is mandatory.

**A bad premise = `FAIL`, regardless of test coverage.** If a sharp principal would bounce the premise, the verdict is `FAIL` even with green tests, clean code, and satisfied AC. Test-passing is the **expected surface** of a bad-premise artifact, not a mitigant — "but it's tested / it works / it's clean" is precisely the rationalisation this gate closes. _Deterministic-rig-for-a-judgment-call_ (a regex/threshold/NLP/checklist standing in for a call a smart agent should just make — see `judgment-non-delegable`, `exercise-authority` Edge 3) is ONE named instance of a bad premise; the test generalises to "was this worth building at all, in this shape?"

## Core Directives

Default posture: **assume it's broken.** The burden is on the artifact to prove it works — not on you to prove it doesn't.

1. **Verify Evidence**: Read files, run code, and inspect actual outputs directly. Do not rely on agent summaries. Cite exact file paths, line numbers, or logs.
2. **Classify the Bar**:
   - **Mechanical Bar**: Verify against Acceptance Criteria (AC). Verdict: `PASS`, `FAIL`, or `REVISE`.
   - **Fitness / Mixed Bar**: Verify against the AC and the spec's `## Fitness Rubric`. (If missing on a fitness task, return `REVISE — fitness rubric missing`).
3. **Completeness check**: Apply the completeness heuristic before signing off:
   - Check freshness of inputs read.
   - Verify changes are complete across all callsites.
   - Acknowledge known limitations or constraints.
4. **Forcing Checks**: Write explicit answers for each in the report before a PASS verdict:
   - **Premise Test (step 0, before reading the diff)**: State verbatim the sharp-principal reaction from task + diffstat alone (see Step 0). A bad premise is a `FAIL` regardless of test coverage; you cannot reach `PASS` without writing it.
   - **Sentinel / Empty-State Audit**: Count and list empty/sentinel fields (e.g. `DERIVER_MISSING`, `N/A`, `TODO`). Fail if primary value-signals are missing.
   - **Principal's-Eye Top-Line Read**: State verbatim the most prominent headline element and verify correctness for the end-user.
   - **Floor vs Ceiling**: State verbatim: "exceptional, or merely working?". Merely working is not a PASS on fitness tasks.
5. **No Anchoring/Bias**:
   - If you participated in designing or iterating on this artifact, you are disqualified from reviewing it for fitness.
   - Dispatches must be neutral (do not pre-state expected verdicts).

## Data Pipeline Verification

For any artifact with computed, aggregated, or derived output (dashboards, reports, metrics), trace source → output: confirm the source is real, populated, and fresh; independently cross-verify the values against that source; disable any fallback to prove the primary path works alone (a fallback silently masks a broken primary); and check behaviour under load. The question is not "did output appear?" but "is this the RIGHT data?" — plausible-looking output is the most dangerous kind of incorrect output.

## HALT Triggers (Immediate FAIL)

Stop evaluation immediately and write a FAIL verdict if any of the following occur:

- **Bad premise** — a sharp principal would not have built this, or not in this shape (the canonical instance: a deterministic rig — regex/threshold/NLP/checklist — standing in for a judgment call). `FAIL` regardless of green tests; test-passing is the expected surface of this failure, not a mitigant.
- Primary fields rendering as sentinels/placeholders.
- Headline element is wrong for the end user.
- Repeated or empty section headers.
- Placeholder text (`{variable}`, `TODO`, `FIXME`) in production.
- Overlapping/clipped text in rendered visual output.
- Suspiciously short output for complex operations.
- Silent error swallowing (`try/except` without logging).
- Test suite checking existence instead of content.
- Data that looks plausible but does not match its source.

## Verdict Format

Output reports exactly in this format:

```markdown
## Verification Report

**Bar:** [mechanical / fitness / mixed]
**Verdict:** [PASS / FAIL / REVISE]

### Concrete observations

[Observed bugs/defects, file paths, line numbers, and log excerpts]

### Forcing checks

0. **Premise test (before reading the diff):** [verbatim sharp-principal reaction from task + diffstat alone — "was this a good idea, in this shape?" A bad premise -> FAIL regardless of tests; cannot reach PASS without this line]
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

---
name: verify
description: Judgement-based QA pass verifying artifacts against acceptance criteria and fitness rubrics. Assumes artifacts are broken until runtime verification proves excellence.
---

# Verify

Rigorous quality review evaluating correctness, completion, and fitness for purpose. Default posture: assume the artifact is broken until proven working. Bound to `marsha`.

## 1. Classify the Bar

- **Mechanical**: Verify strictly against acceptance criteria.
- **Fitness / Mixed**: Verify against acceptance criteria and the spec's fitness rubric. If the rubric is missing on a fitness task, return `REVISE -- fitness rubric missing`.

## 2. Mandatory Forcing Checks

All four checks must be answered explicitly in the report before rendering a `PASS`:
0. **Premise test**: Is the underlying premise sound, or would a sharp principal reject it? (Bad premise = `FAIL`).

1. **Sentinel and placeholder audit**: Check for and report empty or placeholder values (`N/A`, `TODO`, etc.).
2. **Principal's-eye top-line read**: Quote the primary user-facing output verbatim and verify correctness for the actual end user.
3. **Floor versus ceiling**: Answer explicitly: "Exceptional, or merely working?" Merely working fails fitness tasks.

## 3. Immediate Fail Triggers

Render an immediate `FAIL` on:

- Bad premise or invalidated requirements.
- Sentinel values or placeholder text in production outputs.
- Silent exception swallowing without error logging.
- Tests that assert existence or tautologies rather than functional behavior.
- Data that diverges from primary source records.
- Edits made directly to runtime install directories instead of source repos.

## 4. Visual Verification

Evaluate live rendered screenshots (1920x1080) across three dimensions:

- **Legibility**: Overlapping text, poor contrast, or unreadable sizing.
- **Layout**: Clipped elements, collapsed margins, and unintended whitespace.
- **Hierarchy**: Geometry and visual weight matched to semantic importance.

## 5. Verification Report Schema

```markdown
## Verification Report

**Bar**: [mechanical | fitness | mixed]
**Verdict**: [PASS | FAIL | REVISE]

### Concrete Observations

[Observed findings with basis tags ([observed], [attempted-and-failed], etc.) and file:line citations]

### Forcing Checks

0. **Premise test**: [One sentence assessment]
1. **Sentinel audit**: [Counts and occurrences]
2. **Principal's-eye read**: [Verbatim headline and validation]
3. **Floor vs ceiling**: ["Exceptional, or merely working?" answered]

### Recommendation

[Specific remediations and affected criteria for FAIL/REVISE verdicts]
```

Record the verdict and evidence on the associated task record upon completion.

---
name: verify
description: Judgement-based QA pass. Does this artifact meet its goal and serve its user? Demands excellence, not compliance.
agent: "aops:marsha"
---

# Verify

A rigorous QA review: correctness, complete implementation, fitness for purpose. Default posture — **assume it is broken**. The burden is on the artifact to prove it works.

Bound to marsha. Run under another disposition and the bar silently softens.

## 1. Classify the bar

- **Mechanical** — verify against the acceptance criteria.
- **Fitness or mixed** — verify against the acceptance criteria _and_ the spec's fitness rubric. If a fitness task has no rubric, return `REVISE — fitness rubric missing`.

For a content or instruction artifact — a skill, agent body, prompt, doc, spec — the governing standard usually lives in a skill rather than in a rules file. Identify the skill that owns quality for that artifact type and verify against it.

## 2. Forcing checks

Write an explicit answer to each in the report. A `PASS` verdict is unavailable until all four are written.

0. **Premise test, before you read the diff.** From the task and diffstat alone, write the sharp principal's one-sentence reaction: _was this a good idea, in this shape?_ One open sentence, never a checklist. A bad premise is a `FAIL` regardless of test coverage — green tests are the expected surface of a bad premise, not a mitigant. Full discipline: the `strategic-review` skill, §2.
1. **Sentinel and empty-state audit.** Count and list every empty or placeholder field (`N/A`, `TODO`, `DERIVER_MISSING`). Missing primary value-signals are a `FAIL`.
2. **Principal's-eye top-line read.** Quote the most prominent headline element verbatim and say whether it is correct for the end user. On a "show me my X" surface this means reproducing the principal's own view — their account, host, launch context — and confirming _their_ instance is present. A generic instance is a `FAIL`.
3. **Floor versus ceiling.** State verbatim: "exceptional, or merely working?" Merely working is not a `PASS` on a fitness task.

## 3. Halt triggers — immediate FAIL

Stop and write the verdict when you see any of:

- A bad premise (forcing check 0).
- Primary fields rendering as sentinels or placeholders.
- A headline element that is wrong for the end user.
- Repeated or empty section headers; placeholder text in production output.
- Overlapping or clipped text in rendered visual output.
- Suspiciously short output for a complex operation.
- Silent error swallowing — a caught exception with no log.
- A test suite checking existence instead of content.
- Data that looks plausible but does not match its source.

## 4. Visual artifacts

For any rendered output — a screenshot, dashboard, chart, slide — critically evaluate three structural dimensions and cite specific regions. Do not state what is present; judge whether it works.

- **Legibility** — overlapping or clipped text, contrast failures, sizes unreadable at the displayed zoom.
- **Layout** — elements breaking their bounding boxes, wrong z-order, crashed margins, orphan whitespace.
- **Hierarchy** — is emphasis matched to importance? Where position or area carries meaning, does the geometry actually encode it, or has a label crashed it?

A defect obscuring the artifact's primary semantic encoding is a structural failure, not a polish concern. Cognitive-load and emotional-response questions are design-time; they belong to the spec's fitness rubric, not here.

For a web surface: navigate, wait for page-ready, capture at 1920×1080, and drive the affected flow — not just the test suite.

## 5. Report

```markdown
## Verification Report

**Bar:** [mechanical / fitness / mixed]
**Verdict:** [PASS / FAIL / REVISE]

### Concrete observations

[Observed defects with file paths, line numbers, and verbatim log excerpts]

### Forcing checks

0. **Premise test:** [the sharp-principal sentence, written before the diff read]
1. **Sentinel and empty-state audit:** [count and list]
2. **Principal's-eye top-line read:** [headline quoted, and whether it is correct]
3. **Floor vs ceiling:** ["exceptional, or merely working?" — answered]

### Process compliance

[Local-rule violations, cited by rule; or the sources you read and found nothing in]

### Judgement

[Prose evaluation against the acceptance criteria and the fitness rubric]

### Recommendation

[On FAIL or REVISE: specific remediation and its user impact. For brief-sourced work,
address the critique to the brief — name which element was unmet or ambiguous, so
re-dispatch is a brief update rather than a new plan.]
```

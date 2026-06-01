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

# /verify — Judgement-based QA

## Posture

You are the QA reviewer. Three beats, in order:

1. **Baseline sanity.** Look for obvious brokenness first — overlapping text, clipped layouts, runtime errors, placeholder `{variables}`, empty sections between headers, garbage data, silent error swallowing. If the artifact is fundamentally broken at the surface, that is the verdict. Don't soften it into a polish concern.
2. **Evidence-based judgment.** Trace the data, run the thing, look at the output. Cite specific evidence — file paths, line numbers, screenshot regions, log excerpts. QA is qualitative narrative, not a checkbox rubric — judged from the user's perspective, anchored on spec language verbatim; mechanical checks are supporting sub-criteria, not replacements. Runtime QA dispatches require an evidence block before any verdict (exact URL, title, un-hallucinable DOM counts, screenshot at the stated viewport); QA without evidence-of-running ≈ fabrication. Ask "is this real, complete, and correct?"
3. **Demand excellence.** A feature that passes its tests but doesn't serve its users is not good. A feature with rough edges that genuinely helps _is_. The bar is the spec's Fitness Rubric — not "meets minimum."

Default assumption: **IT'S BROKEN.** Prove it works.

## The Fitness Rubric is upstream of you

User-facing artifacts carry a `## Fitness Rubric` section authored at design time by pauli via `/design-rubric`. That section defines what excellence looks like for _this_ artifact and _this_ user — persona, scenarios, dimensions, quality spectrum.

**You read it. You do not re-derive it.** Persona immersion at QA time is contamination — you don't have the original context, you have the artifact in front of you and the temptation to rationalise.

## Classify the bar before you start

First decision in any verification: is this a mechanical task, a fitness task, or mixed?

- **Mechanical bar** (lint fix, dependency bump, test repair, refactor with no UX surface) — evaluate against AC and Red Flags. Verdict is plain `PASS` / `FAIL` / `REVISE`. No rubric needed. Do not invent one.
- **Fitness bar** (UX, prose, design output, dashboard, anything judged on whether it serves a human in context) — read the spec's `## Fitness Rubric` and judge against it. If a fitness task arrives at you without a rubric, verdict is `REVISE — fitness rubric missing; escalate to pauli/design-rubric`. Do not improvise.
- **Mixed bar** (most non-trivial work) — both apply. Check AC + Red Flags mechanically, _and_ judge against the rubric. Verdict synthesises both. Expect the fitness judgement to take more attention than the mechanical check; if your verdict only addresses the mechanical side, it has silently collapsed.

To detect a fitness bar, look for any of these signals in the brief or AC: adjectives of experience ("intuitive", "calm", "readable", "beautiful", "useful"); persona emotional/cognitive state ("tired", "anxious", "overwhelmed"); intended consumer is a human in a cognitively-loaded context; two reasonable evaluators could disagree on PASS/FAIL with the same evidence; fitness-for-purpose language ("serves the user", "lifeline not data dump"). Any one is sufficient. If you see these and the rubric is missing, that is the verdict — don't paper over it.

## The QA loop

1. **Read AC + Fitness Rubric.** One pass to understand what this is supposed to do, for whom, and what excellent looks like.
2. **Step Zero — naive smoke check.** Before any structured walk, look at the artifact and ask: "what's wrong here? be specific." Preferably in a clean sub-context. This is the contamination detector — if your structured pass softens what the naive pass said was catastrophic, trust the naive pass.
3. **Look at the artifact.** Concrete observations first. For visual artifacts, see [Concrete-defects-first](#concrete-defects-first-visual-artifacts) below.
4. **Trace, where it matters.** For data-driven artifacts, follow the pipeline source-to-output (see [Data pipeline verification](#data-pipeline-verification)).
5. **Judge against the rubric.** Per dimension, write one paragraph citing evidence from step 3-4. Not "looks good" — _why_ it does or doesn't serve the dimension.
6. **Verdict.** PASS / FAIL / REVISE with prose reasoning.

## Three dimensions of judgement

These are operational, not philosophical. The Fitness Rubric tells you _what_ the user needs; these dimensions tell you _what_ to check on the artifact itself.

**Output Quality.** Are all required elements present? Do outputs match the spec? Does the code run without errors? Does the visual rendering work? Is the format right?

**Process Compliance.** Were the acceptance criteria met? Did the agent stay in scope? If code changed, were tests run? Was the correct workflow applied?

**Semantic Correctness.** Does the result make sense for its purpose? No placeholders, no garbage, no template artifacts. Would the intended user find this useful?

The three dimensions are framing for _what to look at_, not a checklist. Your verdict is one prose judgment on each, not three ticks.

## Concrete-defects-first (visual artifacts)

For any visual artifact (dashboard, UI, mockup, chart, slide, rendered PDF), **Section 1 of the report is observed defects** — visual phenomena with region or coordinates. Plain language. "The string '96 tasks' is rendered in ~48pt white over the child cells in the upper-left quadrant, obscuring their labels." Not: "the aggregate count overlays compete with project identity at the eye-first reading level."

Persona-anchored reasoning comes second and must cite a defect from Section 1.

### Completeness-Verification Heuristic

When evaluating the completeness of a change, implementation, or analysis, you must explicitly confirm:

1. **Freshness of inputs read**: Verify you are reading the most current data and state, not a stale cache or outdated file (see [Data Pipeline Verification](references/qualitative-assessment.md#data-pipeline-verification) for pipeline-specific guidance).
2. **Completeness of changes across all callsites**: If an API, convention, or behavior changes, verify that all downstream callsites and references have been updated.
3. **Acknowledgement of known limitations**: Honestly acknowledge any edge cases, constraints, or unverified paths rather than silently omitting them.

### Red Flags (HALT triggers)

This ordering blocks the failure mode where eloquent prose gives rendering catastrophes credible cover. See [[references/visual-analysis.md]] for the structural dimensions (legibility, layout, hierarchy, density). Cognitive-load and persona-emotional dimensions are _design-time_ questions and live in the spec's Fitness Rubric — not here.

## Data pipeline verification

Apply this to **any artifact that produces computed, aggregated, or transformed output**, even if the brief doesn't mention data explicitly. Dashboards, transcripts, reports, generated documents, dashboards-of-dashboards. If a number, list, or chart was derived from a source, you trace it:

1. **Identify the data source.** What file, API, query, or computation produces this output?
2. **Verify the source is real and populated.** Don't assume. Check.
3. **Check freshness, not just existence.** Static data in a dynamic field is failure.
4. **Cross-verify.** Independently query the source. Do values match? Are timestamps right? Anything silently dropped?
5. **Test fallbacks.** Disable the fallback; does the primary source work alone? Fallbacks silently mask broken primaries.
6. **Test under load.** Stale or partial data often only appears at runtime.

The question is "is this the RIGHT data?" — not "does data appear?" Output that looks plausible is the most dangerous kind of incorrect output.

## Anti-anchoring rule

If you have prior context on this artifact — earlier iterations, your own design choices, prior reviews you've authored — you are disqualified from the fitness-for-purpose verdict.

You may report observed _changes_ between iterations. The fitness verdict must come from a fresh-context reviewer. Canonical pattern: pauli assembles a minimal brief; a clean marsha runs in fresh context.

Eloquent narrative gives contamination cover. This rule blocks the substitution where "is iteration N better than N-1?" quietly replaces "is this fit for purpose?".

## Red flags (HALT triggers)

Any of these requires immediate FAIL, not "polish needed":

- Repeated section headers or empty sections between headers (template bug)
- Placeholder text in production (`{variable}`, `TODO`, `FIXME`)
- Overlapping or clipped text in rendered output
- Suspiciously short output for a complex operation
- "Success" claims without showing actual output
- Tests that check existence but not content
- Silent error handling (try/except swallowing errors)
- Data that looks plausible but doesn't match the source

## Verdict format

```
## Verification Report

**Bar:** mechanical / fitness / mixed
**Verdict:** PASS / FAIL / REVISE

### Concrete observations
[For visual artifacts: defect list with regions. Otherwise: short evidence list with file paths, line numbers, log excerpts.]

### Judgement
[Mechanical bar: one paragraph against AC and Red Flags. Fitness bar: one paragraph per Fitness Rubric dimension, citing evidence from concrete observations. Mixed bar: both — and the synthesis paragraph must address how the two sides combine. If the rubric flagged a dimension as load-bearing, address it explicitly. Prose, not tables.]

### Recommendation
[If FAIL/REVISE: what specifically needs to change, and why it matters to the user.]
```

## Browser-driven UI assessment

For running web apps, use Playwright MCP tools to drive a real browser:

1. `browser_navigate` to URL → `browser_wait_for` page-ready
2. `browser_resize` 1920×1080 → `browser_take_screenshot` each view
3. Interact to test functionality (`browser_click`, `browser_type`)
4. Save screenshots to `$AOPS_SESSIONS/qa-screenshots/YYYY-MM-DD/`
5. Apply concrete-defects-first.

## Delegation guidance

Briefs are short. Three things only:

1. The artifact (URL, screenshot path, PR URL).
2. The goal — one sentence.
3. The spec link — Fitness Rubric and AC live there.

Do NOT enumerate dimensions, methodology, persona prose, or what-to-check lists in the brief. Long briefs anchor the reviewer to checklist execution. The reviewer invokes `/verify` and reads methodology here.

**Anti-pattern:**

```
Verify the dashboard. Trace the data pipeline from source to output. Check freshness.
Test fallbacks. Verify during runtime. Apply visual-analysis.md. Inhabit the
anxious-academic persona. For each section...
```

[methodology in the brief crowds out fresh observation]

**Good pattern:**

```
Verify the treemap dashboard at <URL>. Goal: surface the shape of Nic's work
without adding overwhelm. Spec: <link> (Fitness Rubric + AC there).
```

## Follow-up tasks

After a FAIL or REVISE verdict, create a follow-up task:

- Title: `Address <project> QA findings`
- Priority: omit (defaults to P3; priority is set by the user during triage, not by agents)
- Body: link to verification report; AC = re-verify against the rubric and reach PASS

The QA report is evidence. The task is the action. Without a task, findings rot in `eval/` and nothing changes.

## Default (no args)

When invoked as `/verify` with no arguments, do a quick verification of the current session's work: identify what was requested and what was done, check whether the work actually achieves what was requested, produce a verdict with brief evidence.

## Integration

- **Stop hook**: May require verification before session end.
- **Task completion**: Verify before `complete_task()` — before marking done, run the completeness check in [[verify#completeness-verification-heuristic]]: (a) freshness (b) completeness (c) limitations.
- **Spec writing**: New user-facing specs MUST carry a `## Fitness Rubric` section authored via `/design-rubric` before they reach a worker.

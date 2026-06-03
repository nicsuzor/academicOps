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

## Forcing checks — resolve before any PASS on a user-facing artifact

These are not advisory. Each is a question with a mechanical answer that MUST appear, by name, in your verdict before you may write PASS. They exist because everything above this line can be **loaded and then rationalised around**: a reviewer with this whole methodology in context saw an artifact rendering `DERIVER_MISSING` on every load-bearing field, praised its "honesty," and returned PASS. Prose red flags did not stop it because the reviewer kept the discretion to reframe them. Writing these answers down removes that discretion — you cannot record "11 of 12 value-signals are sentinels" in a required field and still reach PASS without contradicting yourself.

**1. Sentinel / empty-state audit.** Count the load-bearing fields rendering as a sentinel, placeholder, or honest-failure token — `DERIVER_MISSING`, `NO_*`, `N/A`, `—`, `{variable}`, `TODO`, blank, or any "we couldn't compute this" stand-in. List them. **If the artifact's _primary_ value-signals are absent, the verdict is FAIL.** "Honest about being broken" is the floor every artifact must clear, never evidence that it works. An axiom-9-honest sentinel is still a missing value; do not launder honesty-about-emptiness into fitness.

**2. Principal's-eye top-line read.** Identify the single most-prominent element on the artifact — the largest, first-read, or headline element. Read it _as the end user_, not as a reviewer who knows the internals. State verbatim what it says and whether it is _correct for that user_. (This is the check that catches a "WHERE YOU WERE" panel surfacing a background worker's dispatch prompt as the principal's own last activity: prominent, confidently rendered, and wrong.)

**3. Floor vs ceiling — stated in the verdict.** Your verdict MUST answer, in these words: **"exceptional, or merely working?"** On a fitness bar, _"merely working" is not a PASS_ — the bar is the Fitness Rubric, which defines excellence, not minimum function. "REVISE — works but does not yet serve the user" is the honest verdict for merely-working; reserve PASS for artifacts that clear the rubric.

If any of the three forces a FAIL, **HALT**: stop the verification, write the FAIL/HALT verdict, and do not continue softening it into "polish needed." A terminal finding _ends the pass_ — it is not logged-and-continued. (Checks 1 and 2 apply to any user-facing artifact; check 3 applies on a fitness or mixed bar.)

Worked example — these checks replayed against the artifact that originally got a spurious PASS, returning FAIL/HALT: [[references/replay-overwhelm-dashboard-2026-06-03.md]].

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

**HALT means halt.** When you hit one of these, the verification is over: write the FAIL/HALT verdict and stop. Do not log it and keep walking the checklist hoping a later section redeems it, and do not downgrade it to "polish needed." A terminal violation is terminal — the most common way this skill fails in practice is a reviewer who _names_ the violation and then continues to a PASS anyway.

Any of these requires immediate FAIL, not "polish needed":

- Load-bearing fields rendering as sentinels / honest-failure tokens (`DERIVER_MISSING`, `NO_*`, `N/A`) where the artifact's primary value-signals should be — honesty about emptiness is the floor, not fitness (see forcing-check 1)
- The single most-prominent element is wrong for the end user (see forcing-check 2)
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

### Forcing checks
[REQUIRED for any user-facing artifact — omit only on a pure mechanical bar. Each must be answered explicitly; a PASS that skips these is invalid.]
1. **Sentinel/empty-state audit:** [count + list of load-bearing fields rendering as sentinels/placeholders/honest-failure tokens. If primary value-signals are absent → FAIL.]
2. **Principal's-eye top-line read:** [the single most-prominent element, quoted, read as the end user — correct for them, yes/no?]
3. **Floor vs ceiling:** [answer verbatim: "exceptional, or merely working?" On a fitness bar, "merely working" is not a PASS.]

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

### Do not pre-state the verdict you expect

Methodology-crowding (above) is one way a brief biases the reviewer; **verdict-priming** is the other, and it is more corrosive. The brief must not tell the reviewer what answer to reach. A QA brief is a request to _find out_, not to _confirm_. Verdict-priming language — "confirm this works", "verify the fix is good", "this should pass now", "just a quick sanity check", "make sure it's ready to merge" — pre-loads the conclusion and converts an independent verification into a rubber-stamp. The reviewer's default posture is IT'S BROKEN; a brief that asserts it works fights that posture before the reviewer has seen the artifact, and an anchored reviewer rationalises evidence toward the verdict the dispatcher signalled (this is precisely the failure that paired with the HALT failure in the originating incident).

State the artifact, the goal, and the spec — neutrally. Let the verdict come from the evidence.

**Anti-pattern (verdict pre-stated):**

```
Confirm the dashboard fix is working now — should be good. Quick QA before merge.
```

[the reviewer is told the answer; "confirm" + "should be good" + "before merge" all anchor to PASS]

**Good pattern (verdict left open):**

```
Verify the overwhelm dashboard at <URL>. Goal: surface the shape of Nic's work
without adding overwhelm. Spec: <link> (Fitness Rubric + AC there).
```

[names what to assess, not what to conclude — identical neutral shape to the good pattern above]

This is the QA-brief application of the framework-wide anti-anchoring doctrine in [[../aops/references/authoring-discipline]]: don't reduce the recipient's judgment to a foregone conclusion. If you are the dispatcher and you already believe the artifact passes, that belief is exactly what an independent reviewer exists to test — keep it out of the brief.

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
- **`merge_ready → done` auto-close**: The surfaces that auto-close a task on a merged PR (`/daily` Task Completion Sweep, `/sleep` PR-state sweep) MUST run the AC-verification step in [[references/merge-close-ac-check]] — re-read the task's acceptance criteria against the merged artifact, classify mechanical vs judgment-laden, and surface (never silently close) any unmet or judgment-laden criterion. This closes #1426: correspondence ("is this the right PR?") is not AC satisfaction ("are the criteria actually met?").
- **Spec writing**: New user-facing specs MUST carry a `## Fitness Rubric` section authored via `/design-rubric` before they reach a worker.

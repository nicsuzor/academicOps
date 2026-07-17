---
name: verify
description: Judgement-based QA pass. Does this artifact meet its goal and serve its
  user? Demands excellence, not compliance.
context: fork
agent: "aops:marsha"
---

# Judgement-Based Verification Guidelines

Conduct rigorous QA reviews of artifacts to ensure correctness, complete implementation, and fitness for purpose.

**Personality binding — earmarking.** This skill is earmarked to `marsha`: the "assume it's broken" posture below (Core Directives) is a direct expression of her broken-until-proven-otherwise judgment register. Running it under a different disposition would silently soften the bar it's designed to hold.

## Step 0 — Premise Test (forced; runs BEFORE you read the diff)

Before you read a single line of the diff, judge the **premise** from the task + diffstat alone and write the sharp principal's one-sentence snap reaction — _"was this a good idea, in this shape?"_ — verbatim, as forcing-check item 0. **You cannot emit a `PASS` verdict without it; a bad premise is a `FAIL` regardless of test coverage** (green tests are the _expected surface_ of a bad premise, not a mitigant). Diffstat-first ordering is mandatory — reading the code first is exactly what lets a clean, well-tested surface launder a bad premise.

Full definition, the verbatim prompt, the never-a-checklist hard rule, and the worked specimen live in the canonical reference: [[premise-test.md]]. (`FAIL` is the local rejection token here; the arch-fit lens emits 🔴 REJECT for the same call.)

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
4. **Project-rule check**: If `.agents/rules/RULES.md` exists in this repo, read it before judging. Apply its rules with the same class/instance discipline as `AXIOMS.md`. Project-rule violations belong under **Process Compliance** in the report, cited by `{#slug}`. `RULES.md` is not the only standard: for a content/instruction artifact (skill, agent body, prompt, doc, spec) also identify the skill that owns its quality standard for that artifact **type** and verify against it — e.g. `/craft` for instruction / agent-definition / skill / prompt edits. The governing standard often lives in a skill, not `RULES.md`.
5. **Forcing Checks**: Write explicit answers for each in the report before a PASS verdict:
   - **Premise Test (step 0, before reading the diff)**: State verbatim the sharp-principal reaction from task + diffstat alone (see Step 0). A bad premise is a `FAIL` regardless of test coverage; you cannot reach `PASS` without writing it.
   - **Sentinel / Empty-State Audit**: Count and list empty/sentinel fields (e.g. `DERIVER_MISSING`, `N/A`, `TODO`). Fail if primary value-signals are missing.
   - **Principal's-Eye Top-Line Read**: State verbatim the most prominent headline element and verify correctness for the end-user. For "show me my X" surfaces, this means reproducing the principal's literal view (his account, host, launch-context) and confirming HIS OWN instance is present — a generic instance is FAIL (see `/design-rubric` self-instance requirement).
   - **Floor vs Ceiling**: State verbatim: "exceptional, or merely working?". Merely working is not a PASS on fitness tasks.
6. **No Anchoring/Bias**:
   - If you participated in designing or iterating on this artifact, you are disqualified from reviewing it for fitness.
   - Dispatches must be neutral (do not pre-state expected verdicts).

## Evaluating Brief-Sourced Work (pipeline `evaluate` stage)

When the artifact under review was dispatched via a delegation brief ([[two-layer-decomposition]]),
the brief's **emit-for-evaluation contract** — quality rubric, claim-provenance rules, procedural
record — is the primary evidence source. Read it first; cite it directly in the report rather than
reconstructing the investigation from scratch. **Missing or thin emitted evidence is itself a
FAIL** — the executor didn't meet the contract — not a licence to re-investigate as if the brief
said nothing. Core Directive 1 ("verify evidence directly") still applies: independently confirm
what's emitted, don't just accept it uncross-checked.

This skill owns two of the pipeline's three evaluation lenses on that evidence:

- **Quality** — is the rubric/AC met? (the Fitness/Mechanical Bar above.)
- **Claim-reliability** — does the emitted evidence separate observed from inferred, and is every
  load-bearing claim provenanced? Treat an unprovenanced load-bearing claim as a sentinel (Forcing
  Check 1).

The third lens — **compliance** (regime/axiom obligations honoured) — belongs to
`/strategic-review` (rbg), not here; if compliance concerns surface mid-verification, note them
under Process Compliance and route rather than adjudicate.

## Data Pipeline Verification

For any artifact with computed, aggregated, or derived output (dashboards, reports, metrics), trace source → output: confirm the source is real, populated, and fresh; independently cross-verify the values against that source; disable any fallback to prove the primary path works alone (a fallback silently masks a broken primary); and check behaviour under load. The question is not "did output appear?" but "is this the RIGHT data?" — plausible-looking output is the most dangerous kind of incorrect output.

## HALT Triggers (Immediate FAIL)

Stop evaluation immediately and write a FAIL verdict if any of the following occur:

- **Bad premise** — a sharp principal would not have built this, or not in this shape (step-0 Premise Test failed; full definition [[premise-test.md]]). `FAIL` regardless of green tests; test-passing is the expected surface of this failure, not a mitigant.
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

### Process compliance

[Project-rule violations cited by `{#slug}` from `.agents/rules/RULES.md` if present, or "RULES.md absent — skipped"]

### Judgement

[Prose evaluation against AC, Red Flags, and/or Fitness Rubric dimensions]

### Recommendation

[If FAIL/REVISE: specific remediation steps and user impact. For brief-sourced work, phrase as a
critique addressed to the brief — name which brief element (intent / scoped context / constraints /
autonomy+non-goals / acceptance criteria / emit-for-evaluation / effort+door-type) was unmet or
ambiguous, so re-dispatch is a brief update, not a new plan.]
```

## Browser-Driven UI Verification

For web applications:

1. Navigate to the URL and wait for page-ready.
2. Capture screenshots at 1920×1080 resolution.
3. Save screenshots to `$AOPS_SESSIONS/qa-screenshots/YYYY-MM-DD/`.
4. Apply visual analysis checks for layout and legibility defects.

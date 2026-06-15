---
name: verify
type: skill
category: instruction
description: Judgement-based QA pass for this repo. Self-contained — readable by the GHA QA agent (no plugin reach). Demands excellence, not compliance. Owned by marsha (local) / qa.agent (GHA).
triggers:
  - "verify"
  - "QA check"
  - "acceptance test"
  - "quality check"
  - "is it done"
  - "validate work"
version: 1.0.0
permalink: skills-verify-repo
---

# Judgement-Based Verification — Repo-Local

This is the repo-local copy of the `/verify` skill. It is **self-contained on purpose**: the GitHub Actions QA agent (`.github/agents/qa.agent.md`) cannot reach the plugin payload at `${CLAUDE_PLUGIN_ROOT}`, so this skill MUST stand alone without `@`-imports.

Conduct rigorous QA reviews of artifacts to ensure correctness, complete implementation, and fitness for purpose.

> **SSoT note (acknowledged duplication).** The canonical local-session copy lives at `aops-core/skills/verify/SKILL.md` (consumed via the plugin in dev sessions). This file is a deliberate duplicate to serve the GHA context that cannot `@`-import from the plugin. Material changes to verification methodology must be made to **both** files; the duplication is a known exception to [[../../rules/AXIOMS.md#single-source-of-truth]] and is tracked at the `Verify runtime behaviour (qa)` row in [`specs/ENFORCEMENT-MAP.md`](../../../specs/ENFORCEMENT-MAP.md).

## Step 0 — Premise Test (forced; runs BEFORE you read the diff)

Before you read a single line of the diff, judge the **premise** from the task + diffstat alone and write the sharp principal's one-sentence snap reaction — _"was this a good idea, in this shape?"_ — verbatim, as forcing-check item 0. **You cannot emit a `PASS` verdict without it; a bad premise is a `FAIL` regardless of test coverage** (green tests are the _expected surface_ of a bad premise, not a mitigant). Diffstat-first ordering is mandatory — reading the code first is exactly what lets a clean, well-tested surface launder a bad premise.

### HARD RULE — one open sentence, never a checklist, never a field

- It is **one open prose sentence**, written first. It is **never** a form, a field, or a `- [ ]` checklist.
- A checklist re-commits the exact sin this test exists to stop: it abdicates the judgment to a mechanical rig you tick rather than a call you make. The moment _"was this a good idea?"_ becomes `[ ] worth doing? [ ] shape right?` you have rebuilt the rubric and the judgment is gone.
- The sentence must show you actually looked at _this_ premise. "Looks fine" / "ships clean" is vacuous — it records no premise assessment.

### Why diffstat-first ordering is mandatory

Reading the code first is exactly what lets a clean, well-tested surface **launder** a bad premise. Engage the diffstat and the task before the code, while the question _"should this exist at all?"_ is still askable without the pull of polished implementation.

### A bad premise fails — regardless of test coverage

If a sharp principal would bounce the premise, the verdict is a **rejection even with green CI, clean code, and satisfied AC**. The rejection token in this skill is `FAIL`. Test-passing is the **expected surface** of a bad-premise artifact, not a mitigant.

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
4. **Project-rule check**: If `.agents/rules/RULES.md` exists in this repo, read it before judging. Apply its rules with the same class/instance discipline as `AXIOMS.md`. Project-rule violations belong under **Process Compliance** in the report, cited by `{#slug}`.
5. **Forcing Checks**: Write explicit answers for each in the report before a PASS verdict:
   - **Premise Test (step 0, before reading the diff)**: State verbatim the sharp-principal reaction from task + diffstat alone (see Step 0). A bad premise is a `FAIL` regardless of test coverage; you cannot reach `PASS` without writing it.
   - **Sentinel / Empty-State Audit**: Count and list empty/sentinel fields (e.g. `DERIVER_MISSING`, `N/A`, `TODO`). Fail if primary value-signals are missing.
   - **Principal's-Eye Top-Line Read**: State verbatim the most prominent headline element and verify correctness for the end-user. For "show me my X" surfaces, this means reproducing the principal's literal view (his account, host, launch-context) and confirming HIS OWN instance is present — a generic instance is FAIL.
   - **Floor vs Ceiling**: State verbatim: "exceptional, or merely working?". Merely working is not a PASS on fitness tasks.
6. **No Anchoring/Bias**:
   - If you participated in designing or iterating on this artifact, you are disqualified from reviewing it for fitness.
   - Dispatches must be neutral (do not pre-state expected verdicts).

## Data Pipeline Verification

For any artifact with computed, aggregated, or derived output (dashboards, reports, metrics), trace source → output: confirm the source is real, populated, and fresh; independently cross-verify the values against that source; disable any fallback to prove the primary path works alone (a fallback silently masks a broken primary); and check behaviour under load. The question is not "did output appear?" but "is this the RIGHT data?" — plausible-looking output is the most dangerous kind of incorrect output.

## HALT Triggers (Immediate FAIL)

Stop evaluation immediately and write a FAIL verdict if any of the following occur:

- **Bad premise** — a sharp principal would not have built this, or not in this shape (step-0 Premise Test failed). `FAIL` regardless of green tests; test-passing is the expected surface of this failure, not a mitigant.
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

[If FAIL/REVISE: specific remediation steps and user impact]
```

## Browser-Driven UI Verification

For web applications:

1. Navigate to the URL and wait for page-ready.
2. Capture screenshots at 1920×1080 resolution.
3. Save screenshots to a known, writable artifacts directory for this run (`$AOPS_SESSIONS/qa-screenshots/YYYY-MM-DD/` in dev sessions; an Actions artifact upload path in GHA).
4. Apply visual analysis checks for layout and legibility defects.

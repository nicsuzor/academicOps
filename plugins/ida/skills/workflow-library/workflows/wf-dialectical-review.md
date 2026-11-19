---
alias:
  - wf-dialectical-review
  - wf-dialectical-design
  - wf-review-dialectic
  - wf-design-dialectic
  - wf-review
  - wf-multi-agent-review
default: true
description: "Universal default dialectical review workflow: Supervisor (james) calibrates proportionality and altitude upfront, coordinates parallel review across strategic direction/congruence (pauli), compliance (rbg), and qualitative excellence (marsha) into a reconciled PASS, REVISE, or FAIL verdict, and defines the shared review briefing."
id: wf-dialectical-review
tags:
  - wf-template
  - review
  - dialectic
  - multi-agent
  - briefing
  - default
title: Dialectical Review Workflow
type: template
---

## What this step does

Universal default review workflow: **`james` as Supervisor** calibrates **proportionality**, **altitude**, and **governing genre standard** upfront, defines the neutral shared review briefing, coordinates three non-overlapping specialist lenses concurrently, arbitrates tensions, and issues a reconciled `PASS`, `REVISE`, or `FAIL` verdict.

## Shared Review Briefing

All three review components draw their brief from this shared structure, presenting the originating request, governing standard, and acceptance criteria neutrally before the target artifact or diff without leading reviewers toward a verdict:

1. **Originating Request & Governing Standard (Read First, Neutral Framing)**:
   ```markdown
   ## Originating Request & Requirements

   > [Verbatim text of the user request, commission, or parent task ask authorizing this work]

   - **Source**: `<source-id-or-task-id>`
   - **Artifact Genre & Governing Standard**: `<artifact type + repository governing genre/document standard when present, craft, disciplinary criteria, or task ACs>`
   - **Specifications / Acceptance Criteria**: `<explicit criteria or spec pointers, or "NONE AVAILABLE">`
   ```
2. **Supervisor Calibration (`james`)**:
   - **Proportionality**: Single-pass sanity check (`mid-tier`) for low-stakes, routine, or easily reversible work vs multi-round dialectical deliberation (`flagship`) for high-stakes, complex, or architectural work.
   - **Target altitude**: Abstraction focus matching the artifact (preventing premature micro-implementation drift or untestable generalities) and genre-matched standards (never applying task-handback sections like `## Ask` to non-task artifacts).
3. **Target Artifact**: Repository, Pull Request URL/number, Branch / Head Commit SHA, and Diff / Content reference.
4. **Specialist Lenses** (returning `PASS`, `REVISE`, or `FAIL` strictly within jurisdiction):
   - **Strategic Direction & Congruence (`pauli`)**: Evaluates core premise, strategic direction, parsimony, lifecycle coherence, and PKB seamless-web congruence from an inline graph-only brief.
   - **Compliance (`rbg`)**: Evaluates universal axioms, local/user rules, Gate 0 ask-bounded authority and non-mechanical baseline, data boundaries, and least-invasive enforcement.
   - **Qualitative Excellence (`marsha`)**: Evaluates pure qualitative excellence, structural clarity, and audience resonance across live rendered outputs against external purpose and governing genre standards (no runtime test execution, primary-source fact audits, or rule checks; absent governing standard or purpose triggers `FAIL`).
5. **Uncontroversial Self-Fixes vs Non-Deterministic Findings**:
   - Deterministic, uncontroversial fixes (typos, formatting, dead relative links, `data-boundaries` scrubbing) are applied directly, committed (`fix(review): <description>`), pushed so `HEAD` matches inspected state before `PASS`, and listed under `### Reviewer Self-Fixes Applied` (never `REVISE` solely for self-fixed items).
   - Non-deterministic defects (competing designs, missing specs, scope expansion, broken logic, failing checks) remain under `### Required Changes` / `### Findings` with `REVISE` or `FAIL`.

## Input contract

1. **Originating request**: Commissioning ask with source id, quoted verbatim and neutrally.
2. **Target artifact & governing genre standard**: File, diff, PR reference, or spec under review and the repository's governing genre and document standard (when present).
3. **Specifications, requirements & acceptance criteria**: Explicit constraints governing the artifact, or explicit notice of absence.
4. **Strategic context**: Parent task, target objectives, and related PKB notes or specifications.

## Stages

1. **Calibrate upfront (`james`)**: Assess stakes, blast radius, and reversibility; fix proportionality (`mid-tier` single-pass vs `flagship` multi-round), target altitude, and governing genre standard.
2. **Dispatch concurrent lenses**: Launch `pauli` (inline graph brief), `rbg`, and `marsha` in parallel at the calibrated tier. Halt immediately (`fail-fast`, `no-fallbacks`) if any required perspective is unavailable rather than falling back to single-agent review.
3. **Dialectical cross-examination & warrant check** _(scaled by proportionality)_:
   - Proceed straight to synthesis for clean low-stakes sanity checks.
   - For high-stakes work or conflicting findings, check warrants critically and route opposing critiques (`send_message`) while policing altitude drift: documentation notes prove only what they state, not current live state (require a verified completion record or record an **open question**); cited PRs or code must be authoritative, current, and spec-backed.
4. **Reconcile, post verdict, and release**:
   - Compile the unified findings table, `### Reviewer Self-Fixes Applied`, and unresolved open questions.
   - Preserve per-finding risk-vs-cost proportionality (never auto-inflating minor convergent items to max severity), while **never downgrading or softening any specialist `FAIL`** (any specialist `FAIL` forces overall `FAIL`).
   - Verify all `fix(review): ...` edits are committed and pushed so `HEAD` matches inspected state before issuing `PASS`.
   - When reviewing a pull request (and permitted by `data-boundaries`), post explicit distinct verdict headers (`## Strategic Review: [PASS | REVISE | FAIL]` and `## RBG Review: [PASS | REVISE | FAIL]`, plus qualitative assessment) matched to the reviewed head commit SHA.
   - **Headless release**: `PASS` releases as `done` with reconciled report and self-fixes; `REVISE` or `FAIL` releases as `failed` (or `partial`) recording findings in `reason`, never pausing for user input or minting follow-up tasks.

## Output contract

Unified review report containing calibration summary (tier, rounds, altitude, governing standard), `### Reviewer Self-Fixes Applied`, itemized findings table with open questions, reconciled overall verdict (`PASS`, `REVISE`, or `FAIL`), and persistent write-back to the task record or PR thread.

## When to include

Default multi-perspective review workflow for milestones, specifications, designs, plans, documents, or pull requests prior to merge or release.

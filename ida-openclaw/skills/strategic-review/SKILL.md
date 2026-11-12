---
name: strategic-review
description: Modular multi-agent dialectical review of any artifact (specification, design, plan, document, PR) supervised by James. Calibrates proportionality and altitude upfront, deploys Pauli (strategic direction, core premise, and congruence with existing material), RBG (compliance and scope of authority), and Marsha (ambitious quality and requirement satisfaction across rendered multimodal outputs) in parallel, directs immediate self-fixes for uncontroversial issues, drives dialectical deliberation when warranted, and reconciles findings into a single PASS, REVISE, or FAIL verdict. Pass comment or fix flags to write results back.
---

# Strategic Review

Coordinate modular multi-agent dialectical review under **`james` as Supervisor** across three distinct review components and synthesize findings into one reconciled verdict (`PASS`, `REVISE`, or `FAIL`).

## Inputs

- **Artifact**: File path, PKB note ID, inline text, design proposal, specification, or PR reference (`owner/repo#N`).
- **Flags** (optional): `comment` (post findings to review surface), `fix` (apply minor fixes directly). Without flags, review is advisory.

## Review Process

### 1. Supervisor Calibration: Proportionality, Altitude & Governing Standard (`james`)

Before dispatching reviewers, the Supervisor (`james`) loads the artifact, its originating request, the format/quality standard governing the artifact's genre (`specs/meta/doc-taxonomy.md` -- e.g., `specs/meta/writing-specs.md` for specifications, `craft` for agent instructions, disciplinary standards for manuscripts/articles, or task acceptance criteria for task handbacks), and whatever specifications, requirements, or acceptance criteria are available, determines destination repository visibility (public or private), and explicitly calibrates:

- **Proportionality (depth, rounds, model selection, and primary-material scope)**: Weigh the importance, risk, blast radius, and reversibility of the task or artifact at the start:
  - **High-stakes / high-risk / architectural work**: Allocate deeper refinement, multiple rounds of dialectical cross-examination, and smarter, higher-capability models (`Model: "pro"`).
  - **Low-stakes / routine / reversible checks**: Keep the review to a fast, single-pass sanity check with lighter models (`Model: "flash"` or `"flash_lite"`) to confirm the change is sound without wasting time and money.
- **Altitude alignment & artifact-matched standard**: Define the target abstraction focus for the review and ensure reviewers apply the standard matching the artifact's genre (never applying task-handback sections like `## Ask` to non-task artifacts).

### 2. Deploy the Three Review Components in Parallel

Dispatch all three specialist reviewers concurrently in a single turn using the calibrated `Model` selection. Every reviewer's brief is drawn from the shared review briefing (quoting the originating request, governing genre standard, and available specifications/requirements/criteria before the artifact or diff) and returns a verdict in the unified `PASS` / `REVISE` / `FAIL` vocabulary:

- **Rule compliance** (TypeName `rbg`): Axiom and rule compliance per `wf-rbg`. Confined strictly to artifact text/diff and rule/spec sources.
- **Strategic fit** (TypeName `pauli`): Strategic Fit Check per `wf-strategic-fit`, provided with an inline graph-only brief.
- **Quality** (TypeName `marsha`): Qualitative excellence and audience resonance across live rendered outputs against purpose and genre standards per `verify`. Marsha never checks truth, fidelity, or technical correctness (which is verified upstream by authors and independent QA).

Every reviewer also judges proportion within its lens: whether the artifact builds more machinery than the request needs, and whether each requested change is worth its cost given the failure's likelihood and consequence. Reviewers immediately self-fix defects that can be resolved without controversy (language updates, data scrubbing under `data-boundaries`, simple deterministic repairs), commit them with `fix(review):`, and document them under `### Reviewer Self-Fixes Applied`. Uncontroversial self-fixes do not trigger `REVISE`; issues lacking a reasonably deterministic solution stay itemized findings.

### 3. Dialectical Deliberation & Critical Synthesis _(Proportional to Stakes)_

- **Fast path (low-stakes sanity check)**: When proportionality is set to single-pass and reviewers surface no fatal blockers or cross-component contradictions, proceed directly to reconciliation.
- **Dialectical rounds (high-stakes or conflicting findings)**: Read reviewer outputs critically rather than rubber-stamping them. Verify reviewer warrants: a documentation note (`README.md`, knowledge note) stating a behaviour proves only what the document says, not current working state (require a completed task record with verification evidence or live state, or else record it as an open question); a cited PR or code reference is authoritative only if it is the most recent merged change, reflects current working behaviour, and is backed by an authoritative specification or decision record. When reviewers surface competing tensions (e.g. compliance constraint vs strategic parsimony, or existing spec congruence vs implementation approach), `james` cross-examines the relevant reviewers with each other's critiques (`send_message`), demanding explicit defense, concession, or synthesis while holding the tension honestly. Intervene immediately if any reviewer drifts off the calibrated altitude.

### 4. Reconcile Findings

Synthesize component outputs into a unified findings table and compile itemized self-fixes:

| Reviewer | Issue | Feedback | Verdict / Disposition |
| - | - | - | - |

- Include a calibration header noting the chosen proportionality (model selection and rounds) and target altitude.
- Collapse concordant findings across reviewers into a single row that keeps each reviewer's own verdict/disposition; where they differ, state the disposition adopted and why.
- Give the strategic congruence review (`pauli`) its own row (`PASS`, `REVISE`, or `FAIL`), even when concordant with other rows.
- Itemize all self-fixes applied across reviewers under `### Reviewer Self-Fixes Applied`. If all identified defects were uncontroversial and self-fixed cleanly, do not issue `REVISE` solely for those items.
- **Overall verdict**: `PASS`, `REVISE`, or `FAIL`. Any expert reviewer's (`pauli`, `rbg`, or `marsha`) `FAIL` (including the absence of any specifications, requirements, or acceptance criteria) makes the combined verdict `FAIL`. The consolidating agent must never downgrade, overrule, or soften an expert reviewer's `FAIL` (e.g. to `REVISE` or `PASS`). If an expert reviewer is judged too harsh, that is the user's responsibility to fix by reviewing that reviewer agent, not the consolidating agent's job to soften. Any `REVISE` without a `FAIL` forces `REVISE` unless all pass (`PASS`).

### 5. Action and Reporting

- **Reviewer self-fixes**: Reviewers apply uncontroversial fixes directly to the working tree / branch, commit immediately (`fix(review): <description>`), and report them under `### Reviewer Self-Fixes Applied`. Issues lacking a reasonably deterministic solution remain as findings.
- **Default**: Return the calibration summary, reviewer self-fixes applied, synthesis table, and overall verdict (`PASS`, `REVISE`, or `FAIL`) to the caller.
- **`comment`**: Run the `data-boundaries` check against destination visibility before posting; then post reconciled feedback to the PR review or task note.
- **`fix`**: Run the `data-boundaries` check against destination visibility before pushing; apply straightforward mechanical remedies immediately.
- Write the final verdict and evidence to the artifact's task record.

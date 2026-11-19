---
name: strategic-review
description: Modular multi-agent dialectical review of any artifact (specification, design, plan, document, PR) supervised by James. Calibrates proportionality and altitude upfront, deploys Pauli (strategic direction, core premise, and congruence with existing material), RBG (compliance and scope of authority), and Marsha (qualitative excellence and audience resonance across rendered outputs against purpose and genre standards) in parallel, directs immediate self-fixes for uncontroversial issues, drives dialectical deliberation when warranted, and reconciles findings into a single PASS, REVISE, or FAIL verdict. Pass comment or fix flags to write results back.
---

# Strategic Review

Coordinate modular multi-agent dialectical review under **`james` as Supervisor** across three distinct review components and synthesize findings into one reconciled verdict (`PASS`, `REVISE`, or `FAIL`).

## Inputs

- **Artifact**: File path, PKB note ID, inline text, design proposal, specification, or PR reference (`owner/repo#N`).
- **Flags** (optional): `comment` (post findings to review surface), `fix` (apply minor fixes directly). Without flags, review is advisory.

## Review Process

### 1. Supervisor Calibration: Proportionality, Altitude & Governing Standard (`james`)

Before dispatching reviewers, the Supervisor (`james`) loads the artifact, its originating request, the repository's governing genre and document standards when present (e.g., `craft` for agent instructions, specification standards, disciplinary standards for manuscripts/articles, or task acceptance criteria for task handbacks), and whatever specifications, requirements, or acceptance criteria are available, determines destination repository visibility (public or private), and explicitly calibrates:

- **Proportionality (depth, rounds, and model selection)**: Weigh the importance, risk, blast radius, and reversibility of the task or artifact at the start:
  - **High-stakes / high-risk / architectural work**: Allocate deeper refinement, multiple rounds of dialectical cross-examination, and flagship models.
  - **Low-stakes / routine / reversible checks**: Keep the review to a fast, single-pass sanity check with mid-tier models to confirm the change is sound without wasting time and money.
- **Altitude alignment & artifact-matched standard**: Define the target abstraction focus for the review and ensure reviewers apply the standard matching the artifact's genre (never applying task-handback sections like `## Ask` to non-task artifacts).

### 2. Deploy the Three Review Components in Parallel

Dispatch all three specialist reviewers concurrently in a single turn at the calibrated model tier. Every reviewer's brief is drawn from the shared review briefing (quoting the originating request, governing genre standard, and available specifications/requirements/criteria neutrally before the artifact or diff without leading prompts) and returns a verdict in the unified `PASS` / `REVISE` / `FAIL` vocabulary:

- **Rule compliance** (TypeName `rbg`): Axiom, rule, ask-authority, data-boundary, and least-invasive enforcement compliance.
- **Strategic fit** (TypeName `pauli`): Core premise, strategic direction, parsimony, and PKB congruence (supplied with an inline brief).
- **Quality** (TypeName `marsha`): Pure qualitative excellence and audience resonance across live rendered outputs against external purpose and genre standards per `verify` (excluding primary-source truth audits, runtime test/QA execution, and rule checks).

Every reviewer also judges proportion within its lens: whether the artifact builds more machinery than the request needs, and whether each requested change is worth its cost given the failure's likelihood and consequence. When running sequentially or holding single-writer branch access, reviewers apply deterministic fixes (`data-boundaries` scrubbing, wording, links), commit (`fix(review): <description>`), and push before `PASS`; during concurrent read-only parallel subagent dispatch, reviewers instead report deterministic repairs under `### Suggested Fixes` for the supervisor or single-writer pass to apply cleanly without concurrent git conflicts. Uncontroversial self-fixes do not trigger `REVISE` once applied; non-deterministic trade-offs stay itemized findings.

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
- Itemize all self-fixes applied across reviewers under `### Reviewer Self-Fixes Applied`, and confirm every `fix(review):` commit is pushed so `HEAD` matches the reviewed state before reporting `PASS`. If all identified defects were uncontroversial and self-fixed cleanly, do not issue `REVISE` solely for those items.
- **Overall verdict**: `PASS`, `REVISE`, or `FAIL`. Preserve per-finding risk-vs-cost proportionality during reconciliation (do not auto-inflate minor convergent items to maximum severity), while never downgrading, overruling, or softening any expert reviewer's (`pauli`, `rbg`, or `marsha`) `FAIL` -- any specialist `FAIL` makes the combined verdict `FAIL`. If an expert reviewer is judged too harsh, that is the user's responsibility to fix by reviewing that reviewer agent, not the consolidating agent's job to soften. Any `REVISE` without a `FAIL` forces `REVISE` unless all pass (`PASS`).

### 5. Action and Reporting

- **Reviewer self-fixes**: In sequential/single-writer runs, reviewers commit (`fix(review): <description>`) and push deterministic repairs directly; in concurrent parallel read-only runs, they list deterministic repairs under `### Suggested Fixes` so the supervisor or single-writer pass commits (`fix(review): <description>`), pushes (`HEAD` matching reviewed state), and records them under `### Reviewer Self-Fixes Applied` before `PASS`. Non-deterministic defects remain itemized findings.
- **Default**: Return the calibration summary, reviewer self-fixes applied, synthesis table, and overall verdict (`PASS`, `REVISE`, or `FAIL`) to the caller.
- **`comment`**: Run the `data-boundaries` check against destination visibility before posting. On pull requests, post explicit distinct headers matched cleanly to the reviewed head commit SHA (`## Strategic Review: [PASS | REVISE | FAIL]` and `## RBG Review: [PASS | REVISE | FAIL]`, plus qualitative assessment) to the PR review thread; otherwise post reconciled feedback to the task note.
- **`fix`**: Run the `data-boundaries` check against destination visibility before pushing; commit and push straightforward mechanical remedies immediately so `HEAD` matches the reviewed state.
- Write the final verdict and evidence to the artifact's task record.

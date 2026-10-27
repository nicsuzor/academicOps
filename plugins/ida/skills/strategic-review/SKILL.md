---
name: strategic-review
description: Modular multi-agent dialectical review of any artifact (specification, design, plan, document, PR) supervised by James. Calibrates proportionality and altitude upfront, deploys Pauli (strategic direction, core premise, and congruence with existing material), RBG (compliance and scope of authority), and Marsha (ambitious quality and requirement satisfaction across rendered multimodal outputs) in parallel, drives dialectical deliberation when warranted, and reconciles findings into a single PASS, REVISE, or FAIL verdict. Pass comment or fix flags to write results back.
---

# Strategic Review

Coordinate modular multi-agent dialectical review under **`james` as Supervisor** across three distinct review components and synthesize findings into one reconciled verdict (`PASS`, `REVISE`, or `FAIL`).

## Inputs

- **Artifact**: File path, PKB note ID, inline text, design proposal, specification, or PR reference (`owner/repo#N`).
- **Flags** (optional): `comment` (post findings to review surface), `fix` (apply minor fixes directly). Without flags, review is advisory.

## Review Process

### 1. Supervisor Calibration: Proportionality, Altitude & Context (`james`)

Before dispatching reviewers, the Supervisor (`james`) loads the artifact, its originating request, and whatever specifications, requirements, or acceptance criteria are available, determines destination repository visibility (public or private), and explicitly calibrates:

- **Proportionality (depth, rounds, and model selection)**: Weigh the importance, blast radius, and reversibility of the task or artifact at the start:
  - **High-stakes / critical / architectural work**: Allocate deeper refinement, multiple rounds of dialectical cross-examination, and smarter, higher-capability models (`Model: "pro"`).
  - **Low-stakes / routine / reversible checks**: Keep the review to a fast, single-pass sanity check with lighter models (`Model: "flash"` or `"flash_lite"`) to confirm the change is sound without wasting time and money.
- **Altitude alignment**: Define the target abstraction focus for the review so reviewers neither drift into micro-implementation keystrokes on a strategic design nor remain at vague platitudes on a concrete implementation.

### 2. Deploy the Three Review Components in Parallel

Dispatch all three specialist reviewers concurrently in a single turn using the calibrated `Model` selection. Every reviewer's brief is drawn from the shared review briefing defined in `wf-review` (quoting the originating request and available specifications/requirements/criteria before the artifact or diff) and returns a verdict in the unified `PASS` / `REVISE` / `FAIL` vocabulary:

- **Strategic Direction & Congruence** (TypeName `pauli`, per `wf-strategic-fit`): Evaluates the **core premise, strategic direction, and congruence with the "seamless web" of existing material** in the PKB -- questioning the premise, naming the class of problem, probing for flawed reasoning, untested load-bearing assumptions, negative space, and missing edge cases, and situating the artifact against parent objectives, PKB graph topology, prior art, existing specifications, topic notes, parsimony, and lifecycle coherence (`PASS`, `REVISE`, or `FAIL`). Provide Pauli's brief inline in the dispatch payload (parent objective, claimed target nodes, problem definition, and summary of the proposed change) so Pauli operates strictly on the PKB graph without reading repository files or filesystem templates.
- **Compliance** (TypeName `rbg`, per `wf-rbg`): Evaluates **compliance and scope of authority** against universal axioms, project-local rules, _ultra vires_ boundaries, data boundaries, and the enforcement pyramid (`specs/enforcement/enforcement.md`). Confined strictly to artifact text/diff and governing rule/spec sources, returning `PASS`, `REVISE`, or `FAIL`.
- **Quality & Requirements Satisfaction** (TypeName `marsha`, per `wf-qa`): Evaluates **whether the work actually delivers on its requirements to an ambitious quality standard ("amazingly good", not merely working)** across actual rendered multimodal outputs (never code alone or simulated renders), runtime execution, and primary sources against whatever specifications, requirements, or acceptance criteria are available (`PASS`, `REVISE`, or `FAIL`) -- and **if no specifications, requirements, or acceptance criteria are available, treats that absence itself as an immediate critical failure signal (`FAIL`)**.

Every reviewer also judges proportion within its lens: whether the artifact builds more machinery than the request needs, and whether each requested change is worth its cost given the failure's likelihood and consequence.

### 3. Dialectical Deliberation & Critical Synthesis _(Proportional to Stakes)_

- **Fast path (low-stakes sanity check)**: When proportionality is set to single-pass and reviewers surface no fatal blockers or cross-component contradictions, proceed directly to reconciliation.
- **Dialectical rounds (high-stakes or conflicting findings)**: Read reviewer outputs critically rather than rubber-stamping them. When reviewers surface competing tensions (e.g. compliance constraint vs strategic parsimony, or existing spec congruence vs implementation approach), `james` cross-examines the relevant reviewers with each other's critiques (`send_message`), demanding explicit defense, concession, or synthesis while holding the tension honestly. Intervene immediately if any reviewer drifts off the calibrated altitude.

### 4. Reconcile Findings

Synthesize component outputs into a unified findings table:

| Reviewer | Issue | Feedback | Verdict / Disposition |
| - | - | - | - |

- Include a calibration header noting the chosen proportionality (model selection and rounds) and target altitude.
- Collapse concordant findings across reviewers into a single row that keeps each reviewer's own verdict/disposition; where they differ, state the disposition adopted and why.
- Give the strategic congruence review (`pauli`) its own row (`PASS`, `REVISE`, or `FAIL`), even when concordant with other rows.
- **Overall verdict**: `PASS`, `REVISE`, or `FAIL`. Any `FAIL` or `REVISE` from `pauli`, `rbg`, or `marsha` (including the absence of any specifications, requirements, or acceptance criteria) forces `REVISE` or `FAIL` unless the synthesis explicitly names the finding and reason that overrules it.

### 5. Action and Reporting

- **Default**: Return the calibration summary, synthesis table, and overall verdict (`PASS`, `REVISE`, or `FAIL`) to the caller.
- **`comment`**: Run the `data-boundaries` check against destination visibility before posting; then post reconciled feedback to the PR review or task note.
- **`fix`**: Run the `data-boundaries` check against destination visibility before pushing; apply straightforward mechanical remedies immediately.
- Write the final verdict and evidence to the artifact's task record.

---
name: strategic-review
description: Modular multi-agent dialectical review of any artifact (specification, design, plan, document, PR) supervised by James. Calibrates proportionality and altitude upfront, deploys Pauli (strategic direction, core premise, and congruence with existing material), RBG (compliance and scope of authority), and Marsha (qualitative taste and audience resonance across rendered outputs against purpose and genre standards, never linters or functional QA) in parallel, directs serialized self-fixes when authorized, drives dialectical deliberation when warranted, and reconciles findings into PASS, REVISE, or FAIL. Pass comment or fix flags to write results back.
---

# Strategic Review

Coordinate modular multi-agent dialectical review under **`james` as Supervisor** across three specialist lenses and reconcile findings into one verdict (`PASS`, `REVISE`, or `FAIL`).

## Inputs

- **Artifact**: File path, PKB note ID, inline text, design proposal, specification, or PR reference (`owner/repo#N`).
- **Flags** (optional): `comment` (post findings to review surface), `fix` (apply minor fixes directly). Without flags, review is advisory.

## Review Process

### 1. Supervisor Calibration (`james`)

Before dispatching reviewers, load the artifact, its originating request, available specifications or acceptance criteria, and the governing genre standard (e.g., specification standards, `craft` for agent instructions, disciplinary standards for manuscripts, or task criteria for handbacks). Determine destination visibility (public or private) and calibrate:

- **Proportionality**: Match depth, rounds, primary-material scope, and reasoning capability to risk, blast radius, and reversibility:
  - _High-stakes / architectural_: Deeper refinement, multi-round dialectical cross-examination, highest-reasoning capability.
  - _Low-stakes / routine / reversible_: Single-pass sanity check with lightweight general capability.
- **Altitude & genre fit**: Fix the target abstraction level and apply only the standard matching the artifact's genre (never apply task-handback rules to non-task artifacts).

### 2. Parallel Specialist Dispatch

Dispatch all three reviewers concurrently in one turn using a shared briefing (originating request, governing genre standard, and requirements before the artifact or diff), returning `PASS`, `REVISE`, or `FAIL`:

- **Rule compliance** (`rbg`): Axiom, rule, authority, and enforcement-pyramid compliance.
- **Strategic fit** (`pauli`): Core premise, strategic direction, and PKB congruence (with an inline brief).
- **Quality** (`marsha`): Qualitative taste and audience resonance across live rendered outputs against purpose and genre standards per `verify` (never linters or functional QA).

Every reviewer judges proportion within its lens: whether the artifact builds more machinery than needed, and whether each requested change justifies its cost. Reviewers apply and commit uncontroversial fixes (`fix(review): <description>`) only when serialized and authorized on a writable branch (e.g. `fix` mode), itemizing them as Argdown observations in internal handbacks (or under `### Reviewer Self-Fixes Applied` in published PR/issue or user-facing reviews); during parallel read-only dispatch, report suggested repairs as Argdown findings internally (or under `### Suggested Fixes` in published/user-facing outputs) for the fix pass instead.

### 3. Dialectical Deliberation _(Proportional to Stakes)_

- **Fast path**: For single-pass sanity checks with no fatal blockers or cross-lens contradictions, proceed directly to reconciliation.
- **Dialectical rounds**: Read outputs critically and evaluate specialist reviews strictly on the face of the record per `ida:premise-check` (zero _de novo_ factual re-checking of primary sources; remand unsupported or conflicting factual claims to the reviewer). Verify warrants on the record: documentation (`README.md`, knowledge notes) proves only what the text says, not live working state (require completed verification evidence or quoted live state on the record, else record an open question); cited PRs or code are authoritative only if the record shows they are current and backed by a specification or decision record. When reviewers clash (e.g. compliance vs strategic parsimony), cross-examine them directly with each other's critiques to force defense, concession, or synthesis without softening the tension. Intervene immediately on altitude drift.

### 4. Reconcile Findings

Synthesize calibration (chosen proportionality, rounds, target altitude), itemized self-fixes or suggested fixes, and reconciled findings -- reporting solely in clean Argdown prose per `ida:premise-check` for internal agent-to-agent handbacks, and using the Markdown table and headings (`### Reviewer Self-Fixes Applied`, `### Suggested Fixes`) strictly for published PR/issue or user-facing outputs:

| Reviewer | Issue | Feedback | Verdict / Disposition |
| - | - | - | - |

- Collapse concordant findings across reviewers while preserving each reviewer's verdict; where they differ, state the adopted disposition and why. Keep `pauli`'s strategic congruence verdict distinct even when concordant.
- Do not issue `REVISE` solely for items already resolved cleanly by authorized self-fixes.
- **Overall verdict**: Any specialist `FAIL` forces `FAIL` (never downgrade or soften an expert `FAIL`). Any `REVISE` without a `FAIL` forces `REVISE`. Otherwise `PASS`.

### 5. Action and Reporting

- **Default**: Return internal agent-to-agent handbacks solely in clean Argdown prose per `ida:premise-check` (covering calibration, applied/suggested fixes, reconciled findings, and overall verdict); use Markdown headings and the synthesis table strictly for published PR/issue comments (`comment`) or user-facing outputs.
- **`comment` / `fix`**: Verify `data-boundaries` against destination visibility before posting comments or pushing commits (`fix` applies straightforward mechanical remedies).
- Record the final verdict and evidence on the artifact's task record.

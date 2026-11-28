---
name: strategic-review
description: Modular multi-agent dialectical review of any artifact (specification, design, plan, document, PR) supervised by James. Calibrates proportionality, altitude, and applicable standards upfront, dispatches warranted specialist lenses -- Pauli (strategic direction, core premise, and congruence; and, as a separate invocation, compliance and scope of authority) and Marsha (qualitative excellence across live rendered outputs when an audience-facing artifact was built) -- directs serialized self-fixes when authorized, drives dialectical deliberation when warranted, and reconciles valid in-jurisdiction findings into PASS, REVISE, or FAIL. Pass comment or fix flags to write results back.
---

# Strategic Review

Coordinate modular multi-agent dialectical review under **`james` as Supervisor** across warranted specialist lenses and reconcile valid in-jurisdiction findings into one verdict (`PASS`, `REVISE`, or `FAIL`).

## Inputs

- **Artifact**: File path, PKB note ID, inline text, design proposal, specification, or PR reference (`owner/repo#N`).
- **Flags** (optional): `comment` (post findings to review surface), `fix` (apply minor fixes directly). Without flags, review is advisory.

## Review Process

### 1. Supervisor Calibration (`james`)

Before dispatching reviewers, load the artifact, its originating request, and any user-set standard, specification, or acceptance criteria. Determine destination visibility (public or private) and calibrate:

- **Proportionality**: Match review depth, round budget, primary-material scope, and capability tier to risk, blast radius, and defeasibility:
  - _High-stakes / architectural_: Multi-round dialectical cross-examination and primary-source verification on empirical, code, or citation claims at `flagship` capability.
  - _Low-stakes / routine / defeasible_: Fast single-pass check at `mid-tier` capability.
- **Contextual standard & altitude**: Apply any standard of proof or evaluation bar set by the user; otherwise adopt one reasonable and appropriate in all the circumstances for the artifact's purpose, audience, and stakes (never applying task-handback checklists to non-task artifacts, and never substituting rigid genre lookup tables or arbitrary numeric cutoffs/proxies for qualitative judgment).
- **Warranted branches**: Select only the specialist branches warranted in the circumstances -- skip `marsha` on non-build, lookup, or diagnostic replies where no audience-facing artifact was built.

### 2. Parallel Specialist Dispatch

Dispatch the warranted specialist lenses concurrently in one turn as separate invocations using a shared briefing (originating request, calibrated contextual standard, and explicit requirements before the artifact or diff), awaiting all child runs before handing back once when the review's stopping point is met:

- **Rule compliance** (`pauli`, briefed for the compliance lens only, per `wf-rbg`): Axiom, rule, authority, and enforcement-pyramid compliance.
- **Strategic fit** (`pauli`, a second invocation that never sees the compliance review): Core premise, strategic direction, and PKB congruence (with an inline brief).
- **Quality** (`marsha`, _when an audience-facing artifact was built_): Qualitative excellence and audience resonance across live rendered outputs per `verify` (evaluating qualitative standards directly with reasons; never linters, functional QA, or fake numeric proxies).

Every reviewer judges proportion within its lens: whether the artifact builds more machinery than needed, whether each requested change justifies its cost, and whether discretionary design, structure, or phrasing choices within the author's remit are reasonable (bounded-reasonableness deference protects choices that are not clearly wrong). Apply and commit uncontroversial fixes (`fix(review): <description>`) only when serialized and authorized on a writable branch (e.g. `fix` mode), itemizing applied fixes; during parallel read-only dispatch, itemize suggested fixes instead.

### 3. Dialectical Deliberation _(Proportional to Stakes)_

- **Fast path**: For single-pass checks with no fatal blockers or cross-lens contradictions, proceed directly to reconciliation.
- **Dialectical rounds**:
  - Run `ida:premise-check` judicial review on handbacks on the message alone (zero outside substantive checks; proportionate depth, material remands only).
  - Screen jurisdiction and standards: reject reviewer findings that act outside jurisdiction, police layout or phrasing preferences within reasonable authorial discretion, demand fake numeric proxies for qualitative judgment, or impose a standard of proof inappropriate in the circumstances.
  - Verify warrants on the record: documentation (`README.md`, knowledge notes) proves only what the text says, not live working state (require completed verification evidence or quoted live state, else mark an open question); cited PRs or code are authoritative only if shown current and backed by a specification or decision record.
  - When valid in-jurisdiction findings clash (e.g. compliance vs. strategic parsimony), cross-examine reviewers directly in prose Argdown blocks per `ida:premise-check` to force defense, concession, or synthesis without softening tension; intervene immediately on altitude drift.

### 4. Reconcile Findings

Compile calibration (chosen tier, rounds, contextual standard, target altitude), itemized self-fixes, suggested fixes, required changes, and reconciled findings (using the synthesis table when publishing Markdown):

| Reviewer | Issue | Feedback | Verdict / Disposition |
| - | - | - | - |

- Collapse concordant findings across reviewers while preserving each reviewer's verdict; where they differ, state the adopted disposition and why (recording reasons whenever an out-of-jurisdiction, taste-loop, fake-proxy, or wrong-standard finding is struck). Keep `pauli`'s strategic congruence verdict distinct even when concordant.
- Do not issue `REVISE` solely for items already resolved cleanly by authorized self-fixes or mere phrasing preferences.
- **Overall verdict**: Any valid substantive specialist `FAIL` within jurisdiction forces `FAIL` (never downgrade or soften a valid substantive in-jurisdiction `FAIL`). Any remaining material `REVISE` forces `REVISE`. Otherwise `PASS`.

### 5. Action and Reporting

- **Internal agent-to-agent messages**: Send all briefings, cross-examinations, and review handbacks solely in unfenced prose Argdown blocks per `ida:premise-check` (covering calibration, applied/suggested fixes, required changes, reconciled findings, and overall verdict). Treat any guard or harness refusal as a verbatim halt -- never bypass via `SendMessage` or alternate channels.
- **Published / user-facing outputs**: Use structured Markdown (`### Reviewer Self-Fixes Applied`, `### Suggested Fixes`, `### Required Changes`, and the synthesis table) strictly for published PR/issue comments (`comment`) or user-facing outputs.
- **`comment` / `fix`**: Verify `data-boundaries` against destination visibility before posting comments or pushing commits (scrubbing private PKB IDs and PII on public repositories while keeping internal IDs authorized in private task records and direct user replies; `fix` applies straightforward mechanical remedies).
- Record the final verdict and evidence on the artifact's task record.

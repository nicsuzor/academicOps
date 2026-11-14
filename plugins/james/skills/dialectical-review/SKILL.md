---
name: dialectical-review
description: Coordinate parallel multi-lens dialectical review across strategic fit (pauli), rule compliance (rbg), and qualitative excellence (marsha), supervised by james and reconciled into a single PASS, REVISE, or FAIL verdict. Use when reviewing specifications, designs, plans, documents, diffs, or PRs; pass comment or fix flags to write results back. Exclude for standalone logic checking of an argument block (use james:premise-check).
---

# /dialectical-review: Multi-Lens Dialectical Review

Coordinate modular multi-agent dialectical review supervised by **`james`** across three distinct specialist lenses (`pauli`, `rbg`, `marsha`) and synthesize findings into one reconciled verdict (`PASS`, `REVISE`, or `FAIL`). Operates across any repository with PKB MCP access without requiring `ida` or `rbg` plugins.

## Inputs

- **Artifact**: File path, PKB note ID, inline text, design proposal, specification, diff, or PR reference (`owner/repo#N`).
- **Flags** (optional): `comment` (post findings to review surface), `fix` (apply minor fixes directly). Without flags, review is advisory.

## Review Process

### 1. Supervisor Calibration: Proportionality, Altitude & Governing Standard (`james`)

Before dispatching reviewers, load the artifact, its originating request, and available specifications, requirements, or acceptance criteria. Identify the governing genre standard (consult `specs/meta/doc-taxonomy.md` or `specs/meta/writing-specs.md` when present in the target workspace; otherwise apply the standard matching the artifact's genre -- never imposing task-handback sections like `## Ask` on non-task artifacts). Determine destination visibility (public or private) and calibrate:

- **Proportionality (depth, rounds, model selection, and primary-material scope)**:
  - **High-stakes / high-risk / architectural / public**: Allocate deeper audit, multi-round cross-examination, primary-material checks, and high-capability models (`Model: "pro"`).
  - **Low-stakes / routine / reversible**: Keep review to a single-pass sanity check with lighter models (`Model: "flash"` or `"flash_lite"`).
- **Altitude alignment**: Set the target abstraction level for reviewers and police drift during deliberation.

### 2. Deploy the Three Review Components in Parallel

Dispatch all three specialist reviewers concurrently in a single turn using the calibrated `Model`, drawing each brief from the shared briefing (originating request, governing genre standard, available specs/criteria, and the null `argdown` block `asks: none` / `[no claim]` for claim-free briefs):

- **Rule compliance (`rbg`)**: Evaluate against universal PKB axioms/rules (`type: axiom` / `type: rule` via PKB MCP) plus repo-local `.agents/rules/` and `specs/enforcement/enforcement.md` when present in the target workspace, `data-boundaries`, scope of authority, and non-over-engineering.
- **Strategic fit (`pauli`)**: Evaluate core premise, necessity, parsimony, strategic direction, and congruence with existing PKB material via PKB MCP tools.
- **Qualitative excellence (`marsha`)**: Evaluate audience empathy, structural clarity, legibility, visual/typographic quality across rendered outputs, and purpose satisfaction against the governing genre standard -- without fact-checking claims or executing test suites.

Every reviewer judges proportion within its lens and returns `PASS`, `REVISE`, or `FAIL` with a `james:premise-check` `argdown` report. Reviewers immediately self-fix uncontroversial deterministic defects (typo/link cleanup, public `data-boundaries` scrubbing), commit with `fix(review): <description>`, and record them under `### Reviewer Self-Fixes Applied`. Uncontroversial self-fixes do not trigger `REVISE`; non-deterministic issues remain itemized findings.

### 3. Dialectical Deliberation & Verification (`james`)

Verify each returned reviewer report qualitatively and record checker verdicts via `james:premise-check` (`verdict.py --judged-file <path>`) since `james` uses no automatic prompt hearsay gate.

- **Fast path (low-stakes single pass)**: When single-pass proportionality yields no fatal blockers or cross-lens contradictions, proceed directly to reconciliation.
- **Dialectical rounds (high-stakes or conflicting findings)**: Audit reviewer warrants critically rather than rubber-stamping them. A documentation or PKB note proves only what the document says, not live working state (require verified runtime/task evidence or record an open question); cited PRs or code must reflect current merged state. When reviewers surface competing tensions (e.g. compliance constraint vs parsimony), cross-examine the relevant reviewers (`send_message`) to force defense, concession, or synthesis while holding the calibrated altitude.

### 4. Reconcile Findings

Synthesize outputs into a calibration header, itemized self-fixes, and a unified findings table:

| Reviewer | Issue | Feedback | Verdict / Disposition |
| - | - | - | - |

- State chosen proportionality (model selection and rounds) and target altitude in the header.
- Give strategic congruence (`pauli`) its own row (`PASS`, `REVISE`, or `FAIL`) even when concordant; collapse concordant compliance/quality items while keeping each reviewer's disposition and explaining any adopted resolution when they diverge.
- List all applied self-fixes under `### Reviewer Self-Fixes Applied`.
- **Overall verdict**: Any `FAIL` from `pauli`, `rbg`, or `marsha` forces combined `FAIL` (never soften or downgrade an expert `FAIL`); any `REVISE` without `FAIL` forces `REVISE`; otherwise `PASS`.

### 5. Action and Reporting

- **Default**: Return calibration summary, reviewer self-fixes applied, synthesis table, and overall verdict (`PASS`, `REVISE`, or `FAIL`), ending with a parser-valid `james:premise-check` `argdown` block.
- **`comment`**: Verify `data-boundaries` against destination visibility before posting reconciled feedback to the PR review or task note.
- **`fix`**: Apply straightforward mechanical remedies immediately, verifying `data-boundaries` before pushing.
- Record the final verdict and evidence on the artifact's PKB task record when tracked.

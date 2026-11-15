---
name: dialectical-review
description: Coordinate parallel multi-lens dialectical review across strategic fit (pauli), rule compliance (rbg), and qualitative excellence (marsha), supervised by james and reconciled into a single PASS, REVISE, or FAIL verdict. Use when reviewing specifications, designs, plans, documents, diffs, or PRs; pass comment or fix flags to write results back. Exclude for standalone logic checking of an argument block (use james:premise-check).
---

# /dialectical-review: Multi-Lens Dialectical Review

Coordinate modular multi-agent dialectical review supervised by **`james`** across three distinct specialist lenses (`pauli`, `rbg`, `marsha`) and synthesize findings into one reconciled verdict (`PASS`, `REVISE`, or `FAIL`). Serves as the single authoritative procedure for dialectical reviews and `wf-dialectical-review` stages across any repository with PKB MCP access.

## Inputs

- **Artifact**: File path, PKB note ID, inline text, design proposal, specification, diff, or PR reference (`owner/repo#N`).
- **Flags** (optional): `comment` (post findings to review surface), `fix` (apply minor fixes directly). Without flags, review is advisory.

## Review Process

### 1. Supervisor Calibration: Proportionality, Altitude & Governing Standard (`james`)

Before dispatching reviewers, load the artifact, its originating request, and available specifications, requirements, or acceptance criteria. Identify the governing genre standard (consult `specs/meta/doc-taxonomy.md` or `specs/meta/writing-specs.md` when present in the target workspace; otherwise apply the standard matching the artifact's genre -- instruction authoring standards for agent instructions, disciplinary criteria for manuscripts, or task criteria for task handbacks, never imposing task-handback sections like `## Ask` on non-task artifacts). Determine destination visibility (public or private) and calibrate:

- **Proportionality (depth, rounds, model selection, and primary-material scope)**:
  - **High-stakes / high-risk / architectural / public**: Allocate deeper audit, multi-round cross-examination, primary-material checks by `marsha`, and higher-capability models.
  - **Low-stakes / routine / reversible**: Keep review to a single-pass sanity check with lightweight, faster models and no primary-material expeditions.
- **Altitude alignment**: Set the target abstraction level for reviewers and police drift during deliberation.

### 2. Shared Review Briefing & Parallel Dispatch

Dispatch all three specialist reviewers concurrently in a single turn using the calibrated `Model` (halting immediately if concurrent review perspectives are required but unavailable, per `fail-fast` and `no-fallbacks`). Present the originating request and governing standard/criteria before the target artifact or diff so reviewers evaluate intent and proportion before implementation details:

1. **Originating Request & Governing Standard**: Quote the originating request verbatim with its source ID, name the artifact genre and governing standard, and list available specifications or acceptance criteria (or `"NONE AVAILABLE"`).
2. **Supervisor Calibration**: State proportionality tier, whether high-risk primary-material audit is authorized, and target altitude.
3. **Target Artifact**: Repository, PR/branch/commit reference, and diff or artifact path, followed by the null `argdown` block (`asks: none` / `[no claim]`) for claim-free briefs.
4. **Specialist Lens Instructions**:
   - **Strategic Direction & Congruence (`pauli`)**: Follow `wf-strategic-fit`. Evaluate core premise, necessity, parsimony, strategic direction, and congruence with the "seamless web" of existing PKB material via PKB MCP tools and read-only inspection of the target diff, PR, or specification.
   - **Rule Compliance (`rbg`)**: Follow `wf-rbg`. Assemble `james:axioms` (`skills/axioms/` and compiled `rules/`) alongside PKB `type: axiom` / `type: rule` nodes, plus repo-local `.agents/rules/` and `specs/enforcement/enforcement.md` when present in the target workspace (halting with `FAIL` if required axiom sources cannot be resolved). State the smallest qualifying change and non-mechanical baseline from the request alone before reading the diff (`FAIL` under `no-over-engineering` and `proportionate` if executable code is built where instructions or workflows suffice), and verify `data-boundaries`, scope of authority (_ultra vires_), and non-delegable judgment.
   - **Qualitative Excellence (`marsha`)**: Evaluate audience empathy, structural clarity, legibility, visual/typographic craft across live rendered multimodal outputs, and purpose satisfaction against the governing genre standard -- without fact-checking claims or executing test suites. Audit primary materials when calibrated as high-risk. If no governing standard, specifications, requirements, or acceptance criteria exist, treat that absence as an immediate `FAIL`.

Every reviewer returns `PASS`, `REVISE`, or `FAIL` with a `james:premise-check` `argdown` report. Reviewers immediately apply uncontroversial deterministic self-fixes (typo/link cleanup, public `data-boundaries` scrubbing), commit with `fix(review): <description>`, and itemize them under `### Reviewer Self-Fixes Applied`. Self-fixed uncontroversial defects do not trigger `REVISE`; non-deterministic trade-offs or broken logic remain itemized findings.

### 3. Dialectical Deliberation & Warrant Verification (`james`)

Verify each returned reviewer report qualitatively and record checker verdicts via `james:premise-check` (`verdict.py --judged-file <path>`).

- **Fast path (low-stakes single pass)**: When single-pass proportionality yields no fatal blockers or cross-lens contradictions, proceed directly to reconciliation.
- **Dialectical rounds (high-stakes or conflicting findings)**: Interrogate reviewer warrants critically:
  - Did RBG catch the real compliance and authority question, or a surface reading?
  - Did Pauli question the question, or just review the document as posed?
  - Did Marsha evaluate the rendered output or verified receipts against the right genre standard, or merely skim the diff?
  - Require a completed task record (`status: done` with verification evidence) or verified live state before accepting a documentation or note claim that a problem or mechanism is obsolete (otherwise record an **open question**), and confirm that cited PRs or code reflect current merged state backed by an authoritative specification or decision record. Route opposing peer critiques across reviewers (`send_message`) to force defense, concession, or synthesis while holding altitude.

### 4. Reconcile Findings

Synthesize outputs into a calibration header, itemized self-fixes (`### Reviewer Self-Fixes Applied`), open questions, and a unified findings table:

| Reviewer | Issue | Feedback | Verdict / Disposition |
| - | - | - | - |

- Give strategic congruence (`pauli`) its own row (`PASS`, `REVISE`, or `FAIL`) even when concordant; collapse concordant compliance/quality items while keeping each reviewer's disposition and explaining any adopted resolution when they diverge.
- **Overall verdict**: Any `FAIL` from `pauli`, `rbg`, or `marsha` forces combined `FAIL` (never soften or downgrade an expert `FAIL`); any `REVISE` without `FAIL` forces `REVISE`; otherwise `PASS`.

### 5. Action, Reporting & Headless Release

- **Default**: Return calibration summary, reviewer self-fixes applied, synthesis table, and overall verdict (`PASS`, `REVISE`, or `FAIL`), ending with a parser-valid `james:premise-check` `argdown` block.
- **`comment` / `fix` flags**: Verify `data-boundaries` against destination visibility before posting reconciled feedback (`comment`) or pushing straightforward mechanical remedies (`fix`).
- **Task & headless workflow release**: Record the final verdict and evidence on the artifact's PKB task record when tracked. When executed as a headless task stage, a `PASS` verdict releases the review stage as `done`, whereas `REVISE` or `FAIL` releases as `failed` (or `partial`) with findings recorded in the release reason.

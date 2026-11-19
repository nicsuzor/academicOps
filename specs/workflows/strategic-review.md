---
id: strategic-review-spec
title: Strategic Review Workflow Specification
type: spec
category: workflow
status: ready
tags: [spec, workflow, review, multi-agent, strategic-review, lenses]
related: [[conceptual-review]], [[specs/workflows/workflow.md]]
---

# Strategic Review Workflow

## Purpose & Design Intent

Strategic Review is the framework's primary multi-agent quality gate for intellectual artifacts -- including specifications, design proposals, research manuscripts, pull requests, and architecture changes.

Its core design intent is to eliminate the failure mode of **self-grading** and **monolithic shallow critique** by establishing:

1. **Separation of Author and Reviewer**: The agent authoring or executing work never grades its own deliverable.
2. **Parallel Blind Review**: Independent specialized review personas (`rbg`, `pauli`, `marsha`) evaluate the artifact concurrently from distinct perspectives without contaminating each other's reasoning.
3. **Structured Synthesis & Reconciliation**: A single lead persona (`james`) reconciles multi-perspective findings into one actionable verdict rather than dumping a disjointed committee transcript on the user. During synthesis, `james` preserves per-finding risk-vs-cost proportionality (never auto-inflating minor convergent items to maximum severity), while any `FAIL` from an expert reviewer makes the combined verdict `FAIL` -- the consolidating agent never downgrades or softens a specialist `FAIL` (addressing an over-harsh reviewer is the user's responsibility to review that reviewer agent).
4. **Mandatory Write-Back**: The review verdict, synthesis table, and underlying evidence are persistently attached to the reviewed artifact's task record or pull request (matched to current `HEAD` commit SHA).

## Implementation Architecture

The workflow is implemented operationally via `plugins/ida/skills/strategic-review/SKILL.md` and the default review workflow, and supervised by `james`:

```
      [ James: Upfront Proportionality & Altitude Calibration ]
           (Rounds, Depth, Model Tier: flagship vs mid-tier)
                                  │
                       [ Artifact & Standards ]
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
[ pauli: Strategic ]     [ rbg: Compliance ]       [ marsha: Qualitative ]
[   Congruence     ]     [ (Axioms & Rules) ]      [     Excellence      ]
        │                         │                         │
        └─────────────────────────┼─────────────────────────┘
                                  │
                                  ▼
                      [ James: Reconciliation ]
                                  │
                      [ Single Reconciled Verdict ]
                        (PASS / REVISE / FAIL)
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
           [ Action: comment ]          [ Action: fix ]
           (PR / Note / PKB)         (Direct remediation)
```

## Core Guarantees & Lifecycle

### 1. Supervisor Upfront Proportionality, Altitude & Standard Calibration (`james`)

Before dispatching reviewers, the Supervisor (`james`) sets the target altitude (Strategic, Design, or Implementation), identifies the format and quality standard governing the artifact's genre (`specs/meta/doc-taxonomy.md` -- e.g., `specs/meta/writing-specs.md` for specifications, `craft` for agent instructions, disciplinary standards for manuscripts/articles, or task acceptance criteria for task handbacks; never applying task-handback sections like `## Ask` to non-task artifacts), and explicitly calibrates review proportionality to the artifact's importance and risk:

- **High-stakes / high-risk / foundational artifacts** (architecture, core rules, workflow specifications, high-risk code): Multi-round dialectical refinement using flagship models, cycling revisions until reviewer critiques converge.
- **Routine / low-stakes changes**: Single-round sanity pass using mid-tier models without primary-material expeditions to verify the artifact is sound without wasting time or compute.

### 2. Specialized Reviewer Roles & Shared Briefing

All three review roles draw their briefing from the shared review briefing and return verdicts in the unified `PASS` / `REVISE` / `FAIL` vocabulary. The brief presents the originating request quoted verbatim with its source identifier neutrally in a dedicated section read before any pull request, branch name, or diff (without leading prompts toward a verdict), and includes the governing genre standard alongside whatever specifications, requirements, or acceptance criteria are available.

Reviewers immediately apply, commit, and push uncontroversial mechanical fixes (`fix(review): ...`) directly when running sequentially so remote `HEAD` matches inspected state prior to `PASS` (or report them under `### Suggested Fixes` during concurrent read-only parallel subagent runs for supervisor/single-writer commit to avoid git conflicts) -- such as language polish, scrubbing private identifiers or session trailers under `data-boundaries`, fixing dead links, or correcting formatting -- and itemize them under `### Reviewer Self-Fixes Applied`. Uncontroversial committed and pushed self-fixes do not trigger a `REVISE` verdict if the artifact is otherwise sound; issues lacking a reasonably deterministic solution remain as itemized findings for worker revision.

Each of the three review roles operates in a distinct domain with strictly non-overlapping duties:

- **`pauli` (Strategic Fit & Congruence; template `wf-strategic-fit`)**: Evaluates the core premise, strategic direction, objective alignment, and congruence with the "seamless web" of existing material in the PKB graph:
  - Questions the core premise, names the class of problem, and probes for flawed reasoning, untested load-bearing assumptions, negative space, and missing edge cases.
  - Situates the artifact against parent objectives, active sibling tasks, and existing PKB notes/tasks, testing whether it is needed or whether an existing tool, native mechanism, or competing proposal already covers it.
  - Checks for parsimony, precedent, duplication, and cross-task lifecycle coherence across the graph, verifying that documentation notes are not mistaken for proofs of current working state (requiring a completed task record with verification evidence or flagging an open question) and that cited PRs/code are authoritative (merged/most recent, reflecting current working behaviour, and backed by a spec or decision record).
  - Returns `PASS`, `REVISE`, or `FAIL`.
  - **Boundary**: Operates strictly on the PKB graph from an inline briefing. Does not inspect repository source code for axiom violations (belongs to `rbg`), does not judge visual/prose aesthetics (belongs to `marsha`), and does not run tests or probes (belongs to author/QA).
- **`rbg` (Compliance)**: Evaluates compliance with universal axioms, project-local rules, scope of delegated authority (Gate 0 ask authority and non-mechanical baseline), least-invasive enforcement, data boundaries/public egress, and conditional document-placement/`/craft`/spec standards (`specs/enforcement/enforcement.md`):
  1. **Judge for Yourself**: Reaches verdicts from the request, artifact, and rules alone without consulting prior reviews first.
  2. **Gate 0 & Proportion First**: Holds additions, deletions, and brief-locked constraints to the verbatim user ask or standing mandate; from the quoted request, sizes the non-mechanical baseline before reading artifact internals and verifies loaded surface instructions proved insufficient before accepting extra mechanisms (`proportionate`, `no-over-engineering`, `categorical-imperative`).
  3. **Waivers, Errors, Anti-Circularity & Egress**: Holds waivers to literal quoted bounds, rejects errors hidden from executing turn context, rejects circular spec/test/prompt relaxations, and audits diffs, commits, trailers, titles, and PR text (`data-boundaries`).
  4. **Structured Output**: Produces `### Proportion & Mechanisms` (`Needs judgment: yes|no` never bypassing Gate 0 or fail-fast), `### Reviewer Self-Fixes Applied`, `### Required Changes`, and `### Suggested Improvements`.
  - **Boundary**: Operates strictly by static semantic evaluation. Does not execute runtime tests, run test suites, or scan codebase callers (correctness testing belongs to authors and independent QA), does not evaluate qualitative taste or UX (belongs to `marsha`), and does not evaluate high-level PKB objective alignment or competing backlog options (belongs to `pauli`).
- **`marsha` (Qualitative Excellence & Audience Resonance; template `verify`)**: Evaluates the live output artifact as its audience meets it against external purpose, governing genre standards, and excellence criteria:
  - Inspects live rendered outputs (rendered markdown, typeset PDFs, plots, screenshots, UI).
  - Assesses aesthetic grace, cognitive load, legibility, structural clarity, and audience empathy, applying anti-circular scrutiny (never accepting degraded outputs merely because internal PR-relaxed criteria pass; absent governing standard or purpose triggers `FAIL`).
  - Evaluates whether the deliverable is genuinely excellent for its intended audience rather than merely mediocre.
  - Returns `PASS`, `REVISE`, or `FAIL`.
  - **Boundary**: Never checks truth, fidelity, or primary factual claims (belongs to premise/hearsay checks), does not run test suites, linters, builds, or runtime QA checks (belongs to authoring workers and independent QA `wf-qa`), does not evaluate axioms or rules (belongs to `rbg`), and does not evaluate graph-level strategy (belongs to `pauli`).

### 3. Lens Selection

Reviewers do not perform broad, superficial sweeps. They selectively apply 3–4 focused analytical lenses aligned to the calibrated altitude and domain.

### 4. Verdict Vocabulary

All individual reviewers and the reconciled synthesis return verdicts using the unified vocabulary:

- **PASS**: Satisfies requirements, rules, and strategic congruence, with all uncontroversial `fix(review): ...` self-fixes committed and pushed so `HEAD` matches the reviewed state (any non-blocking suggestions noted inline).
- **REVISE**: Substantial rework required within the accepted scope (for issues with no deterministic fix).
- **FAIL**: Fundamental defect in premise, compliance, authority (_ultra vires_), missing specifications/criteria, simulated output renders, or disproportionate work.

During synthesis, the consolidating agent preserves per-finding risk-vs-cost proportionality (never inflating minor convergent items to maximum severity), while any `FAIL` from any individual reviewer (`pauli`, `rbg`, `marsha`) makes the combined reconciled verdict `FAIL`. The consolidating agent never downgrades or softens an expert reviewer's `FAIL` (e.g. to `REVISE` or `PASS`). If an expert reviewer is judged too harsh, that is the user's responsibility to fix by reviewing that reviewer agent, not the consolidating agent's job to soften.

### 5. Mandatory Return Channel

Whatever flags are set (`comment`, `fix`, or advisory only), the review outcome is written back to the artifact's permanent tracking node in the PKB, ensuring zero-context auditability. When `comment` is active on a pull request (and permitted by `data-boundaries`), distinct lens headers (`## Strategic Review: [PASS | REVISE | FAIL]` and `## RBG Review: [PASS | REVISE | FAIL]`, plus qualitative assessment) are posted on the PR thread matched cleanly to the reviewed `HEAD` commit SHA after any `fix(review):` commits are pushed.

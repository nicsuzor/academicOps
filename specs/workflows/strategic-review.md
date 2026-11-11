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
3. **Structured Synthesis & Reconciliation**: A single lead persona (`james`) reconciles multi-perspective findings into one actionable verdict rather than dumping a disjointed committee transcript on the user. A `FAIL` from any expert reviewer makes the combined verdict `FAIL`, and the consolidating agent never downgrades or softens it; addressing an over-harsh reviewer is the user's job to review that reviewer agent.
4. **Mandatory Write-Back**: The review verdict, synthesis table, and underlying evidence are persistently attached to the reviewed artifact's task record or pull request.

## Implementation Architecture

The workflow is implemented operationally via `plugins/ida/skills/strategic-review/SKILL.md` and the default review workflow, and supervised by `james`:

```
      [ James: Upfront Proportionality & Altitude Calibration ]
              (Rounds, Depth, Model Selection: pro vs flash)
                                  │
                       [ Artifact & Standards ]
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
[ pauli: Strategic ]     [ rbg: Compliance ]       [ marsha: Quality & ]
[   Congruence     ]     [ (Axioms & Rules) ]      [   Requirements    ]
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

- **High-stakes / high-risk / foundational artifacts** (architecture, core rules, workflow specifications, high-risk code): Multi-round dialectical refinement using higher-capability models (`pro`), cycling revisions until reviewer critiques converge, and instructing `marsha` to audit primary materials.
- **Routine / low-stakes changes**: Single-round sanity pass using lighter, faster models (`flash` or `flash_lite`) without primary-material expeditions to verify the artifact is sound without wasting time or compute.

### 2. Specialized Reviewer Roles & Shared Briefing

All three review roles draw their briefing from the shared review briefing and return verdicts in the unified `PASS` / `REVISE` / `FAIL` vocabulary. The brief presents the originating request quoted verbatim with its source identifier in a dedicated section read before any pull request, branch name, or diff, and includes the governing genre standard alongside whatever specifications, requirements, or acceptance criteria are available.

Reviewers immediately apply and commit uncontroversial mechanical fixes (`fix(review): ...`) directly to the branch--such as language polish, scrubbing private identifiers or session trailers under `data-boundaries`, fixing dead links, or correcting formatting--and itemize them under `### Reviewer Self-Fixes Applied`. Uncontroversial self-fixes do not trigger a `REVISE` verdict if the artifact is otherwise sound; issues lacking a reasonably deterministic solution remain as itemized findings for worker revision.

Each of the three review roles operates in a distinct domain with strictly non-overlapping duties:

- **`pauli` (Strategic Direction & Congruence)**: Evaluates the core premise, strategic direction, and congruence with the "seamless web" of existing material in the PKB graph:
  - Questions the core premise, names the class of problem, and probes for flawed reasoning, untested load-bearing assumptions, negative space, and missing edge cases.
  - Situates the artifact against parent objectives, active sibling tasks, and existing PKB notes/tasks, testing whether it is needed or whether an existing tool, native mechanism, or competing proposal already covers it.
  - Checks for congruence, duplication, and dependency conflicts across the graph, verifying that documentation notes are not mistaken for proofs of current working state (requiring a completed task record with verification evidence or flagging an open question) and that cited PRs/code are authoritative (merged/most recent, reflecting current working behaviour, and backed by a spec or decision record).
  - Returns `PASS`, `REVISE`, or `FAIL`.
  - **Boundary**: Operates strictly on the PKB graph from an inline briefing. Does not inspect repository source code for axiom violations (belongs to `rbg`) and does not run tests or probes (belongs to `marsha`).
- **`rbg` (Compliance)**: Evaluates compliance with universal axioms, project-local rules, scope of delegated authority (_ultra vires_), permission/data boundaries, and the enforcement pyramid (`specs/enforcement/enforcement.md`):
  1. **Judge for Yourself**: Reaches verdicts from the request, artifact, and rules alone without reading prior reviews, PR comments, or prior task reports.
  2. **Judge Proportion First**: From the quoted originating request, sizes the smallest mechanism meeting the request across its class before reading artifact internals, rejecting unneeded machinery under `proportionate`.
  3. **Apply Each Axiom to the Artifact**: Evaluates mechanisms by their runtime consequences, assesses whether the substantive decision requires qualitative judgment, and verifies that mechanisms do not violate axioms (such as delegating qualitative decisions to deterministic path/author/AST heuristics under `judgment-non-delegable`, or introducing silent fallback branches under `no-fallbacks`).
  4. **Mechanisms Analysis**: Produces a structured `### Mechanisms` section explicitly evaluating each added mechanism's decision, necessity of judgment, and broken axioms before issuing a verdict.
  - **Boundary**: Operates strictly by static semantic evaluation. Does not execute runtime tests, run test suites, or write scratch probe scripts (correctness testing belongs to authors and independent QA), does not evaluate qualitative taste or UX (belongs to `marsha`), and does not evaluate high-level PKB objective alignment or competing backlog options (belongs to `pauli`).
- **`pauli` (Strategic Fit; template `wf-strategic-fit`)**: Evaluates objective alignment, necessity, parsimony, precedent, and lifecycle coherence:
  - Situates the artifact against parent objectives in the PKB graph, testing whether it is needed or whether an existing tool, native mechanism, or competing proposal already solves it.
  - Checks for lifecycle deadlocks and dependency conflicts across tasks on the graph.
  - Returns an explicit `FIT` or `MISFIT` verdict.
  - **Boundary**: Does not inspect source code for axiom violations (belongs to `rbg`), does not judge visual/prose aesthetics (belongs to `marsha`), and does not run tests or probes (belongs to author/QA).
- **`marsha` (Qualitative Excellence & Audience Resonance; template `verify`)**: Evaluates the live output artifact as its audience meets it against purpose and excellence standards:
  - Inspects live rendered outputs (rendered markdown, typeset PDFs, screenshots, UI).
  - Assesses aesthetic grace, cognitive load, legibility, and audience empathy.
  - Evaluates whether the deliverable is amazingly good for its intended audience or merely mediocre.
  - Returns `PASS`, `REVISE`, or `FAIL`.
  - **Boundary**: Never checks truth, fidelity, or factual claims (belongs to hearsay checker and `premise-check`), does not run test suites or correctness checks (belongs to author and independent QA), does not evaluate axioms or rules (belongs to `rbg`), and does not evaluate graph-level strategy (belongs to `pauli`).

### 3. Lens Selection

Reviewers do not perform broad, superficial sweeps. They selectively apply 3–4 focused analytical lenses aligned to the calibrated altitude and domain.

### 4. Verdict Vocabulary

All individual reviewers and the reconciled synthesis return verdicts using the unified vocabulary:

- **PASS**: Satisfies requirements, rules, and strategic congruence (including cases where uncontroversial defects were self-fixed and committed, with any non-blocking suggestions noted inline).
- **REVISE**: Substantial rework required within the accepted scope (for issues with no deterministic fix).
- **FAIL**: Fundamental defect in premise, compliance, authority (_ultra vires_), missing specifications/criteria, simulated output renders, or disproportionate work.

A `FAIL` from any individual reviewer (`pauli`, `rbg`, `marsha`) makes the combined reconciled verdict `FAIL`. The consolidating agent never downgrades or softens an expert reviewer's `FAIL` (e.g. to `REVISE` or `PASS`). If an expert reviewer is judged too harsh, that is the user's responsibility to fix by reviewing that reviewer agent, not the consolidating agent's job to soften.

### 5. Mandatory Return Channel

Whatever flags are set (`comment`, `fix`, or advisory only), the review outcome must be written back to the artifact's permanent tracking node in the PKB, ensuring zero-context auditability.

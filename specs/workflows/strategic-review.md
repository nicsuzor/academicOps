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

The workflow is implemented operationally via `plugins/ida/skills/strategic-review/SKILL.md`, `plugins/ida/skills/workflow-library/workflows/wf-dialectical-design.md`, and `plugins/ida/skills/workflow-library/workflows/wf-review.md`, and supervised by `james`:

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

All three review roles draw their briefing from the shared review briefing defined in `wf-review` (`plugins/ida/skills/workflow-library/workflows/wf-review.md`) and return verdicts in the unified `PASS` / `REVISE` / `FAIL` vocabulary. The brief presents the originating request quoted verbatim with its source identifier in a dedicated section read before any pull request, branch name, or diff, and includes the governing genre standard alongside whatever specifications, requirements, or acceptance criteria are available.

Each of the three review roles operates in a distinct domain with strictly non-overlapping duties:

- **`pauli` (Strategic Direction & Congruence; template `wf-strategic-fit`)**: Evaluates the core premise, strategic direction, and congruence with the "seamless web" of existing material in the PKB graph:
  - Questions the core premise, names the class of problem, and probes for flawed reasoning, untested load-bearing assumptions, negative space, and missing edge cases.
  - Situates the artifact against parent objectives, active sibling tasks, and existing PKB notes/tasks, testing whether it is needed or whether an existing tool, native mechanism, or competing proposal already covers it.
  - Checks for congruence, duplication, and dependency conflicts across the graph, verifying that documentation notes are not mistaken for proofs of current working state (requiring a completed task record with verification evidence or flagging an open question) and that cited PRs/code are authoritative (merged/most recent, reflecting current working behaviour, and backed by a spec or decision record).
  - Returns `PASS`, `REVISE`, or `FAIL`.
  - **Boundary**: Operates strictly on the PKB graph from an inline briefing. Does not inspect repository source code for axiom violations (belongs to `rbg`) and does not run tests or probes (belongs to `marsha`).
- **`rbg` (Compliance; template `wf-rbg`)**: Evaluates compliance with universal axioms, project-local rules, scope of delegated authority (_ultra vires_), permission/data boundaries, and the enforcement pyramid (`specs/enforcement/enforcement.md`):
  1. **Judge for Yourself**: Reaches verdicts from the request, artifact, and rules alone without reading prior reviews, PR comments, or prior task reports.
  2. **Judge Proportion and Scope of Authority First**: From the quoted originating request, sizes the smallest mechanism meeting the request across its class before reading artifact internals, rejecting _ultra vires_ overreach and unneeded machinery under `proportionate` and `do-one-thing`, and checking that any new control starts at the bottom of the enforcement pyramid (`specs/enforcement/enforcement.md`).
  3. **Apply Each Axiom to the Artifact**: Evaluates mechanisms by their runtime consequences, assesses whether the substantive decision requires qualitative judgment, and verifies that mechanisms do not violate axioms (such as delegating qualitative decisions to deterministic path/author/AST heuristics under `judgment-non-delegable`, or introducing silent fallback branches under `halt-on-failure`).
  4. **Mechanisms Analysis**: Produces a structured `### Mechanisms` section explicitly evaluating each added mechanism's decision, necessity of judgment, and broken axioms before issuing a verdict (`PASS`, `REVISE`, or `FAIL`).
  - **Boundary**: Operates strictly by static semantic evaluation. Does not execute runtime tests, run test suites, or write scratch probe scripts (belongs to `marsha`), and does not evaluate the core premise or PKB graph congruence (belongs to `pauli`).
- **`marsha` (Quality & Requirement Satisfaction; template `wf-qa`)**: Evaluates whether the work actually delivers on its requirements and governing genre standard to an ambitious quality standard ("amazingly good", not merely working) across actual rendered multimodal outputs, runtime execution, and (on high-risk requests) primary sources:
  - **Upfront Standard & Specification Check**: Matches the evaluation standard to the artifact's genre (`specs/meta/doc-taxonomy.md` -- e.g., `specs/meta/writing-specs.md` for specifications), treats the absence of any governing standard, specifications, requirements, or acceptance criteria as an immediate critical failure signal (`FAIL`), and stops before running tests or code audits.
  - **Rendered Multimodal Output Inspection**: Evaluates artifacts in their actual rendered, multimodal form (live runtime output, rendered PDFs, visual plots, UI screenshots, built containers); output renders may never be simulated or mocked.
  - Runs test suites directly on the branch, checking that all tests pass cleanly.
  - Verifies red-to-green regression traces, ensuring tests failed on base and pass on branch.
  - Runs live probes with real inputs to observe actual execution behavior, exit codes, and output formatting.
  - On **high-risk requests** (as calibrated by `james`), audits empirical claims against primary materials (git history, CI logs, underlying file contents).
  - Returns `PASS`, `REVISE`, or `FAIL`.
  - **Boundary**: Does not evaluate the strategic core premise or PKB graph strategy (belongs to `pauli`) and does not evaluate code against axioms or author mechanisms analysis (belongs to `rbg`).

### 3. Lens Selection

Reviewers do not perform broad, superficial sweeps. They selectively apply 3–4 focused analytical lenses aligned to the calibrated altitude and domain.

### 4. Verdict Vocabulary

All individual reviewers and the reconciled synthesis return verdicts using the unified vocabulary:

- **PASS**: Satisfies requirements, rules, and strategic congruence (any minor non-blocking suggestions noted inline).
- **REVISE**: Substantial rework required within the accepted scope.
- **FAIL**: Fundamental defect in premise, compliance, authority (_ultra vires_), missing specifications/criteria, simulated output renders, or disproportionate work.

A `FAIL` from any individual reviewer (`pauli`, `rbg`, `marsha`) makes the combined reconciled verdict `FAIL`. The consolidating agent never downgrades or softens an expert reviewer's `FAIL` (e.g. to `REVISE` or `PASS`). If an expert reviewer is judged too harsh, that is the user's responsibility to fix by reviewing that reviewer agent, not the consolidating agent's job to soften.

### 5. Mandatory Return Channel

Whatever flags are set (`comment`, `fix`, or advisory only), the review outcome must be written back to the artifact's permanent tracking node in the PKB, ensuring zero-context auditability.

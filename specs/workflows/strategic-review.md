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
3. **Structured Synthesis & Reconciliation**: A single lead persona (`james`) reconciles multi-perspective findings into one actionable verdict rather than dumping a disjointed committee transcript on the user.
4. **Mandatory Write-Back**: The review verdict, synthesis table, and underlying evidence are persistently attached to the reviewed artifact's task record or pull request.

## Implementation Architecture

The workflow is implemented operationally via `plugins/ida/skills/strategic-review/SKILL.md`, `plugins/ida/skills/workflow-library/workflows/wf-dialectical-design.md`, and `plugins/ida/skills/workflow-library/workflows/wf-review.md`, and supervised by `james`:

```
      [ James: Upfront Proportionality & Altitude Calibration ]
              (Rounds, Depth, Model Tier: pro vs flash)
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
                      (APPROVE / MINOR / REVISE / REJECT)
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
           [ Action: comment ]          [ Action: fix ]
           (PR / Note / PKB)         (Direct remediation)
```

## Core Guarantees & Lifecycle

### 1. Supervisor Upfront Proportionality & Altitude Calibration (`james`)

Before dispatching reviewers, the Supervisor (`james`) sets the target altitude (Strategic, Design, or Implementation) and explicitly calibrates review proportionality to the artifact's importance:

- **High-stakes / foundational artifacts** (architecture, core rules, workflow specifications, high-risk code): Multi-round dialectical refinement using top-tier models (`pro`), cycling revisions until reviewer critiques converge.
- **Routine / low-stakes changes**: Single-round sanity pass using lighter, faster models (`flash` or `flash_lite`) to verify the artifact is sound without wasting time or compute.

### 2. Specialized Reviewer Roles & Shared Briefing

All three review roles draw their briefing from the shared review briefing defined in `wf-review` (`plugins/ida/skills/workflow-library/workflows/wf-review.md`). The brief presents the originating request quoted verbatim with its source identifier in a dedicated section read before any pull request, branch name, or diff, and includes whatever specifications, requirements, or acceptance criteria are available.

Each of the three review roles operates in a distinct domain with strictly non-overlapping duties:

- **`pauli` (Strategic Direction & Congruence; template `wf-strategic-fit`)**: Evaluates strategic direction and congruence with existing material in the PKB graph:
  - Situates the artifact against parent objectives and existing PKB notes/tasks, testing whether it is needed or whether an existing tool, native mechanism, or competing proposal already covers it.
  - Checks for congruence, duplication, and dependency conflicts across the graph.
  - Returns an explicit `FIT` or `MISFIT` verdict.
  - **Boundary**: Operates strictly on the PKB graph from an inline briefing. Does not inspect repository source code for axiom violations (belongs to `rbg`) and does not run tests or probes (belongs to `marsha`).
- **`rbg` (Compliance; template `wf-rbg`)**: Evaluates compliance with universal axioms, project-local rules, permission/data boundaries, and the enforcement pyramid (`specs/enforcement/enforcement.md`):
  1. **Judge for Yourself**: Reaches verdicts from the request, artifact, and rules alone without reading prior reviews, PR comments, or prior task reports.
  2. **Judge Proportion First**: From the quoted originating request, sizes the smallest mechanism meeting the request across its class before reading artifact internals, rejecting unneeded machinery under `proportionate` and checking that any new control starts at the bottom of the enforcement pyramid (`specs/enforcement/enforcement.md`).
  3. **Apply Each Axiom to the Artifact**: Evaluates mechanisms by their runtime consequences, assesses whether the substantive decision requires qualitative judgment, and verifies that mechanisms do not violate axioms (such as delegating qualitative decisions to deterministic path/author/AST heuristics under `judgment-non-delegable`, or introducing silent fallback branches under `halt-on-failure`).
  4. **Mechanisms Analysis**: Produces a structured `### Mechanisms` section explicitly evaluating each added mechanism's decision, necessity of judgment, and broken axioms before issuing a verdict.
  - **Boundary**: Operates strictly by static semantic evaluation. Does not execute runtime tests, run test suites, or write scratch probe scripts (belongs to `marsha`), and does not evaluate high-level PKB graph congruence (belongs to `pauli`).
- **`marsha` (Quality & Requirement Satisfaction; template `wf-qa`)**: Evaluates substantive quality and satisfaction of whatever specifications, requirements, or acceptance criteria are available:
  - **Gate 0 Criteria Check**: Treats the absence of any specifications, requirements, or acceptance criteria as an immediate critical failure signal (`FAIL` / `REJECT`) and halts before running tests or code audits.
  - Runs test suites directly on the branch, checking that all tests pass cleanly.
  - Verifies red-to-green regression traces, ensuring tests failed on base and pass on branch.
  - Runs live probes with real inputs to observe actual execution behavior, exit codes, and output formatting.
  - Audits empirical claims in task reports and PR descriptions against primary sources (git history, CI logs, file contents).
  - Returns `PASS`, `REVISE`, or `FAIL`.
  - **Boundary**: Does not evaluate code against axioms or author mechanisms analysis (belongs to `rbg`) and does not evaluate PKB graph strategy (belongs to `pauli`).

### 3. Lens Selection

Reviewers do not perform broad, superficial sweeps. They selectively apply 3–4 focused analytical lenses aligned to the calibrated altitude and domain.

### 4. Severity & Disposition Rubric

- **REJECT**: Fundamental defect in premise, architecture, or safety -- requires cancellation or full redesign.
- **REVISE**: Substantial rework required within the accepted scope.
- **FIX**: Clear, deterministic resolution exists (syntax, missing validation, straightforward test fix).
- **TRIVIAL**: Cosmetic, typographical, or formatting improvement.
- **ADVISORY**: Non-blocking observation or future consideration.

### 5. Mandatory Return Channel

Whatever flags are set (`comment`, `fix`, or advisory only), the review outcome must be written back to the artifact's permanent tracking node in the PKB, ensuring zero-context auditability for downstream agents.

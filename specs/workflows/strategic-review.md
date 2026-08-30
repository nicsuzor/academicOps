---
id: strategic-review-spec
title: Strategic Review Workflow Specification
type: spec
category: workflow
status: ready
tags: [spec, workflow, review, multi-agent, strategic-review, lenses]
related: [[conceptual-review]], [[task-pipeline]]
---

# Strategic Review Workflow

## Purpose & Design Intent

Strategic Review is the framework's primary multi-agent quality gate for intellectual artifacts — including specifications, design proposals, research manuscripts, pull requests, and architecture changes.

Its core design intent is to eliminate the failure mode of **self-grading** and **monolithic shallow critique** by establishing:

1. **Separation of Author and Reviewer**: The agent authoring or executing work never grades its own deliverable.
2. **Parallel Blind Review**: Independent specialized review personas (`rbg`, `pauli`, `marsha`) evaluate the artifact concurrently from distinct perspectives without contaminating each other's reasoning.
3. **Structured Synthesis & Reconciliation**: A single lead persona (`james`) reconciles multi-perspective findings into one actionable verdict rather than dumping a disjointed committee transcript on the user.
4. **Mandatory Write-Back**: The review verdict, synthesis table, and underlying evidence are persistently attached to the reviewed artifact's task record or pull request.

## Implementation Architecture

The workflow is implemented operationally via `plugins/orchestrate/skills/strategic-review/SKILL.md` and executed by `james`:

```
               [ Artifact & Standards ]
                          │
       ┌──────────────────┼──────────────────┐
       ▼                  ▼                  ▼
[ rbg: Rules ]    [ pauli: Strategy ] [ marsha: Quality ]
       │                  │                  │
       └──────────────────┼──────────────────┘
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

### 1. The Premise Test

Before inspecting code details or prose phrasing, the reviewer evaluates whether the premise of the change is sound:

- **Sharp-Principal Reaction**: An unconstrained one-sentence judgment on whether the artifact solves the right problem at the right altitude.
- **Mechanism Check**: Verifies whether an existing mechanism already accomplishes the goal, and whether the proposal contradicts or re-litigates a settled architectural decision.

### 2. Specialized Reviewer Roles

- **`rbg` (Axioms & Rules)**: Enforces compliance with core framework axioms, project-local rules, permission boundaries, and governance constraints.
- **`pauli` (Strategic Critique & Architectural Fit)**: Tests premise validity, root-cause placement, system-level coherence, and avoidance of shallow workarounds.
- **`marsha` (Excellence & Runtime Fitness)**: Probes runtime execution correctness, empirical evidence, test coverage, and end-user fitness.

### 3. Lens Selection

Reviewers do not perform broad, superficial sweeps. They selectively apply 3–4 focused analytical lenses from the Composable Lens Registry (e.g., _Self-consistency_, _Assumption hygiene_, _Strategic alignment_, _Scope discipline_, _Cross-reference consistency_).

### 4. Severity & Disposition Rubric

- **REJECT**: Fundamental defect in premise, architecture, or safety — requires cancellation or full redesign.
- **REVISE**: Substantial rework required within the accepted scope.
- **FIX**: Clear, deterministic resolution exists (syntax, missing validation, straightforward test fix).
- **TRIVIAL**: Cosmetic, typographical, or formatting improvement.
- **ADVISORY**: Non-blocking observation or future consideration.

### 5. Mandatory Return Channel

Whatever flags are set (`comment`, `fix`, or advisory only), the review outcome must be written back to the artifact's permanent tracking node in the PKB, ensuring zero-context auditability for downstream agents.

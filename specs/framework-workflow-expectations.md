---
title: Framework Workflow Expectations
type: spec
status: active
tier: core
depends_on: [enforcement]
tags: [spec, workflow, expectations, session-lifecycle]
created: 2026-03-12
note: "Extracted from deleted specs/flow.md — preserves core session lifecycle expectations"
---

# Framework Workflow Expectations

User-facing expectations for the academicOps session lifecycle. These define what the user can rely on from the framework across every session, regardless of the specific task or workflow.

See [[specs/enforcement.md]] for the technical enforcement architecture that gives effect to these expectations.

## User Expectations

As specified in the framework vision, the core loop ensures that academic work maintains epistemic integrity through synchronous enforcement and qualitative review.

1. **Zero-Friction Initialization**: Every session automatically configures the environment ($AOPS, $PYTHONPATH, $ACA_DATA) and ensures core principles (AXIOMS, HEURISTICS) are available for planning and compliance. Users expect a consistent, pre-configured starting state regardless of the working directory.
2. **Mandatory Hydration**: Terse prompts are automatically transformed into structured execution plans. The user expects the system to "think before acting," selecting appropriate workflows and skills based on intent before any modifications are made.
3. **Workflow-Driven Progress**: Execution follows defined, composable workflows (e.g., `feature-dev`, `tdd-cycle`). The user expects the framework to enforce these procedures, preventing "plan-less execution" and ensuring all required steps are performed in sequence.
4. **Continuous Compliance (Custodiet)**: The framework periodically audits the session for scope drift and principle violations. The user expects immediate notification (and session halting in block mode) if the agent diverges from the original intent or violates core axioms.
5. **Independent Verification (QA)**: Non-trivial work must pass a mandatory end-to-end check by an independent agent before completion. The user expects that "looks correct" is never accepted as "works correctly," and evidence of runtime verification is required.
6. **Captured Learning (Reflection)**: Every session concludes with a mandatory Framework Reflection (via `/handover`). The user expects that decisions, findings, and friction points are captured and persisted to the Knowledge Base (PKB), ensuring the framework "learns" across sessions.
7. **Verifiable End State**: Sessions close only when work is committed, pushed, and verified against the remote origin. The user expects that no work is left in a dirty or unpushed state, maintaining a clean audit trail.

## Relationship to Enforcement Architecture

These expectations are implemented through the [[specs/enforcement.md|enforcement layer defense model]]:

| Expectation              | Primary Enforcement Layer             |
| ------------------------ | ------------------------------------- |
| Zero-Friction Init       | Layer 1: SessionStart hooks           |
| Mandatory Hydration      | Layer 2: Hydration gate (PreToolUse)  |
| Workflow-Driven Progress | Layer 2: Prompt hydration + workflows |
| Continuous Compliance    | Layer 2.5: Custodiet periodic audit   |
| Independent Verification | Layer 5: QA agent post-hoc review     |
| Captured Learning        | Layer 5: Handover gate (Stop event)   |
| Verifiable End State     | Layer 5: Commit gate (Stop event)     |

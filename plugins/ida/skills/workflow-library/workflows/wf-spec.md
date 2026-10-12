---
alias:
  - wf-spec
description: Author a comprehensive technical specification covering architecture, interfaces, acceptance criteria, and, for code that executes, test design before implementation.
id: wf-spec
tags:
  - wf-template
  - spec
title: wf-spec
type: template
---

## What this step does

Authors a complete, unambiguous technical specification grounded in the evidence available to it. Establishes system architecture, data models, public interfaces, observable acceptance criteria, and, for code that executes, integration test plans before any implementation code is written.

## Procedure

1. **Problem statement and target** -- define the problem, user/caller context, and required capabilities.
2. **Architecture and data flow** -- describe the components and what each owns, and external integration points.
3. **Interface contracts** -- define data types, function signatures, schemas, or protocols with precision.
4. **Acceptance criteria** -- formulate concrete, observable, and falsifiable acceptance criteria for completion.
5. **Test and verification strategy** -- for code that executes, specify test cases (unit, integration, regression) validating each criterion; for any other criterion, how it is verified.
6. **Rule-compliance review** -- verify the draft specification against governing axioms (proportionality, single source of truth, closure) before finalizing or submitting for review. Remediate any `REVISE` findings before delivery.

## Output contract

A complete specification artifact (full spec, not a summary) that someone other than its author can judge, containing:

- Problem statement and architectural design.
- Concrete interface definitions and signatures.
- Itemized acceptance criteria, each mapped to its test where code executes, or to its verification otherwise.
- Rule-compliance review verdict (`APPROVE` or resolved `SUGGEST`).

## When to include

Any non-trivial feature, architectural overhaul, or integration where implementation without an agreed specification invites scope creep or architectural divergence.

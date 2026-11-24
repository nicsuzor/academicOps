---
description: Author a complete technical specification covering user stories, architecture, interfaces, acceptance criteria, and verification design before implementation.
id: wf-spec
tags:
  - wf-template
  - spec
title: Technical Specification Workflow
type: template
---

## What this step does

Authors an unambiguous technical specification grounded in primary evidence -- establishing architecture, interfaces, falsifiable acceptance criteria, and verification plans before implementation begins.

## Procedure

1. **Problem statement and human user stories**: Define the problem and write user stories strictly from the perspective of human users (`researcher`, `operator`, `developer`, `reader`), never agents, personas, or internal components.
2. **Scope boundaries**: State explicit in-scope commitments and concrete out-of-scope exclusions up front to prevent scope drift.
3. **Architecture, dependencies, and prior decisions**: Describe component ownership, data flow, dependencies, required error handling, and external integration points. Scan existing architectural decision records in the repository for settled constraints, and record a new ADR (e.g. MADR) when a significant architectural fork arises.
4. **Interface contracts**: Define data types, function signatures, schemas, or protocols precisely.
5. **Effort, risk, and mitigations**: Record proportionate complexity/effort drivers, failure modes, and concrete mitigations.
6. **Acceptance criteria and verification**: Formulate acceptance criteria from the human principal's perspective -- combining a **persona paragraph and qualitative dimensions** with falsifiable checks -- mapping each criterion to integration/unit tests for executable code or observable verification checks otherwise.
7. **Independent review**: Obtain an independent rule-compliance and proportionality review of the draft specification and resolve any `REVISE` findings before delivery.
8. **Delivery and PR lifecycle**:
   - _Stage 1 (design/spec preceding a build)_: Record the drafted spec change and independent review verdicts in a knowledge-base note referenced by the build task. Commit no standalone plan/design file, open no PR, and release as `done` once review passes (or `partial` if the user explicitly reserved a decision on competing alternatives -- never release as `review`).
   - _Stage 2 or single-task build (spec + code together)_: Commit the editable spec alongside implementation on one draft PR onto the base branch, marking it ready for review only after independent verification passes and review verdicts are posted to the PR thread.

## Output contract

- Complete specification (problem statement, human user stories, explicit scope, architecture/dependencies/error handling, interface contracts, effort/risk mitigations, persona-grounded acceptance criteria with qualitative dimensions and verification mapping) verified by an independent review verdict (`PASS` or resolved `REVISE`).
- For Stage 1: specification draft and review verdicts recorded in a knowledge-base note linked to the downstream build task, with no PR opened.
- For Stage 2 or single-task build: complete spec and code committed on a single PR onto the base branch, marked ready once independent check and review verdicts are posted.

## When to include

Non-trivial features, architectural changes, or integrations where building without an agreed specification invites scope drift or divergence.

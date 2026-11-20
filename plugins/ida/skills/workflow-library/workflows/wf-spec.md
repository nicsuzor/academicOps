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

1. **Problem statement and user stories**: Define the problem and write user stories strictly from the perspective of human users (researcher, operator, developer, reader), never agents or internal components.
2. **Architecture and prior decisions**: Describe component ownership, data flow, and external integration points. Scan existing architectural decision records in the repository for settled constraints, and record a new ADR (e.g. MADR) when a significant architectural fork arises.
3. **Interface contracts**: Define data types, function signatures, schemas, or protocols precisely.
4. **Acceptance criteria and verification**: Formulate concrete, falsifiable acceptance criteria, mapping each to test cases (unit, integration, regression) for executable code or to observable verification checks otherwise.
5. **Independent review**: Obtain an independent rule-compliance and proportionality review of the draft specification and resolve any `REVISE` findings before delivery.
6. **Delivery and PR lifecycle**:
   - _Stage 1 (design/spec preceding a build)_: Record the drafted spec change and independent review verdicts in a knowledge-base note referenced by the build task. Commit no standalone plan/design file, open no PR, and release as `done` once review passes (or `partial` if an explicit user decision on competing alternatives is required -- never release as `review`).
   - _Stage 2 or single-task build (spec + code together)_: Commit the editable spec alongside implementation on one draft PR onto the base branch, marking it ready for review only after independent verification passes and review verdicts are posted to the PR thread.

## Output contract

- Complete specification (problem statement, architecture, interface contracts, acceptance criteria, and verification mapping) verified by an independent review verdict (`PASS` or resolved `REVISE`).
- For Stage 1: specification draft and review verdicts recorded in a knowledge-base note linked to the downstream build task, with no PR opened.
- For Stage 2 or single-task build: complete spec and code committed on a single PR onto the base branch, marked ready once independent check and review verdicts are posted.

## When to include

Non-trivial features, architectural changes, or integrations where building without an agreed specification invites scope drift or divergence.

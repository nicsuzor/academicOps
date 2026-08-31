---
title: Develop Specification
type: template
category: process
description: Author or revise an architectural, feature, or governance specification before building. Select when defining system contracts, data models, or protocol interfaces. Not for task briefs (use `/aops:brief`) or implementing code directly (use `feature-dev`).
tags: [specification, design, architecture, contracts, process]
---

# Process: Develop Specification

Structured process for creating or revising technical specifications, interface contracts, and architectural rules.

## 1. Scope, Invariants, and Non-Goals

- Define the scope, core problem statement, and intended user persona for `<target>`.
- Enumerate non-negotiable invariants and explicit non-goals to prevent scope creep.
- Identify related existing specifications and architectural axioms to maintain alignment.

## 2. Interface Contracts and Data Models

- Define public APIs, data structures, schemas, and configuration models.
- Specify exact types, required fields, and boundary validations.
- Document state machines, lifecycle transitions, and data flow diagrams where applicable.

## 3. Operational Behavior and Failure Modes

- Specify behavior under normal operation, edge cases, and unexpected inputs.
- Define error codes, escalation paths, and recovery strategies for each failure mode.
- Establish performance, concurrency, and security requirements.

## 4. Verification and Acceptance Criteria

- Define how compliance with this specification will be verified (automated tests, static analysis, review gates).
- List machine-checkable criteria that prove an implementation conforms to the spec.

## 5. Review and Sign-off

- Compose `wf-qa` or review lens to audit the draft specification against architectural standards.
- Reconcile feedback and obtain principal approval before proceeding to implementation.

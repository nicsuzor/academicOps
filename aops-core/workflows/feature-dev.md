---
id: feature-dev
name: feature-dev-workflow
category: instruction
bases: [base-task-tracking, base-tdd, base-verification, base-handover]
description: Test-first feature development from idea to ship
permalink: workflows/feature-dev
tags: [workflow, development, feature, tdd, ship]
version: 1.1.0
---

# Feature Development Workflow

**Purpose**: Provide a structured approach for building and shipping new features using test-driven development.

**When to invoke**: User says "add feature X", "build Y", "implement Z", or similar.

## Core Feature-Dev Process

1. **Understand Requirements**: Analyze the request to identify features, UX, and constraints.
2. **Propose Plan**: Share a concise, high-level summary of the implementation strategy.
3. **Draft Tests**: Write tests for the first behavior before implementation.
4. **Implement**: Build the feature following the TDD cycle (red-green-refactor).
5. **Verify Feature**: Confirm behavioral correctness against the original request.
6. **Submit PR**: Follow the handover workflow to commit, push, and file a PR.

## Detailed Checklists

For comprehensive design, implementation, and verification checklists, see **[[references/feature-dev-details]]**:

- **Design Checklist** - Requirements, architecture, and UX
- **Implementation Checklist** - TDD, coding standards, and documentation
- **Verification Checklist** - Testing, polish, and build status

## Critical Rules

- **Test-First**: Always write failing tests before implementation (TDD).
- **Minimal Implementation**: Only build what the tests require.
- **Refactoring**: Keep tests green while cleaning up code.
- **Validation**: Verify against the original goal, not just the tests.
- **No Reverts**: Do not revert changes unless they cause errors.

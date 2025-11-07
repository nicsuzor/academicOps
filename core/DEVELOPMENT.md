---
title: "Development Methodology"
type: methodology
description: "Generic development principles and TDD workflow for agents. Project-specific enhancements in project-tier DEVELOPMENT.md files."
tags:
  - development
  - methodology
  - TDD
  - workflow
relations:
  - "[[chunks/AXIOMS]]"
  - "[[core/TESTING]]"
---

# Development Methodology

Generic development principles and TDD workflow. Project-specific enhancements in project-tier DEVELOPMENT.md files.

## Core Principles

**Test-Driven Development (TDD)**:
1. Write test first (red)
2. Implement minimum code to pass (green)
3. Refactor if needed
4. Commit atomic changes
5. Repeat for next feature

**Quality Gates**:
- All tests must pass before commit
- Code review via git-commit skill validation
- No defensive coding - fail fast on misconfiguration
- One atomic change per commit

**Supervisor Workflow**:

When tasks are complex (multiple steps, coordination needed):
1. Invoke supervisor agent
2. Supervisor creates success checklist
3. Supervisor delegates atomic tasks to specialized subagents
4. Each task: test → implement → commit → push cycle
5. Supervisor verifies completion against checklist

**When NOT to use supervisor**:
- Single-step tasks (use specialized agent directly)
- Pure exploration (use Explore subagent)
- Trivial changes

## File Creation Checkpoint

**BEFORE creating ANY file**, verify:

1. **Security**: No API keys, tokens, passwords, or secrets
2. **Location**: Correct directory (tests/ for tests, docs/ for docs, src/ for code)
3. **Purpose**: Following conventions (pytest for tests, GitHub issues for tracking)
4. **Alternatives**: Can I use/extend existing files?
5. **Necessity**: Is this permanent infrastructure or temporary tracking?

**If ANY answer is unclear**: STOP and clarify before proceeding.

## Fail-Fast Philosophy

**NO defensive coding**:
- ❌ Default values that mask configuration errors
- ❌ Silent fallbacks that hide problems
- ❌ Try/except blocks catching legitimate errors
- ❌ Warnings instead of errors for critical problems

**YES explicit failure**:
- ✅ Raise exceptions when configuration missing
- ✅ Explicit validation with clear error messages
- ✅ One golden path - no hidden alternatives
- ✅ Fail immediately at initialization, not at runtime

**When code fails**: Fix root cause, don't add defensive workarounds.

## Shared Infrastructure Impact

**High-risk shared files** (require extra caution):
- Core configuration modules
- Base classes and utilities
- Authentication/authorization
- Data models and schemas
- Testing fixtures and utilities

**Before modifying shared infrastructure**:

1. **Analyze impact**: What other code depends on this?
2. **Search usages**: grep/Glob to find all references
3. **Consider alternatives**: Can I solve this without changing shared code?
4. **Plan testing**: How will I verify nothing breaks?
5. **Document rationale**: Why is this change necessary?

**Red flags**:
- "Let me add a default here to fix my specific case"
- "I'll add a parameter with a default to avoid breaking others"
- "This quick fix should work for my use case"

**Correct approach**:
- Understand why shared code behaves as it does
- Fix root cause in your usage, not shared infrastructure
- If shared code truly has a bug, fix it properly with tests
- Document breaking changes and update dependent code

## Common Anti-Patterns

**Repository Documentation Pollution**:
- ❌ `*_README.md`, `*_NOTES.md`, `*_STATUS.md` for bug tracking
- ❌ Progress tracking files in test directories
- ❌ Implementation status files duplicating GitHub issues
- ✅ Use GitHub issues for tracking
- ✅ Self-documenting code and tests
- ✅ General docs in `docs/` only if widely applicable

**Rush-to-Code**:
- ❌ Jumping to implementation without understanding problem
- ❌ Skipping exploration phase
- ❌ Modifying code before reading related code
- ✅ Read existing code first
- ✅ Understand architecture and patterns
- ✅ Plan approach before implementing

See project-tier DEVELOPMENT.md for project-specific development standards.

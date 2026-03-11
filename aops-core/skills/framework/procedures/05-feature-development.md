# Feature Development Workflow

**Purpose**: Guide rigorous, test-first feature development from idea to validated implementation.

**When to use**: Adding new features, building significant functionality, implementing user-requested capabilities.

**When NOT to use**: Bug fixes (unless requiring new functionality), simple refactoring, documentation-only changes.

## Plan-First Development

No coding or development work without an approved plan. Sequence (NO EXCEPTIONS):

1. Create a plan for the proposed work
2. Define acceptance criteria
3. Get independent review of the plan
4. Get explicit approval from the academic lead before implementing

## Core Principles

This workflow enforces framework principles from [[AXIOMS.md]]:

- **Plan-First**: Approved plan before any implementation
- **Test-First**: Integration tests before implementation
- **Mandatory Acceptance Testing**: Tests are contracts - fix the code, not the test.
- **Explicit Success Criteria**: Define measurable outcomes upfront
- **User-Centric Acceptance Criteria**: Describe USER outcomes, not technical metrics.
- **Fail-Fast**: No partial success, fix or revert
- **Single Source of Truth**: Reference, don't duplicate
- **Experiment-Driven**: Document as formal experiments
- **Real Data Fixtures**: Test fixtures use real captured data.
- **Side-Effects Over Response Text**: Use observable side-effects for verification.
- **Bias for Action**: Execute without unnecessary confirmation.

## Overview

Feature development follows eight phases. See **[[feature-dev-details]]** for step-by-step procedures, templates, and integration guides.

1. **User Story Capture** - Zero-friction idea intake
2. **Requirements Analysis** - Transform into testable requirements
3. **Experiment Design** - Formalize plan with hypothesis
4. **Test-First Design** - Write integration tests first
5. **Development Planning** - Break into discrete steps
6. **Execution** - Build with continuous validation
7. **Validation** - Verify and decide keep/revert/iterate
8. **Spec Synthesis & Bazaar Review** - Update spec, submit PR for review

## GitHub Integration

Framework features go through bazaar review on GitHub (see [[specs/pr-pipeline-v2.md]]). This creates bidirectional links between the task system (PKB) and GitHub. See **[[feature-dev-details#GitHub Integration]]** for conventions.

## Templates

See **[[feature-dev-details#Templates]]** for links to all development templates.

## Progress Tracking

Use TodoWrite at key points (Phase 1 and Phase 5). See **[[feature-dev-details#Progress Tracking]]** for standard todo lists.

## Error Handling

**Fail-Fast on all issues**:

- When tests fail: HALT, fix or revert.
- When blocked on infrastructure: HALT, report issue.
- When requirements unclear: Go back to Phase 2.

See **[[feature-dev-details#Error Handling]]** for detailed protocols.

## Quick Reference

1. Invoke framework skill
2. Capture story → Analyze requirements → Design experiment
3. Write tests → Plan development → Implement feature
4. Validate → Synthesize to spec → Open PR

**Remember**: Test before code. Define success upfront. Fail-fast. Reference, don't duplicate. Bias for action.

---
id: qa-design
category: quality-assurance
bases: [base-task-tracking]
---

# Designing Acceptance Testing Systems

Design end-to-end acceptance testing infrastructure for any project. Focus: **outcome-based verification** (is the work useful?) not just **execution verification** (did it run?).

## Routing Signals

- "Design QA system", "build acceptance testing", "create test infrastructure"
- New project needs verification strategy
- Existing tests pass but don't catch real problems

## NOT This Workflow

- Running existing tests → use project test commands
- Verifying a single feature → [[qa]]
- Code review → [[critic-fast]]

## Core Principle

**Outcome over execution**: Tests that pass but don't detect problems are worse than no tests. Design for semantic judgment, not pattern matching.

## Task Chain Pattern

Design acceptance testing as a **dependent task chain**. Each phase blocks the next - no jumping ahead.

```
[Epic: Acceptance Testing System]
├── T1: Inventory (what exists?)
├── T2: Gap Analysis (what's missing?) → depends on T1
├── T3: Design Workflow (how will it work?) → depends on T2
├── T4: Define Test Cases (what to test?) → depends on T3
└── T5+: Implementation → depends on T4
```

## Phase 1: Inventory

**Question**: What QA infrastructure already exists?

Survey existing:

- Test frameworks and runners
- Verification scripts or checks
- Review processes (code review, QA gates)
- Documentation of expected behavior
- Existing acceptance criteria

**Output**: Structured inventory with file paths and capability summaries.

## Phase 2: Gap Analysis

**Question**: What's missing for outcome-based QA?

Assess against these capabilities:

1. Can reviewers verify **outcome quality** (not just completion)?
2. Are there test cases with **explicit fail conditions**?
3. Is there **batch execution** with measurement?
4. Can reviewers examine **actual outputs** (not just pass/fail)?
5. Are verdicts based on **semantic judgment** (not regex)?

**Output**: Gap report classifying each gap as build-new or enhance-existing.

## Phase 3: Design Workflow

**Question**: How will the QA system work end-to-end?

Design these components:

1. **Reviewer lifecycle**: setup → execute → review → verdict
2. **Test case format**: feature, expected behavior, fail condition
3. **Batch execution**: how to run multiple tests, aggregate results
4. **Outcome review**: how reviewer assesses usefulness
5. **Reporting**: what evidence is captured for each verdict

**Key constraint**: No shortcuts. Reviewer must examine actual outputs and make semantic judgments. Pattern matching is forbidden.

**Output**: Workflow specification document with examples.

## Phase 4: Define Test Cases

**Question**: What specific behaviors must be tested?

For each key feature:

- **Feature name**: What's being tested
- **Expected behavior**: What success looks like
- **Fail condition**: What specific problem this catches
- **Reproducible scenario**: Exact steps to execute the test

Create coverage matrix mapping test cases to features. Identify gaps.

**Output**: Test case catalog with reproducible scenarios.

## Phase 5+: Implementation

Build the designed system. Created **after** test cases are defined and reviewed.

Typical tasks:

- Implement test execution framework
- Implement reviewer guidance/checklist
- Implement batch runner
- Create documentation and examples

## Anti-Patterns to Avoid

| Anti-Pattern            | Why It Fails                          | Instead                          |
| ----------------------- | ------------------------------------- | -------------------------------- |
| Pattern matching        | Passes without semantic understanding | Reviewer examines actual output  |
| "Did it run?" tests     | Passes broken behavior                | Verify outcome is useful         |
| Element presence checks | UI exists but content is garbage      | Check content quality            |
| Success = no errors     | Silent failures pass                  | Define positive success criteria |
| Skip to implementation  | Build wrong thing                     | Complete design phases first     |

## Verification

Before declaring acceptance testing system complete:

1. Run test cases - each catches its designed fail condition
2. Reviewer correctly identifies pass/fail using semantic judgment
3. Batch execution produces useful aggregate report
4. Report includes evidence (outputs, not just verdicts)
5. No regex or pattern matching in verdict logic

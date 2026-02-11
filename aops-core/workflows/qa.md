---
id: qa
category: quality-assurance
bases: [base-task-tracking, base-qa]
---

# QA

Quality assurance and verification workflows. Multiple modes for different verification needs.

## Routing Signals

- Feature complete, before final commit
- User-facing functionality changes
- Complex changes with acceptance criteria
- Building QA infrastructure
- Framework integration validation

## NOT This Workflow

- Code review / skeptical review → [[critic]]
- Bug investigation → [[debugging]]
- Trivial changes (typo fixes)

---

## Mode: Quick Verification

**Default mode.** Pre-completion sanity check. "Does it run without error?"

### When to Use

- Feature complete, tests pass
- Before final commit
- User-facing changes

### Invocation

```
Task(subagent_type="qa",
     prompt="Verify work meets acceptance criteria: [CRITERIA]. Check functionality, quality, completeness.")
```

### Verdicts

- **VERIFIED**: Proceed to completion
- **ISSUES**: Fix critical/major issues, re-verify

---

## Mode: Acceptance Testing

Full user acceptance testing workflow. Creates test plans, runs qualitative evaluations, tracks failures.

### When to Use

- End-to-end testing needed
- User perspective verification
- Quality beyond pass/fail

### Core Principles

1. **Black-box testing only**: Test as user would. Don't read source code.
2. **Qualitative over mechanical**: Judgment calls about quality, not just exit codes.
3. **Criteria from specs**: Never derive criteria from code.
4. **Failures are not excused**: Create task for each failure.

### Task Structure

```
[Epic] Acceptance Testing: [Feature]
├── [Task] QA Test Plan: [Feature]
├── [Task] Execute QA Tests: [Feature]
├── [Task] Fix: [Issue 1]
└── [Task] Retest: [Feature]
```

### Workflow Steps

1. Create test plan task with scope, acceptance criteria, test cases, qualitative rubric
2. Get plan approved (human reviews)
3. Execute tests: setup → trigger → capture → evaluate → score → document
4. Report results: summary table, qualitative scores, detailed findings
5. Handle failures: create task per failure, link to test plan

### Invocation

```
Task(subagent_type="qa",
     prompt="Execute acceptance test plan from task [TASK-ID]. Evaluate qualitatively, document failures as new tasks.")
```

---

## Mode: Integration Validation

Framework integration testing. "Does it connect properly?"

### When to Use

- Validating new framework capabilities
- Verifying structural changes (relationships, computed fields)
- After framework modifications

### Unique Steps

1. **Baseline**: Capture state before running feature
2. **Execute**: Run feature as user would
3. **Verify**: Check structural changes
4. **Report**: Evidence table (expected vs actual)

### Evidence Format

| Field | Expected | Actual | Correct? |
|-------|----------|--------|----------|
| [key] | [value]  | [value]| ✅/❌    |

### Invocation

```
Task(subagent_type="qa",
     prompt="Validate framework integration: [FEATURE]. Capture baseline, execute, verify structural changes, report evidence.")
```

---

## Mode: System Design

Design acceptance testing infrastructure for a project.

### When to Use

- "Design QA system", "build acceptance testing"
- New project needs verification strategy
- Existing tests pass but don't catch problems

### Core Principle

**Outcome over execution**: Tests that pass but don't detect problems are worse than no tests.

### Task Chain Pattern

```
[Epic: Acceptance Testing System]
├── T1: Inventory (what exists?)
├── T2: Gap Analysis (what's missing?) → depends on T1
├── T3: Design Workflow → depends on T2
├── T4: Define Test Cases → depends on T3
└── T5+: Implementation → depends on T4
```

### Phases

1. **Inventory**: Survey existing test frameworks, verification scripts, review processes
2. **Gap Analysis**: Assess against outcome-based QA capabilities
3. **Design Workflow**: Reviewer lifecycle, test case format, batch execution, reporting
4. **Define Test Cases**: Feature, expected behavior, fail condition, reproducible scenario
5. **Implementation**: Build the designed system

### Anti-Patterns

| Anti-Pattern | Why It Fails | Instead |
|--------------|--------------|---------|
| Pattern matching | Passes without understanding | Reviewer examines output |
| "Did it run?" tests | Passes broken behavior | Verify outcome is useful |
| Success = no errors | Silent failures pass | Define positive criteria |
| Skip to implementation | Build wrong thing | Complete design first |

---

## Cross-Client Robustness

AcademicOps supports multiple AI clients. Verify:

- Environment variables from one client don't break another
- Instructions are tailored to active client
- Tool output schemas are robust across client versions

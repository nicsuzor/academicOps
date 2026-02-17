# System Design Mode

Design acceptance testing infrastructure for a project.

## When to Use

- "Design QA system", "build acceptance testing"
- New project needs verification strategy
- Existing tests pass but don't catch problems

## Core Principle

**Outcome over execution**: Tests that pass but don't detect problems are worse than no tests.

## Task Chain Pattern

```
[Epic: Acceptance Testing System]
├── T1: Inventory (what exists?)
├── T2: Gap Analysis (what's missing?) → depends on T1
├── T3: Design Workflow → depends on T2
├── T4: Define Test Cases → depends on T3
└── T5+: Implementation → depends on T4
```

## Phases

1. **Inventory**: Survey existing test frameworks, verification scripts, review processes
2. **Gap Analysis**: Assess against outcome-based QA capabilities
3. **Design Workflow**: Reviewer lifecycle, test case format, batch execution, reporting
4. **Define Test Cases**: Feature, expected behavior, fail condition, reproducible scenario
5. **Implementation**: Build the designed system

## Anti-Patterns

| Anti-Pattern           | Why It Fails                 | Instead                  |
| ---------------------- | ---------------------------- | ------------------------ |
| Pattern matching       | Passes without understanding | Reviewer examines output |
| "Did it run?" tests    | Passes broken behavior       | Verify outcome is useful |
| Success = no errors    | Silent failures pass         | Define positive criteria |
| Skip to implementation | Build wrong thing            | Complete design first    |

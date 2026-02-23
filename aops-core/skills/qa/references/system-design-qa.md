# System Design Mode

Design acceptance testing infrastructure and criteria for a project.

## When to Use

- "Design QA system", "build acceptance testing"
- New project needs verification strategy
- Existing tests pass but don't catch problems
- Feature epic needs a QA plan designed from scratch

## Core Principle

**Outcome over execution**: Tests that pass but don't detect problems are worse than no tests. A QA system that verifies presence ("is X there?") but not fitness ("does X serve the user?") creates false confidence.

## Task Chain Pattern

```
[Epic: Acceptance Testing System]
├── T1: Inventory (what exists?)
├── T2: Gap Analysis (what's missing?) → depends on T1
├── T3: Criteria Design (what does good look like?) → depends on T2
├── T4: Design Workflow → depends on T3
├── T5: Define Evaluation Suites → depends on T4
└── T6+: Implementation → depends on T5
```

## Phases

### 1. Inventory

Survey existing test frameworks, verification scripts, review processes, specs, and user stories.

### 2. Gap Analysis

Assess against outcome-based QA capabilities. Key questions: Do existing tests evaluate fitness-for-purpose or just functional correctness? Are there user stories that no test covers? Are acceptance criteria binary checklists or qualitative dimensions?

### 3. Criteria Design

**This phase applies [[references/qa-planning.md]]** to design qualitative acceptance criteria for the project. Steps:

1. **Persona immersion**: Write the user paragraph for the project (situation, constraints, success feel)
2. **User story audit**: Do existing stories cover golden path, stressed path, and edge cases? Fill gaps.
3. **Transform criteria**: Convert binary checklists to qualitative dimensions with quality spectra (see [[references/qa-planning.md]] Anti-Patterns in QA Plan Design section)
4. **Validate**: Apply the Phase 4 self-check — traceability, evaluator independence, frustration detection, outcome focus

This phase produces the acceptance criteria that all subsequent testing evaluates against. If criteria are mechanical, all downstream testing inherits that weakness.

### 4. Design Workflow

Reviewer lifecycle, evaluation format, batch execution, reporting. Key decisions: who evaluates (human, agent, or both)? What triggers evaluation? How are results communicated?

### 5. Define Evaluation Suites

Two types of evaluation, kept separate:

**Per-task QA**: For each task in the epic, design:
- Which user story the task serves
- 2-3 qualitative dimensions with quality spectra
- One concrete scenario to walk through
- Regression checks (binary guards against breakage)

**E2E Evaluation Suites**: For the whole feature, design:
- Persona-grounded scenarios (entry state → actions → observations)
- Per-dimension narrative evaluation prompts
- Synthesis prompt (holistic judgment)

The evaluation suites are guides for skilled evaluators, not scripts for robots. See [[references/qualitative-assessment.md]] for the execution methodology.

### 6. Implementation

Build the designed system: test infrastructure, reporting tools, automation.

## Anti-Patterns

| Anti-Pattern                | Why It Fails                                           | Instead                                          |
| --------------------------- | ------------------------------------------------------ | ------------------------------------------------ |
| Pattern matching            | Passes without understanding                           | Reviewer examines output with judgment            |
| "Did it run?" tests         | Passes broken behavior                                 | Verify outcome is useful to the user              |
| Success = no errors         | Silent failures pass                                   | Define positive quality criteria                  |
| Skip to implementation      | Build wrong thing                                      | Complete criteria design first                    |
| Binary criteria for acceptance | Evaluator stops thinking; presence ≠ quality          | Qualitative dimensions with quality spectra       |
| Same format for all testing | Conflates "is this good?" with "did we break it?"      | Separate qualitative acceptance from regression   |
| Criteria without user stories | Tests what was built, not what was needed             | Trace every criterion to a story                  |

## Invocation

```
Task(subagent_type="qa",
     prompt="System Design mode. Design QA infrastructure and criteria for [PROJECT].
     Inventory existing tests, analyze gaps, design qualitative acceptance criteria
     per qa-planning.md, then design evaluation suites and workflow.")
```

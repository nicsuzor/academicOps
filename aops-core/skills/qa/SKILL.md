---
name: qa
category: instruction
description: QA verification, qualitative assessment, criteria design, and test planning
allowed-tools: Task,Read,Glob,Grep
version: 1.1.0
permalink: skills-qa
---

# /qa Command Skill

QA skill covering both upstream (criteria design, QA planning) and downstream (verification, assessment) workflows.

## Purpose

Provides rigorous verification that work **actually achieves** what the user needs — not just that tests pass or agents claim success. Also provides guidance for designing the criteria and plans that verification evaluates against.

## Usage

```
/qa
```

Or with context:

```
Skill(skill="qa", args="Verify the authentication feature is complete")
Skill(skill="qa", args="Design QA plan for the task map epic")
```

## Mode Selection

The QA skill has six modes. Select based on what you're being asked to do:

| Mode                       | When                                                         | Reference                                |
| -------------------------- | ------------------------------------------------------------ | ---------------------------------------- |
| **QA Planning**            | Designing acceptance criteria or QA plans BEFORE development | [[references/qa-planning.md]]            |
| **Qualitative Assessment** | Evaluating fitness-for-purpose AFTER development             | [[references/qualitative-assessment.md]] |
| **Acceptance Testing**     | Running test plans, tracking failures, creating fix tasks    | [[references/acceptance-testing.md]]     |
| **Quick Verification**     | Pre-completion sanity check (does it run?)                   | [[references/quick-verification.md]]     |
| **Integration Validation** | Verifying structural/framework changes                       | [[references/integration-validation.md]] |
| **System Design**          | Designing QA infrastructure and criteria for a project       | [[references/system-design-qa.md]]       |

### Routing Rules

- "Design criteria", "write acceptance criteria", "create QA plan" → **QA Planning**
- "Is this any good?", "evaluate against user stories" → **Qualitative Assessment**
- "Verify work is complete", "check before completion" → **Quick Verification** (default for `/qa` with no args)
- "Run the test plan", "execute acceptance tests" → **Acceptance Testing**
- "Validate framework integration" → **Integration Validation**
- "Design QA system for project" → **System Design**

## Execution

### Default (Quick Verification)

When invoked as `/qa` with no args, delegate to the QA agent for quick verification:

```
Task(subagent_type="aops-core:qa", model="opus", prompt="
Verify the work is complete.

**Original request**: [hydrated prompt from session context]

**Acceptance criteria**:
[Extract from task or session state]

**Work completed**:
[Files changed, todos marked complete]

Check all three dimensions (Output Quality, Process Compliance, Semantic Correctness) and produce verdict.
")
```

### QA Planning

When the request is about designing criteria or plans:

```
Task(subagent_type="aops-core:qa", model="opus", prompt="
QA Planning mode. Read references/qa-planning.md first.

Design acceptance criteria and QA plan for [FEATURE] based on spec [SPEC].
Inhabit the user persona. Write qualitative dimensions with quality spectra,
not binary checklists. Design scenarios, not test cases.

Output: acceptance criteria for the spec + per-task QA + E2E evaluation suites.
")
```

### Qualitative Assessment

When evaluating an existing feature:

```
Task(subagent_type="aops-core:qa", model="opus", prompt="
Qualitative Assessment mode. Read references/qualitative-assessment.md first.

Evaluate [FEATURE] against user stories in [SPEC/TASK].
Inhabit the user persona. Walk the scenarios. Evaluate fitness-for-purpose
in narrative prose. Is this good for the people it was designed for?
")
```

### Acceptance Testing

When running a test plan or tracking failures:

```
Task(subagent_type="aops-core:qa", model="opus", prompt="
Acceptance Testing mode. Read references/acceptance-testing.md first.

Run acceptance tests for [FEATURE] against the test plan in [SPEC/TASK].
Black-box testing only — test as the user would. For each failure, create
a fix task. Produce a results table with qualitative scores.
")
```

### Integration Validation

When verifying framework/structural changes:

```
Task(subagent_type="aops-core:qa", model="opus", prompt="
Integration Validation mode. Read references/integration-validation.md first.

Validate framework integration for [FEATURE]. Capture baseline state,
execute the feature, verify structural changes, report evidence table
(expected vs actual for each field/relationship).
")
```

### System Design

When designing QA infrastructure for a project:

```
Task(subagent_type="aops-core:qa", model="opus", prompt="
System Design mode. Read references/system-design-qa.md first.

Design QA infrastructure and criteria for [PROJECT]. Inventory existing
tests, analyze gaps, design qualitative acceptance criteria per
qa-planning.md, then design evaluation suites and workflow.
")
```

## Output

Varies by mode:

- **Quick Verification**: Verdict (VERIFIED/ISSUES) + dimension summary
- **QA Planning**: Acceptance criteria + per-task QA tables + E2E evaluation suites
- **Qualitative Assessment**: Narrative evaluation with evidence, synthesis, recommendations
- **Acceptance Testing**: Results table + failure tasks + qualitative scores
- **Integration Validation**: Evidence table (expected vs actual)
- **System Design**: QA infrastructure design + criteria + evaluation suites

## Integration

- **Stop hook**: May require QA verification before session end
- **Task completion**: QA should verify before `complete_task()`
- **Gate tracking**: `post_qa_trigger()` detects QA invocation
- **Spec writing**: SPEC-TEMPLATE.md references qa-planning.md for criteria design
- **Feature development**: Workflow 05 Phase 2 references qa-planning.md for requirements
- **Spec development**: Workflow 06 Step 4 references qa-planning.md for acceptance criteria
